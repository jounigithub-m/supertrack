"""
Redis client for caching and temporary storage.
"""

import logging
import json
import pickle
from typing import Any, Dict, List, Optional, Union, Tuple
import time

import redis

from ..utils.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class RedisClient:
    """
    Client for Redis caching and temporary storage operations.
    
    This client provides methods for caching data, managing distributed locks,
    and supporting tenant isolation for cached data.
    """
    
    def __init__(
        self, 
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: int = 0,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize the Redis client.
        
        Args:
            host: Redis server host. Defaults to settings.redis_host.
            port: Redis server port. Defaults to settings.redis_port.
            password: Redis password. Defaults to settings.redis_password.
            db: Redis database number (0-15).
            tenant_id: Optional tenant ID for key prefixing.
        """
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.password = password or settings.redis_password
        self.db = db
        self.tenant_id = tenant_id
        
        # Initialize Redis client
        self.client = self._create_client()
    
    def _create_client(self) -> redis.Redis:
        """Create and return a Redis client."""
        try:
            return redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=False  # We handle decoding manually for flexibility
            )
        except Exception as e:
            logger.error(f"Error creating Redis client: {str(e)}")
            raise
    
    def _get_tenant_key(self, key: str) -> str:
        """
        Get the full key with tenant prefix if a tenant ID is set.
        
        Args:
            key: The original key
            
        Returns:
            The key with tenant prefix if applicable
        """
        if self.tenant_id:
            return f"tenant:{self.tenant_id}:{key}"
        return key
    
    async def verify_connectivity(self) -> bool:
        """
        Verify that the connection to Redis is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis connectivity check failed: {str(e)}")
            return False
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expiration: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
        serialize: bool = True
    ) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: The key to set
            value: The value to set
            expiration: Optional expiration time in seconds
            nx: Only set if key does not exist
            xx: Only set if key already exists
            serialize: Whether to JSON/pickle serialize the value
            
        Returns:
            True if the key was set
        """
        tenant_key = self._get_tenant_key(key)
        
        # Serialize value if needed
        if serialize:
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                # Use JSON for simple types
                value = json.dumps(value).encode('utf-8')
            else:
                # Use pickle for complex types
                value = pickle.dumps(value)
        
        try:
            # Set parameters
            params = {}
            if expiration is not None:
                params['ex'] = expiration
            if nx:
                params['nx'] = True
            if xx:
                params['xx'] = True
            
            result = self.client.set(tenant_key, value, **params)
            return result is True
        except Exception as e:
            logger.error(f"Error setting key '{tenant_key}': {str(e)}")
            raise
    
    async def get(
        self, 
        key: str, 
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """
        Get a value from Redis.
        
        Args:
            key: The key to get
            default: Default value to return if key doesn't exist
            deserialize: Whether to deserialize the value from JSON/pickle
            
        Returns:
            The value or default if not found
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            value = self.client.get(tenant_key)
            
            if value is None:
                return default
            
            # Deserialize if needed
            if deserialize:
                try:
                    # Try JSON first
                    return json.loads(value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        # Fall back to pickle
                        return pickle.loads(value)
                    except Exception:
                        # Return raw value if all deserialization fails
                        return value
            
            return value
        except Exception as e:
            logger.error(f"Error getting key '{tenant_key}': {str(e)}")
            raise
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: The key to delete
            
        Returns:
            True if the key was deleted
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            result = self.client.delete(tenant_key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting key '{tenant_key}': {str(e)}")
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            return self.client.exists(tenant_key) > 0
        except Exception as e:
            logger.error(f"Error checking existence of key '{tenant_key}': {str(e)}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set an expiration time on a key.
        
        Args:
            key: The key to expire
            seconds: Time to expiration in seconds
            
        Returns:
            True if the timeout was set
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            return self.client.expire(tenant_key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for key '{tenant_key}': {str(e)}")
            raise
    
    async def ttl(self, key: str) -> int:
        """
        Get the time to live for a key.
        
        Args:
            key: The key to check
            
        Returns:
            Time to live in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            return self.client.ttl(tenant_key)
        except Exception as e:
            logger.error(f"Error getting TTL for key '{tenant_key}': {str(e)}")
            raise
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Find keys matching a pattern.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            List of matching keys
        """
        # If tenant is set, add tenant prefix to pattern
        if self.tenant_id and not pattern.startswith(f"tenant:{self.tenant_id}:"):
            tenant_pattern = f"tenant:{self.tenant_id}:{pattern}"
        else:
            tenant_pattern = pattern
        
        try:
            keys = self.client.keys(tenant_pattern)
            # Decode byte strings to regular strings
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Error getting keys with pattern '{tenant_pattern}': {str(e)}")
            raise
    
    async def acquire_lock(
        self, 
        lock_name: str, 
        timeout: int = 10,
        expiration: int = 30
    ) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_name: Name of the lock
            timeout: Time to wait for lock in seconds
            expiration: Lock expiration time in seconds
            
        Returns:
            True if lock was acquired
        """
        lock_key = self._get_tenant_key(f"lock:{lock_name}")
        
        # Set a unique lock value to identify our lock
        lock_value = str(time.time())
        
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            # Try to acquire the lock
            acquired = await self.set(lock_key, lock_value, expiration=expiration, nx=True, serialize=False)
            
            if acquired:
                return True
            
            # Wait a bit before trying again
            time.sleep(0.1)
        
        return False
    
    async def release_lock(self, lock_name: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_name: Name of the lock
            
        Returns:
            True if lock was released
        """
        lock_key = self._get_tenant_key(f"lock:{lock_name}")
        return await self.delete(lock_key)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a key by the given amount.
        
        Args:
            key: The key to increment
            amount: The amount to increment by
            
        Returns:
            The new value
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            return self.client.incrby(tenant_key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key '{tenant_key}': {str(e)}")
            raise
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a key by the given amount.
        
        Args:
            key: The key to decrement
            amount: The amount to decrement by
            
        Returns:
            The new value
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            return self.client.decrby(tenant_key, amount)
        except Exception as e:
            logger.error(f"Error decrementing key '{tenant_key}': {str(e)}")
            raise
    
    async def hash_set(self, key: str, mapping: Dict[str, Any], expiration: Optional[int] = None) -> bool:
        """
        Set multiple fields in a hash.
        
        Args:
            key: The hash key
            mapping: Dictionary of field-value pairs
            expiration: Optional expiration time in seconds
            
        Returns:
            True if the operation succeeded
        """
        tenant_key = self._get_tenant_key(key)
        
        # Serialize values
        serialized_mapping = {}
        for field, value in mapping.items():
            if isinstance(value, (dict, list)):
                serialized_mapping[field] = json.dumps(value)
            else:
                serialized_mapping[field] = value
        
        try:
            self.client.hset(tenant_key, mapping=serialized_mapping)
            
            # Set expiration if provided
            if expiration is not None:
                self.client.expire(tenant_key, expiration)
                
            return True
        except Exception as e:
            logger.error(f"Error setting hash fields for key '{tenant_key}': {str(e)}")
            raise
    
    async def hash_get(self, key: str, field: str, default: Any = None) -> Any:
        """
        Get a field from a hash.
        
        Args:
            key: The hash key
            field: The field to get
            default: Default value if field doesn't exist
            
        Returns:
            The field value or default
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            value = self.client.hget(tenant_key, field)
            
            if value is None:
                return default
            
            # Try to deserialize JSON
            if isinstance(value, bytes):
                try:
                    return json.loads(value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return value.decode('utf-8')
            
            return value
        except Exception as e:
            logger.error(f"Error getting hash field '{field}' for key '{tenant_key}': {str(e)}")
            raise
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """
        Get all fields and values from a hash.
        
        Args:
            key: The hash key
            
        Returns:
            Dictionary of field-value pairs
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            result = self.client.hgetall(tenant_key)
            
            # Deserialize values and convert byte keys to strings
            deserialized = {}
            for field, value in result.items():
                # Convert byte keys to strings
                if isinstance(field, bytes):
                    field = field.decode('utf-8')
                
                # Try to deserialize values
                if isinstance(value, bytes):
                    try:
                        deserialized[field] = json.loads(value.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        deserialized[field] = value.decode('utf-8')
                else:
                    deserialized[field] = value
            
            return deserialized
        except Exception as e:
            logger.error(f"Error getting all hash fields for key '{tenant_key}': {str(e)}")
            raise
    
    async def list_push(
        self, 
        key: str, 
        *values: Any, 
        side: str = 'right',
        expiration: Optional[int] = None
    ) -> int:
        """
        Push values to a list.
        
        Args:
            key: The list key
            *values: Values to push
            side: Side to push to ('left' or 'right')
            expiration: Optional expiration time in seconds
            
        Returns:
            Length of the list after push
        """
        tenant_key = self._get_tenant_key(key)
        
        # Serialize values
        serialized_values = []
        for value in values:
            if isinstance(value, (dict, list)):
                serialized_values.append(json.dumps(value))
            else:
                serialized_values.append(value)
        
        try:
            if side.lower() == 'left':
                result = self.client.lpush(tenant_key, *serialized_values)
            else:
                result = self.client.rpush(tenant_key, *serialized_values)
            
            # Set expiration if provided
            if expiration is not None:
                self.client.expire(tenant_key, expiration)
                
            return result
        except Exception as e:
            logger.error(f"Error pushing to list '{tenant_key}': {str(e)}")
            raise
    
    async def list_pop(self, key: str, side: str = 'right', default: Any = None) -> Any:
        """
        Pop a value from a list.
        
        Args:
            key: The list key
            side: Side to pop from ('left' or 'right')
            default: Default value if list is empty
            
        Returns:
            The popped value or default
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            if side.lower() == 'left':
                value = self.client.lpop(tenant_key)
            else:
                value = self.client.rpop(tenant_key)
            
            if value is None:
                return default
            
            # Try to deserialize JSON
            if isinstance(value, bytes):
                try:
                    return json.loads(value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return value.decode('utf-8')
            
            return value
        except Exception as e:
            logger.error(f"Error popping from list '{tenant_key}': {str(e)}")
            raise
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get a range of values from a list.
        
        Args:
            key: The list key
            start: Start index
            end: End index
            
        Returns:
            List of values in the specified range
        """
        tenant_key = self._get_tenant_key(key)
        
        try:
            values = self.client.lrange(tenant_key, start, end)
            
            # Deserialize values
            deserialized = []
            for value in values:
                if isinstance(value, bytes):
                    try:
                        deserialized.append(json.loads(value.decode('utf-8')))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        deserialized.append(value.decode('utf-8'))
                else:
                    deserialized.append(value)
            
            return deserialized
        except Exception as e:
            logger.error(f"Error getting range from list '{tenant_key}': {str(e)}")
            raise
    
    async def flush_db(self) -> bool:
        """
        Delete all keys in the current database.
        WARNING: Use with caution!
        
        Returns:
            True if operation succeeded
        """
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error flushing database: {str(e)}")
            raise


# Create a default client instance
default_redis_client = RedisClient()


def get_tenant_redis_client(tenant_id: str) -> RedisClient:
    """
    Get a Redis client for a specific tenant.
    
    Args:
        tenant_id: ID of the tenant
        
    Returns:
        A RedisClient instance with tenant isolation
    """
    return RedisClient(tenant_id=tenant_id)