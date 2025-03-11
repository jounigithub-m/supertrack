"""
StarRocks client for analytical database operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import time
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

from ..utils.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class StarRocksClient:
    """
    Client for StarRocks database operations.
    
    This client provides methods for executing analytical queries on StarRocks
    and for managing tables and data.
    """
    
    def __init__(
        self, 
        host: Optional[str] = None, 
        port: Optional[int] = None, 
        user: Optional[str] = None, 
        password: Optional[str] = None, 
        database: Optional[str] = None
    ):
        """
        Initialize the StarRocks client.
        
        Args:
            host: StarRocks server host. Defaults to settings.starrocks_host.
            port: StarRocks server port. Defaults to settings.starrocks_port.
            user: StarRocks username. Defaults to settings.starrocks_user.
            password: StarRocks password. Defaults to settings.starrocks_password.
            database: StarRocks database name. If None, no specific database is selected.
        """
        self.host = host or settings.starrocks_host
        self.port = port or settings.starrocks_port
        self.user = user or settings.starrocks_user
        self.password = password or settings.starrocks_password
        self.database = database
        
        # Initialize connection
        self.connection = None
    
    def _get_connection(self) -> pymysql.Connection:
        """
        Get a connection to the StarRocks database.
        
        Returns:
            A PyMySQL connection object
        """
        if self.connection is None or not self.connection.open:
            try:
                conn_params = {
                    "host": self.host,
                    "port": self.port,
                    "user": self.user,
                    "password": self.password,
                    "charset": "utf8mb4",
                    "cursorclass": DictCursor,
                }
                
                if self.database:
                    conn_params["database"] = self.database
                
                self.connection = pymysql.connect(**conn_params)
            except Exception as e:
                logger.error(f"Error connecting to StarRocks: {str(e)}")
                raise
        
        return self.connection
    
    def close(self) -> None:
        """Close the StarRocks connection."""
        if self.connection and self.connection.open:
            self.connection.close()
            self.connection = None
    
    async def verify_connectivity(self) -> bool:
        """
        Verify that the connection to StarRocks is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS test")
                result = cursor.fetchone()
                return result and result["test"] == 1
        except Exception as e:
            logger.error(f"StarRocks connectivity check failed: {str(e)}")
            return False
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query: SQL query string
            parameters: Optional parameters for the query
            
        Returns:
            List of records as dictionaries
        """
        if parameters is None:
            parameters = {}
            
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, parameters)
                results = cursor.fetchall()
                return list(results)
        except Exception as e:
            logger.error(f"StarRocks query error: {str(e)}")
            raise
    
    async def execute_query_to_dataframe(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return the results as a pandas DataFrame.
        
        Args:
            query: SQL query string
            parameters: Optional parameters for the query
            
        Returns:
            Results as a pandas DataFrame
        """
        results = await self.execute_query(query, parameters)
        return pd.DataFrame(results)
    
    async def execute_update(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Execute a SQL update statement and return the number of affected rows.
        
        Args:
            query: SQL update statement
            parameters: Optional parameters for the query
            
        Returns:
            Number of affected rows
        """
        if parameters is None:
            parameters = {}
            
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, parameters)
                conn.commit()
                return affected_rows
        except Exception as e:
            conn.rollback()
            logger.error(f"StarRocks update error: {str(e)}")
            raise
    
    async def create_database(self, database_name: str) -> bool:
        """
        Create a database if it doesn't exist.
        
        Args:
            database_name: Name of the database to create
            
        Returns:
            True if database was created or already exists
        """
        query = f"CREATE DATABASE IF NOT EXISTS `{database_name}`"
        try:
            await self.execute_update(query)
            logger.info(f"Database '{database_name}' created or already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating database '{database_name}': {str(e)}")
            raise
    
    async def create_table(
        self, 
        table_name: str, 
        column_definitions: List[str],
        primary_keys: List[str],
        distribution_keys: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        partition_by: Optional[str] = None,
        engine: str = "OLAP",
        if_not_exists: bool = True
    ) -> bool:
        """
        Create a table with the specified schema.
        
        Args:
            table_name: Name of the table to create
            column_definitions: List of column definitions (e.g. ["id INT", "name VARCHAR(100)"])
            primary_keys: List of primary key columns
            distribution_keys: Optional list of distribution key columns
            order_by: Optional list of order by columns
            partition_by: Optional partition by expression
            engine: Table engine (default: OLAP)
            if_not_exists: Whether to use IF NOT EXISTS clause
            
        Returns:
            True if table was created successfully
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        
        columns_str = ",\n    ".join(column_definitions)
        primary_keys_str = ", ".join(primary_keys)
        
        # Build distribution clause
        distribution_clause = ""
        if distribution_keys:
            dist_keys_str = ", ".join(distribution_keys)
            distribution_clause = f"DISTRIBUTED BY HASH({dist_keys_str})"
        
        # Build order by clause
        order_clause = ""
        if order_by:
            order_str = ", ".join(order_by)
            order_clause = f"ORDER BY ({order_str})"
        
        # Build partition clause
        partition_clause = ""
        if partition_by:
            partition_clause = f"PARTITION BY {partition_by}"
        
        query = f"""
        CREATE TABLE {exists_clause} `{table_name}` (
            {columns_str},
            PRIMARY KEY ({primary_keys_str})
        )
        ENGINE = {engine}
        {distribution_clause}
        {order_clause}
        {partition_clause}
        """
        
        try:
            await self.execute_update(query)
            logger.info(f"Table '{table_name}' created or already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating table '{table_name}': {str(e)}")
            raise
    
    async def batch_insert(
        self, 
        table_name: str, 
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Insert multiple rows into a table in batches.
        
        Args:
            table_name: Name of the target table
            data: List of row dictionaries to insert
            batch_size: Number of rows to insert in each batch
            
        Returns:
            Total number of inserted rows
        """
        if not data:
            return 0
        
        total_rows = 0
        
        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            
            if not batch:
                continue
                
            # Get column names from the first row
            columns = list(batch[0].keys())
            columns_str = ", ".join([f"`{col}`" for col in columns])
            
            # Create placeholders for values
            placeholders = ", ".join(["%s"] * len(columns))
            
            # Create SQL statement
            query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
            
            # Extract values in the correct order for each row
            values = []
            for row in batch:
                row_values = [row.get(col) for col in columns]
                values.append(row_values)
            
            try:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    rows_affected = cursor.executemany(query, values)
                    conn.commit()
                    total_rows += rows_affected
            except Exception as e:
                conn.rollback()
                logger.error(f"Error in batch insert: {str(e)}")
                raise
            
            # Pause briefly between batches to avoid overloading the server
            if i + batch_size < len(data):
                time.sleep(0.1)
        
        return total_rows
    
    async def load_dataframe(
        self, 
        table_name: str, 
        df: pd.DataFrame,
        batch_size: int = 1000
    ) -> int:
        """
        Load a pandas DataFrame into a table.
        
        Args:
            table_name: Name of the target table
            df: pandas DataFrame to load
            batch_size: Number of rows to insert in each batch
            
        Returns:
            Total number of inserted rows
        """
        # Convert DataFrame to list of dictionaries
        data = df.to_dict(orient="records")
        return await self.batch_insert(table_name, data, batch_size)


# Create a default client instance
default_starrocks_client = StarRocksClient()


def get_tenant_starrocks_client(tenant_id: str) -> StarRocksClient:
    """
    Get a StarRocks client for a specific tenant.
    
    Args:
        tenant_id: ID of the tenant
        
    Returns:
        A StarRocksClient instance for the tenant database
    """
    # In StarRocks, we use separate databases for tenant isolation
    database = f"tenant_{tenant_id}"
    return StarRocksClient(database=database)