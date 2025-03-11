"""
Azure Cosmos DB client for interacting with the database.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as cosmos_exceptions
from azure.cosmos.partition_key import PartitionKey

from ..utils.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class CosmosDBClient:
    """
    Client for Azure Cosmos DB operations with tenant isolation support.
    
    This client provides methods for CRUD operations on Cosmos DB containers
    and supports tenant isolation by operating within a specific database.
    """
    
    def __init__(self, database_name: Optional[str] = None):
        """
        Initialize the Cosmos DB client.
        
        Args:
            database_name: Optional name of the database to use. Defaults to settings.cosmos_db_name.
        """
        self.client = cosmos_client.CosmosClient.from_connection_string(
            settings.cosmos_db_connection_string
        )
        self.database_name = database_name or settings.cosmos_db_name
        self.database = self.client.get_database_client(self.database_name)
        
        # Cache for containers to avoid repeated lookups
        self._container_cache = {}
    
    def get_container(self, container_name: str) -> Any:
        """
        Get a container client by name.
        
        Args:
            container_name: Name of the container
            
        Returns:
            A ContainerProxy object for the requested container
        """
        if container_name not in self._container_cache:
            self._container_cache[container_name] = self.database.get_container_client(container_name)
        return self._container_cache[container_name]
    
    async def create_database_if_not_exists(self) -> None:
        """Create the database if it doesn't already exist."""
        try:
            self.client.create_database_if_not_exists(
                id=self.database_name,
                offer_throughput=400  # Minimum throughput
            )
            logger.info(f"Database '{self.database_name}' created or already exists")
        except Exception as e:
            logger.error(f"Error creating database '{self.database_name}': {str(e)}")
            raise
    
    async def create_container_if_not_exists(
        self, 
        container_name: str, 
        partition_key: str = "/id",
        throughput: int = 400
    ) -> None:
        """
        Create a container if it doesn't already exist.
        
        Args:
            container_name: Name of the container
            partition_key: Partition key path (default: "/id")
            throughput: Provisioned throughput (default: 400 RU/s)
        """
        try:
            self.database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_key),
                offer_throughput=throughput
            )
            # Clear cache to ensure we get the new container
            if container_name in self._container_cache:
                del self._container_cache[container_name]
            logger.info(f"Container '{container_name}' created or already exists")
        except Exception as e:
            logger.error(f"Error creating container '{container_name}': {str(e)}")
            raise
    
    async def upsert_item(
        self, 
        container_name: str, 
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create or update an item in a container.
        
        Args:
            container_name: Name of the container
            item: The item to upsert
            
        Returns:
            The created or updated item
        """
        container = self.get_container(container_name)
        try:
            result = container.upsert_item(body=item)
            return result
        except cosmos_exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error upserting item in '{container_name}': {str(e)}")
            raise
    
    async def get_item(
        self, 
        container_name: str, 
        item_id: str, 
        partition_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from a container.
        
        Args:
            container_name: Name of the container
            item_id: ID of the item to retrieve
            partition_key: Optional partition key value (if different from item_id)
            
        Returns:
            The retrieved item or None if not found
        """
        container = self.get_container(container_name)
        partition_key_value = partition_key or item_id
        
        try:
            return container.read_item(item=item_id, partition_key=partition_key_value)
        except cosmos_exceptions.CosmosResourceNotFoundError:
            logger.debug(f"Item '{item_id}' not found in container '{container_name}'")
            return None
        except cosmos_exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error getting item '{item_id}' from '{container_name}': {str(e)}")
            raise
    
    async def delete_item(
        self, 
        container_name: str, 
        item_id: str, 
        partition_key: Optional[str] = None
    ) -> None:
        """
        Delete an item from a container.
        
        Args:
            container_name: Name of the container
            item_id: ID of the item to delete
            partition_key: Optional partition key value (if different from item_id)
        """
        container = self.get_container(container_name)
        partition_key_value = partition_key or item_id
        
        try:
            container.delete_item(item=item_id, partition_key=partition_key_value)
        except cosmos_exceptions.CosmosResourceNotFoundError:
            logger.debug(f"Item '{item_id}' not found for deletion in container '{container_name}'")
        except cosmos_exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error deleting item '{item_id}' from '{container_name}': {str(e)}")
            raise
    
    async def query_items(
        self, 
        container_name: str, 
        query: str, 
        parameters: Optional[List[Dict[str, Any]]] = None,
        partition_key: Optional[str] = None,
        max_item_count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query items from a container.
        
        Args:
            container_name: Name of the container
            query: SQL query string
            parameters: Optional parameters for the query
            partition_key: Optional partition key to restrict the query
            max_item_count: Maximum number of items to return
            
        Returns:
            List of items matching the query
        """
        container = self.get_container(container_name)
        
        query_options = {
            'max_item_count': max_item_count,
            'enable_cross_partition_query': partition_key is None
        }
        
        if parameters:
            query_options['parameters'] = parameters
            
        try:
            results = list(container.query_items(
                query=query,
                partition_key=partition_key,
                **query_options
            ))
            return results
        except cosmos_exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error querying items from '{container_name}': {str(e)}")
            raise
    
    async def get_items_by_property(
        self,
        container_name: str,
        property_name: str,
        property_value: Any,
        partition_key: Optional[str] = None,
        max_item_count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get items that match a specific property value.
        
        Args:
            container_name: Name of the container
            property_name: Name of the property to match
            property_value: Value to match
            partition_key: Optional partition key to restrict the query
            max_item_count: Maximum number of items to return
            
        Returns:
            List of items with the matching property value
        """
        query = f"SELECT * FROM c WHERE c.{property_name} = @value"
        parameters = [{"name": "@value", "value": property_value}]
        
        return await self.query_items(
            container_name=container_name,
            query=query,
            parameters=parameters,
            partition_key=partition_key,
            max_item_count=max_item_count
        )
    
    async def bulk_upsert(
        self,
        container_name: str,
        items: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Bulk upsert items to a container.
        
        Args:
            container_name: Name of the container
            items: List of items to upsert
            batch_size: Number of items to upsert in each batch
            
        Returns:
            List of upserted items
        """
        container = self.get_container(container_name)
        results = []
        
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_results = []
            
            # Process each item in the batch
            for item in batch:
                try:
                    result = container.upsert_item(body=item)
                    batch_results.append(result)
                except cosmos_exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error upserting item in batch: {str(e)}")
                    # Append the original item with an error flag
                    item['_error'] = str(e)
                    batch_results.append(item)
            
            results.extend(batch_results)
            
            # Pause briefly between batches to avoid rate limiting
            if i + batch_size < len(items):
                time.sleep(0.1)
        
        return results


# Create a singleton instance for the system database
system_db_client = CosmosDBClient(settings.cosmos_db_name)


def get_tenant_db_client(tenant_id: str) -> CosmosDBClient:
    """
    Get a database client for a specific tenant.
    
    Args:
        tenant_id: ID of the tenant
        
    Returns:
        A CosmosDBClient instance for the tenant database
    """
    tenant_db_name = f"tenant_{tenant_id}"
    return CosmosDBClient(tenant_db_name)