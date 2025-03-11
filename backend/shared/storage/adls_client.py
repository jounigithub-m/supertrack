"""
Azure Data Lake Storage Gen2 client for file storage operations.
"""

import logging
import os
import io
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple
import json
import pandas as pd

from azure.storage.filedatalake import (
    DataLakeServiceClient,
    DataLakeDirectoryClient,
    DataLakeFileClient,
    ContentSettings
)
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from ..utils.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class ADLSClient:
    """
    Client for Azure Data Lake Storage Gen2 operations.
    
    This client provides methods for file and directory operations on Azure Data Lake Storage,
    with support for tenant isolation and hierarchical file structures.
    """
    
    def __init__(
        self, 
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        file_system_name: str = "supertrack",
        tenant_id: Optional[str] = None
    ):
        """
        Initialize the ADLS client.
        
        Args:
            connection_string: Optional connection string for Azure Storage.
            account_name: Optional storage account name (used if connection_string is not provided).
            account_key: Optional storage account key (used if connection_string is not provided).
            file_system_name: Name of the file system (container).
            tenant_id: Optional tenant ID for tenant isolation.
        """
        self.connection_string = connection_string or settings.storage_connection_string
        self.account_name = account_name or settings.storage_account_name
        self.account_key = account_key or settings.storage_account_key
        self.file_system_name = file_system_name
        self.tenant_id = tenant_id
        
        # Initialize clients
        self.service_client = self._create_service_client()
        self.file_system_client = self._get_file_system_client()
    
    def _create_service_client(self) -> DataLakeServiceClient:
        """Create and return a Data Lake service client."""
        try:
            if self.connection_string:
                return DataLakeServiceClient.from_connection_string(self.connection_string)
            else:
                # Use account name and key
                account_url = f"https://{self.account_name}.dfs.core.windows.net"
                return DataLakeServiceClient(account_url, credential=self.account_key)
        except Exception as e:
            logger.error(f"Error creating ADLS service client: {str(e)}")
            raise
    
    def _get_file_system_client(self):
        """Get a file system (container) client."""
        return self.service_client.get_file_system_client(self.file_system_name)
    
    def _get_tenant_path(self, path: str) -> str:
        """
        Get the full path including tenant prefix if a tenant ID is set.
        
        Args:
            path: The relative path
            
        Returns:
            The full path with tenant prefix if applicable
        """
        if self.tenant_id:
            # Ensure path doesn't start with a slash
            path = path.lstrip("/")
            return f"tenants/{self.tenant_id}/{path}"
        return path
    
    async def create_file_system(self) -> bool:
        """
        Create the file system (container) if it doesn't exist.
        
        Returns:
            True if file system was created or already exists
        """
        try:
            self.file_system_client.create_file_system()
            logger.info(f"File system '{self.file_system_name}' created")
            return True
        except ResourceExistsError:
            logger.debug(f"File system '{self.file_system_name}' already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating file system '{self.file_system_name}': {str(e)}")
            raise
    
    async def delete_file_system(self) -> bool:
        """
        Delete the file system (container).
        
        Returns:
            True if file system was deleted
        """
        try:
            self.file_system_client.delete_file_system()
            logger.info(f"File system '{self.file_system_name}' deleted")
            return True
        except ResourceNotFoundError:
            logger.warning(f"File system '{self.file_system_name}' not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting file system '{self.file_system_name}': {str(e)}")
            raise
    
    async def create_directory(self, directory_path: str) -> bool:
        """
        Create a directory if it doesn't exist.
        
        Args:
            directory_path: Path of the directory to create
            
        Returns:
            True if directory was created or already exists
        """
        full_path = self._get_tenant_path(directory_path)
        
        try:
            directory_client = self.file_system_client.get_directory_client(full_path)
            directory_client.create_directory()
            logger.info(f"Directory '{full_path}' created")
            return True
        except ResourceExistsError:
            logger.debug(f"Directory '{full_path}' already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating directory '{full_path}': {str(e)}")
            raise
    
    async def create_directory_recursively(self, directory_path: str) -> bool:
        """
        Create a directory and all parent directories if they don't exist.
        
        Args:
            directory_path: Path of the directory to create
            
        Returns:
            True if all directories were created or already exist
        """
        full_path = self._get_tenant_path(directory_path)
        
        # Split path into components
        path_parts = full_path.strip("/").split("/")
        current_path = ""
        
        for part in path_parts:
            if part:
                current_path = f"{current_path}/{part}" if current_path else part
                await self.create_directory(current_path)
        
        return True
    
    async def delete_directory(self, directory_path: str, recursive: bool = True) -> bool:
        """
        Delete a directory.
        
        Args:
            directory_path: Path of the directory to delete
            recursive: Whether to delete subdirectories and files
            
        Returns:
            True if directory was deleted
        """
        full_path = self._get_tenant_path(directory_path)
        
        try:
            directory_client = self.file_system_client.get_directory_client(full_path)
            directory_client.delete_directory(recursive=recursive)
            logger.info(f"Directory '{full_path}' deleted")
            return True
        except ResourceNotFoundError:
            logger.warning(f"Directory '{full_path}' not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting directory '{full_path}': {str(e)}")
            raise
    
    async def upload_file(
        self, 
        file_path: str, 
        data: Union[str, bytes, BinaryIO],
        content_type: Optional[str] = None,
        overwrite: bool = True
    ) -> bool:
        """
        Upload a file to Data Lake Storage.
        
        Args:
            file_path: Path where the file should be stored
            data: File data as string, bytes, or file-like object
            content_type: Optional MIME type of the content
            overwrite: Whether to overwrite existing file
            
        Returns:
            True if file was uploaded successfully
        """
        full_path = self._get_tenant_path(file_path)
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            await self.create_directory_recursively(parent_dir)
        
        # Prepare data for upload
        if isinstance(data, str):
            data = data.encode('utf-8')
            if not content_type:
                content_type = 'text/plain'
        
        # Set content settings if content type is provided
        content_settings = None
        if content_type:
            content_settings = ContentSettings(content_type=content_type)
        
        try:
            file_client = self.file_system_client.get_file_client(full_path)
            
            if isinstance(data, (bytes, bytearray)):
                file_client.upload_data(data, overwrite=overwrite, content_settings=content_settings)
            else:
                # Assume file-like object
                file_client.upload_data(data.read(), overwrite=overwrite, content_settings=content_settings)
                
            logger.info(f"File '{full_path}' uploaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error uploading file '{full_path}': {str(e)}")
            raise
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download a file from Data Lake Storage.
        
        Args:
            file_path: Path of the file to download
            
        Returns:
            File content as bytes
        """
        full_path = self._get_tenant_path(file_path)
        
        try:
            file_client = self.file_system_client.get_file_client(full_path)
            
            # Download the file
            download = file_client.download_file()
            data = download.readall()
            
            logger.info(f"File '{full_path}' downloaded successfully")
            return data
        except ResourceNotFoundError:
            logger.error(f"File '{full_path}' not found")
            raise
        except Exception as e:
            logger.error(f"Error downloading file '{full_path}': {str(e)}")
            raise
    
    async def download_file_as_text(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Download a file from Data Lake Storage and decode as text.
        
        Args:
            file_path: Path of the file to download
            encoding: Text encoding to use
            
        Returns:
            File content as string
        """
        data = await self.download_file(file_path)
        return data.decode(encoding)
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from Data Lake Storage.
        
        Args:
            file_path: Path of the file to delete
            
        Returns:
            True if file was deleted
        """
        full_path = self._get_tenant_path(file_path)
        
        try:
            file_client = self.file_system_client.get_file_client(full_path)
            file_client.delete_file()
            logger.info(f"File '{full_path}' deleted successfully")
            return True
        except ResourceNotFoundError:
            logger.warning(f"File '{full_path}' not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting file '{full_path}': {str(e)}")
            raise
    
    async def list_directory(
        self, 
        directory_path: str, 
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List files and directories in a directory.
        
        Args:
            directory_path: Path of the directory to list
            recursive: Whether to list subdirectories recursively
            
        Returns:
            List of file and directory items
        """
        full_path = self._get_tenant_path(directory_path)
        
        try:
            directory_client = self.file_system_client.get_directory_client(full_path)
            
            paths = directory_client.get_paths(recursive=recursive)
            items = []
            
            for path in paths:
                # Extract the name from the full path
                name = path.name.split('/')[-1] if path.name else ''
                
                item = {
                    "name": name,
                    "full_path": path.name,
                    "is_directory": path.is_directory,
                    "size": path.content_length if not path.is_directory else None,
                    "last_modified": path.last_modified,
                }
                items.append(item)
            
            return items
        except ResourceNotFoundError:
            logger.warning(f"Directory '{full_path}' not found")
            return []
        except Exception as e:
            logger.error(f"Error listing directory '{full_path}': {str(e)}")
            raise
    
    async def upload_json(
        self, 
        file_path: str, 
        data: Dict[str, Any],
        overwrite: bool = True
    ) -> bool:
        """
        Upload JSON data to a file.
        
        Args:
            file_path: Path where the file should be stored
            data: JSON-serializable data
            overwrite: Whether to overwrite existing file
            
        Returns:
            True if file was uploaded successfully
        """
        json_str = json.dumps(data, indent=2)
        return await self.upload_file(
            file_path=file_path,
            data=json_str,
            content_type='application/json',
            overwrite=overwrite
        )
    
    async def download_json(self, file_path: str) -> Dict[str, Any]:
        """
        Download and parse a JSON file.
        
        Args:
            file_path: Path of the JSON file to download
            
        Returns:
            Parsed JSON data
        """
        json_str = await self.download_file_as_text(file_path)
        return json.loads(json_str)
    
    async def upload_dataframe(
        self, 
        file_path: str, 
        df: pd.DataFrame,
        format: str = 'csv',
        overwrite: bool = True,
        **kwargs
    ) -> bool:
        """
        Upload a pandas DataFrame to a file.
        
        Args:
            file_path: Path where the file should be stored
            df: pandas DataFrame to upload
            format: Format to save ('csv', 'parquet', or 'json')
            overwrite: Whether to overwrite existing file
            **kwargs: Additional arguments for DataFrame export function
            
        Returns:
            True if file was uploaded successfully
        """
        buffer = io.BytesIO()
        
        if format.lower() == 'csv':
            df.to_csv(buffer, index=False, **kwargs)
            content_type = 'text/csv'
        elif format.lower() == 'parquet':
            df.to_parquet(buffer, index=False, **kwargs)
            content_type = 'application/octet-stream'
        elif format.lower() == 'json':
            df.to_json(buffer, orient='records', **kwargs)
            content_type = 'application/json'
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        buffer.seek(0)
        
        return await self.upload_file(
            file_path=file_path,
            data=buffer,
            content_type=content_type,
            overwrite=overwrite
        )
    
    async def download_dataframe(
        self, 
        file_path: str, 
        format: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Download and parse a file into a pandas DataFrame.
        
        Args:
            file_path: Path of the file to download
            format: Format of the file ('csv', 'parquet', or 'json')
            **kwargs: Additional arguments for pandas read function
            
        Returns:
            pandas DataFrame
        """
        # If format is not specified, try to determine from file extension
        if not format:
            _, ext = os.path.splitext(file_path)
            format = ext.lstrip('.').lower()
        
        data = await self.download_file(file_path)
        buffer = io.BytesIO(data)
        
        if format.lower() == 'csv':
            return pd.read_csv(buffer, **kwargs)
        elif format.lower() == 'parquet':
            return pd.read_parquet(buffer, **kwargs)
        elif format.lower() == 'json':
            return pd.read_json(buffer, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Create a default client instance
default_adls_client = ADLSClient()


def get_tenant_adls_client(tenant_id: str) -> ADLSClient:
    """
    Get an ADLS client for a specific tenant.
    
    Args:
        tenant_id: ID of the tenant
        
    Returns:
        An ADLSClient instance with tenant isolation
    """
    return ADLSClient(tenant_id=tenant_id)