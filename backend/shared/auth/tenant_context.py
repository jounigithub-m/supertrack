"""
Tenant context and isolation utilities.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Set, Union, Callable
import contextvars
from enum import Enum

from ..database import system_db_client, get_tenant_db_client
from ..database import get_tenant_neo4j_client, get_tenant_starrocks_client
from ..storage import get_tenant_adls_client, get_tenant_redis_client

# Configure logging
logger = logging.getLogger(__name__)


# Context variable for current tenant
current_tenant_var = contextvars.ContextVar("current_tenant", default=None)


class TenantRole(str, Enum):
    """Tenant roles for users."""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TenantContext:
    """
    Context manager for tenant-specific operations.
    
    This class provides a context for operations within a specific tenant,
    with access to tenant-specific resources and clients.
    """
    
    def __init__(
        self, 
        tenant_id: str, 
        user_id: Optional[str] = None,
        user_role: Optional[str] = None
    ):
        """
        Initialize tenant context.
        
        Args:
            tenant_id: ID of the tenant
            user_id: Optional ID of the current user
            user_role: Optional role of the current user within the tenant
        """
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.user_role = user_role
        self._token = None
        
        # Lazy-loaded client instances
        self._db_client = None
        self._neo4j_client = None
        self._starrocks_client = None
        self._adls_client = None
        self._redis_client = None
    
    @property
    def db_client(self):
        """Get Cosmos DB client for this tenant."""
        if self._db_client is None:
            self._db_client = get_tenant_db_client(self.tenant_id)
        return self._db_client
    
    @property
    def neo4j_client(self):
        """Get Neo4j client for this tenant."""
        if self._neo4j_client is None:
            self._neo4j_client = get_tenant_neo4j_client(self.tenant_id)
        return self._neo4j_client
    
    @property
    def starrocks_client(self):
        """Get StarRocks client for this tenant."""
        if self._starrocks_client is None:
            self._starrocks_client = get_tenant_starrocks_client(self.tenant_id)
        return self._starrocks_client
    
    @property
    def adls_client(self):
        """Get ADLS client for this tenant."""
        if self._adls_client is None:
            self._adls_client = get_tenant_adls_client(self.tenant_id)
        return self._adls_client
    
    @property
    def redis_client(self):
        """Get Redis client for this tenant."""
        if self._redis_client is None:
            self._redis_client = get_tenant_redis_client(self.tenant_id)
        return self._redis_client
    
    async def get_tenant_details(self) -> Dict[str, Any]:
        """
        Get details about the tenant.
        
        Returns:
            Tenant details from the system database
        """
        tenant = await system_db_client.get_item("tenants", self.tenant_id)
        return tenant or {}
    
    async def has_permission(self, required_role: Union[str, TenantRole]) -> bool:
        """
        Check if the current user has permission for a role.
        
        Args:
            required_role: Role required for the operation
            
        Returns:
            True if user has sufficient permissions
        """
        if not self.user_id or not self.user_role:
            return False
        
        # Convert string role to enum if needed
        if isinstance(required_role, str):
            try:
                required_role = TenantRole(required_role.lower())
            except ValueError:
                logger.warning(f"Invalid role: {required_role}")
                return False
        
        # Convert user role to enum if needed
        user_role = self.user_role
        if isinstance(user_role, str):
            try:
                user_role = TenantRole(user_role.lower())
            except ValueError:
                logger.warning(f"Invalid user role: {user_role}")
                return False
        
        # Check permissions
        if user_role == TenantRole.ADMIN:
            # Admin has access to everything
            return True
        
        if user_role == TenantRole.MEMBER:
            # Member has access to member and viewer operations
            return required_role != TenantRole.ADMIN
        
        if user_role == TenantRole.VIEWER:
            # Viewer has access only to viewer operations
            return required_role == TenantRole.VIEWER
        
        return False
    
    async def __aenter__(self):
        """Enter the tenant context."""
        # Store previous tenant context
        self._token = current_tenant_var.set(self)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the tenant context."""
        # Restore previous tenant context
        current_tenant_var.reset(self._token)


async def get_current_tenant() -> TenantContext:
    """
    Get the current tenant context.
    
    Returns:
        Current tenant context
        
    Raises:
        ValueError: If no tenant context is set
    """
    tenant = current_tenant_var.get()
    if tenant is None:
        raise ValueError("No tenant context set")
    return tenant


async def require_tenant_context(
    func: Callable
) -> Callable:
    """
    Decorator to require a tenant context for a function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
        
    Raises:
        ValueError: If no tenant context is set
    """
    async def wrapper(*args, **kwargs):
        tenant = current_tenant_var.get()
        if tenant is None:
            raise ValueError("This operation requires a tenant context")
        return await func(*args, **kwargs)
    
    return wrapper


async def get_user_tenants(user_id: str) -> List[Dict[str, Any]]:
    """
    Get tenants the user has access to.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of tenant details the user has access to
    """
    # Get user from system database
    user = await system_db_client.get_item("users", user_id)
    
    if not user:
        return []
    
    # Get tenant access from user
    tenant_access = user.get("tenant_access", [])
    
    if not tenant_access:
        return []
    
    # Get tenant details for each tenant the user has access to
    tenants = []
    
    for access in tenant_access:
        tenant_id = access.get("tenant_id")
        
        if not tenant_id:
            continue
        
        tenant = await system_db_client.get_item("tenants", tenant_id)
        
        if tenant:
            # Add role to tenant details
            tenant["role"] = access.get("role", "viewer")
            tenants.append(tenant)
    
    return tenants


async def create_tenant_context_from_request(request) -> TenantContext:
    """
    Create a tenant context from a request.
    
    Args:
        request: HTTP request
        
    Returns:
        Tenant context
        
    Raises:
        ValueError: If tenant ID is missing or user doesn't have access
    """
    from .jwt_utils import get_user_from_request
    
    # Extract tenant ID from headers
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        raise ValueError("Tenant ID is required in X-Tenant-ID header")
    
    # Get user information from request
    try:
        user_info = await get_user_from_request(request)
        user_id = user_info.get("id")
        
        # Check if user has access to this tenant
        tenant_access = user_info.get("tenant_access", [])
        user_role = None
        
        for access in tenant_access:
            if access.get("tenant_id") == tenant_id:
                user_role = access.get("role")
                break
        
        if not user_role:
            raise ValueError(f"User doesn't have access to tenant {tenant_id}")
        
        # Create tenant context
        return TenantContext(tenant_id, user_id, user_role)
        
    except Exception as e:
        logger.error(f"Error creating tenant context: {str(e)}")
        raise ValueError(f"Error creating tenant context: {str(e)}")


def tenant_required(func: Callable) -> Callable:
    """
    Decorator for Azure Functions to require a tenant context.
    
    Args:
        func: Azure Function to decorate
        
    Returns:
        Decorated function
    """
    async def wrapper(req, *args, **kwargs):
        try:
            # Create tenant context from request
            tenant_ctx = await create_tenant_context_from_request(req)
            
            # Run the function within the tenant context
            async with tenant_ctx:
                return await func(req, *args, **kwargs)
        except ValueError as e:
            return {
                "status_code": 400,
                "body": {"error": str(e)}
            }
        except Exception as e:
            logger.error(f"Error in tenant_required: {str(e)}")
            return {
                "status_code": 500,
                "body": {"error": "An error occurred processing the request"}
            }
    
    return wrapper