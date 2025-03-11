"""
Configuration utilities for managing environment variables and application settings.
"""

import os
from typing import Any, Dict, Optional, Set, Union
import logging
from enum import Enum

# Setup logging
logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def get_environment() -> Environment:
    """Get the current environment (development, staging, or production)."""
    env = os.environ.get("ENVIRONMENT", "development").lower()
    
    if env in [e.value for e in Environment]:
        return Environment(env)
    
    logger.warning(f"Unknown environment: {env}, defaulting to development")
    return Environment.DEVELOPMENT


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == Environment.DEVELOPMENT


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == Environment.PRODUCTION


def get_required_setting(name: str) -> str:
    """
    Get a required environment variable.
    
    Args:
        name: Name of the environment variable
        
    Returns:
        The value of the environment variable
        
    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.environ.get(name)
    if value is None:
        if is_development():
            logger.warning(f"Required environment variable {name} not set, using empty string")
            return ""
        raise ValueError(f"Required environment variable '{name}' not set")
    return value


def get_optional_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an optional environment variable with a default value.
    
    Args:
        name: Name of the environment variable
        default: Default value to return if the variable is not set
        
    Returns:
        The value of the environment variable or the default
    """
    return os.environ.get(name, default)


def get_boolean_setting(name: str, default: bool = False) -> bool:
    """
    Get a boolean environment variable.
    
    Args:
        name: Name of the environment variable
        default: Default value to return if the variable is not set
        
    Returns:
        Boolean value of the environment variable
    """
    value = get_optional_setting(name, str(default).lower())
    return value.lower() in ("true", "1", "t", "yes", "y")


def get_int_setting(name: str, default: int = 0) -> int:
    """
    Get an integer environment variable.
    
    Args:
        name: Name of the environment variable
        default: Default value to return if the variable is not set
        
    Returns:
        Integer value of the environment variable
    """
    value = get_optional_setting(name, str(default))
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {name}: {value}, using default {default}")
        return default


def get_float_setting(name: str, default: float = 0.0) -> float:
    """
    Get a float environment variable.
    
    Args:
        name: Name of the environment variable
        default: Default value to return if the variable is not set
        
    Returns:
        Float value of the environment variable
    """
    value = get_optional_setting(name, str(default))
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for {name}: {value}, using default {default}")
        return default


def get_list_setting(name: str, default: Optional[list] = None, separator: str = ",") -> list:
    """
    Get a list environment variable.
    
    Args:
        name: Name of the environment variable
        default: Default value to return if the variable is not set
        separator: Separator to split the string value
        
    Returns:
        List value of the environment variable
    """
    if default is None:
        default = []
        
    value = get_optional_setting(name)
    if value is None:
        return default
        
    return [item.strip() for item in value.split(separator) if item.strip()]


def get_connection_string(name: str) -> str:
    """
    Get a database connection string, with special handling for development mode.
    
    Args:
        name: Name of the connection string environment variable
        
    Returns:
        The connection string value
    """
    value = get_optional_setting(name)
    
    if not value and is_development():
        # In development, we'll log a warning but return an empty string
        # This allows the application to start without all connections configured
        logger.warning(f"Connection string {name} not set in development mode")
        return ""
        
    if not value:
        raise ValueError(f"Required connection string '{name}' not set")
        
    return value


# Common configuration settings as properties
class Settings:
    """Common application settings retrieved from environment variables."""
    
    @property
    def log_level(self) -> str:
        """Logging level for the application."""
        return get_optional_setting("LOG_LEVEL", "INFO").upper()
    
    @property
    def enable_telemetry(self) -> bool:
        """Whether telemetry is enabled."""
        return get_boolean_setting("ENABLE_TELEMETRY", False)
    
    @property
    def max_batch_size(self) -> int:
        """Maximum batch size for operations."""
        return get_int_setting("MAX_BATCH_SIZE", 1000)
    
    @property
    def cache_ttl(self) -> int:
        """Default cache TTL in seconds."""
        return get_int_setting("CACHE_TTL", 3600)  # 1 hour
    
    @property
    def cosmos_db_connection_string(self) -> str:
        """Cosmos DB connection string."""
        return get_connection_string("COSMOS_DB_CONNECTION_STRING")
    
    @property
    def cosmos_db_name(self) -> str:
        """Cosmos DB database name."""
        return get_optional_setting("COSMOS_DB_NAME", "supertrack-system")
    
    @property
    def neo4j_uri(self) -> str:
        """Neo4j connection URI."""
        return get_optional_setting("NEO4J_URI", "neo4j://localhost:7687")
    
    @property
    def neo4j_user(self) -> str:
        """Neo4j username."""
        return get_optional_setting("NEO4J_USER", "neo4j")
    
    @property
    def neo4j_password(self) -> str:
        """Neo4j password."""
        return get_required_setting("NEO4J_PASSWORD")
    
    @property
    def starrocks_host(self) -> str:
        """StarRocks database host."""
        return get_optional_setting("STARROCKS_HOST", "localhost")
    
    @property
    def starrocks_port(self) -> int:
        """StarRocks database port."""
        return get_int_setting("STARROCKS_PORT", 9030)
    
    @property
    def starrocks_user(self) -> str:
        """StarRocks database username."""
        return get_optional_setting("STARROCKS_USER", "root")
    
    @property
    def starrocks_password(self) -> str:
        """StarRocks database password."""
        return get_required_setting("STARROCKS_PASSWORD")
    
    @property
    def storage_connection_string(self) -> str:
        """Azure Storage connection string."""
        return get_connection_string("AZURE_STORAGE_CONNECTION_STRING")
    
    @property
    def storage_account_name(self) -> str:
        """Azure Storage account name."""
        return get_required_setting("AZURE_STORAGE_ACCOUNT_NAME")
    
    @property
    def storage_account_key(self) -> str:
        """Azure Storage account key."""
        return get_required_setting("AZURE_STORAGE_ACCOUNT_KEY")
    
    @property
    def redis_host(self) -> str:
        """Redis host."""
        return get_optional_setting("REDIS_HOST", "localhost")
    
    @property
    def redis_port(self) -> int:
        """Redis port."""
        return get_int_setting("REDIS_PORT", 6379)
    
    @property
    def redis_password(self) -> str:
        """Redis password."""
        return get_optional_setting("REDIS_PASSWORD", "")


# Create a singleton instance
settings = Settings()