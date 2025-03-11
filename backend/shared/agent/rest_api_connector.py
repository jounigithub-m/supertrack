"""
REST API connector implementation for external API integration.
"""

import logging
import json
import asyncio
import httpx
from typing import Any, Dict, List, Optional, Union, Tuple
import time
import uuid
import re
from urllib.parse import urlparse, urljoin

from .connector_agent import (
    ConnectorAgent,
    ConnectorType,
    ConnectionStatus,
    ConnectionConfig,
    ConnectorResult,
)
from .base_agent import AgentOptions, OpenAIModel

# Configure logging
logger = logging.getLogger(__name__)


class APIAuthType:
    """Authentication types for REST APIs."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class APIMethod:
    """HTTP methods for REST APIs."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class RestAPIConnector(ConnectorAgent):
    """
    Connector agent for REST APIs.
    
    This agent provides integration with external REST APIs,
    handling authentication, requests, and response parsing.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None,
        model: Optional[OpenAIModel] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        connection_config: Optional[ConnectionConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the REST API connector agent.
        
        Args:
            session_id: Optional ID for the session
            options: Optional configuration options
            model: OpenAI model instance
            tenant_id: ID of the tenant
            user_id: ID of the user
            connection_config: Configuration for the REST API connection
            system_prompt: Custom system prompt
        """
        super().__init__(
            session_id=session_id,
            options=options,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            connection_config=connection_config,
            system_prompt=system_prompt or self._get_rest_api_prompt(),
        )
        
        # HTTP client
        self.client = None
        
        # Saved endpoints
        self.endpoints = {}
        
        # Authentication information
        self.auth_headers = {}
        self.auth_params = {}
    
    def _get_rest_api_prompt(self) -> str:
        """
        Get the system prompt for the REST API connector.
        
        Returns:
            System prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        connect to and interact with external REST APIs. Follow these guidelines:
        
        1. Help users establish connections to REST APIs
        2. Assist with formulating API requests
        3. Format API responses in a clear and useful way
        4. Suggest optimizations for API usage
        5. Handle API errors and provide troubleshooting assistance
        
        You can help with:
        1. Configuring API connections with proper authentication
        2. Executing API requests with appropriate parameters
        3. Troubleshooting API connection issues
        4. Parsing and explaining API responses
        5. Constructing complex API requests
        
        Please provide clear and structured responses about API requests, responses,
        and any errors that occur.
        """
    
    async def connect(self) -> ConnectorResult:
        """
        Connect to the REST API.
        
        Returns:
            Result of the connection attempt
        """
        if not self.connection_config:
            return ConnectorResult.error_result("No connection configuration provided")
        
        try:
            # Update status
            self.connection_config.status = ConnectionStatus.CONNECTING
            
            # Get base URL from connection params
            base_url = self.connection_config.params.get("base_url")
            if not base_url:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = "Base URL is required"
                return ConnectorResult.error_result("Base URL is required")
            
            # Validate URL format
            try:
                parsed_url = urlparse(base_url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "Invalid URL format"
                    return ConnectorResult.error_result("Invalid URL format")
            except Exception as e:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = f"Invalid URL: {str(e)}"
                return ConnectorResult.error_result(f"Invalid URL: {str(e)}")
            
            # Create headers
            headers = self.connection_config.params.get("headers", {})
            
            # Set up authentication
            auth_type = self.connection_config.credentials.get("auth_type", APIAuthType.NONE)
            
            # Initialize auth headers and params
            self.auth_headers = {}
            self.auth_params = {}
            
            if auth_type == APIAuthType.API_KEY:
                api_key = self.connection_config.credentials.get("api_key")
                api_key_name = self.connection_config.credentials.get("api_key_name", "api_key")
                api_key_location = self.connection_config.credentials.get("api_key_location", "header")
                
                if not api_key:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "API key is required"
                    return ConnectorResult.error_result("API key is required")
                
                if api_key_location == "header":
                    self.auth_headers[api_key_name] = api_key
                else:
                    self.auth_params[api_key_name] = api_key
            
            elif auth_type == APIAuthType.BEARER_TOKEN:
                token = self.connection_config.credentials.get("token")
                
                if not token:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "Bearer token is required"
                    return ConnectorResult.error_result("Bearer token is required")
                
                self.auth_headers["Authorization"] = f"Bearer {token}"
            
            elif auth_type == APIAuthType.BASIC_AUTH:
                username = self.connection_config.credentials.get("username")
                password = self.connection_config.credentials.get("password")
                
                if not username or not password:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "Username and password are required"
                    return ConnectorResult.error_result("Username and password are required")
                
                # Basic auth is handled by httpx directly
                auth = (username, password)
            else:
                auth = None
            
            # Merge authentication headers with custom headers
            merged_headers = {**headers, **self.auth_headers}
            
            # Create HTTP client
            timeout = self.connection_config.params.get("timeout", 30.0)
            
            if auth_type == APIAuthType.BASIC_AUTH:
                self.client = httpx.AsyncClient(
                    base_url=base_url,
                    headers=merged_headers,
                    auth=auth,
                    timeout=timeout,
                )
            else:
                self.client = httpx.AsyncClient(
                    base_url=base_url,
                    headers=merged_headers,
                    timeout=timeout,
                )
            
            # Test connection with a simple request if health endpoint is provided
            health_endpoint = self.connection_config.params.get("health_endpoint")
            
            if health_endpoint:
                try:
                    response = await self.client.get(health_endpoint)
                    response.raise_for_status()
                except Exception as e:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = f"Failed health check: {str(e)}"
                    return ConnectorResult.error_result(f"Failed health check: {str(e)}")
            
            # Update connection status
            self.connection_config.status = ConnectionStatus.CONNECTED
            self.connection_config.last_connected = time.time()
            self.connection = self.client
            
            # Load endpoints if available
            endpoints = self.connection_config.params.get("endpoints", {})
            if endpoints:
                self.endpoints = endpoints
            
            return ConnectorResult.success_result(
                data={"message": "Connected successfully"},
                metadata={
                    "base_url": base_url,
                    "auth_type": auth_type,
                    "endpoints": list(self.endpoints.keys()),
                }
            )
        except Exception as e:
            logger.error(f"Error connecting to REST API: {str(e)}")
            self.connection_config.status = ConnectionStatus.ERROR
            self.connection_config.error = str(e)
            return ConnectorResult.error_result(f"Error connecting to REST API: {str(e)}")
    
    async def disconnect(self) -> ConnectorResult:
        """
        Disconnect from the REST API.
        
        Returns:
            Result of the disconnection attempt
        """
        if not self.client:
            return ConnectorResult.success_result({"message": "Already disconnected"})
        
        try:
            await self.client.aclose()
            self.client = None
            self.connection = None
            self.connection_config.status = ConnectionStatus.DISCONNECTED
            
            return ConnectorResult.success_result({"message": "Disconnected successfully"})
        except Exception as e:
            logger.error(f"Error disconnecting from REST API: {str(e)}")
            return ConnectorResult.error_result(f"Error disconnecting: {str(e)}")
    
    async def execute(self, **kwargs) -> ConnectorResult:
        """
        Execute a request to the REST API.
        
        Args:
            **kwargs: Parameters for the request
                - method: HTTP method (GET, POST, etc.)
                - path: API endpoint path
                - params: Query parameters
                - data: Request body for POST/PUT/PATCH
                - json: JSON request body for POST/PUT/PATCH
                - headers: Additional headers
            
        Returns:
            Result of the request
        """
        if not self.is_connected():
            return ConnectorResult.error_result("Not connected to REST API")
        
        try:
            # Get request parameters
            method = kwargs.get("method", "GET").upper()
            path = kwargs.get("path", "")
            params = kwargs.get("params", {})
            data = kwargs.get("data")
            json_data = kwargs.get("json")
            headers = kwargs.get("headers", {})
            endpoint_name = kwargs.get("endpoint")
            
            # Check if using a saved endpoint
            if endpoint_name and endpoint_name in self.endpoints:
                endpoint = self.endpoints[endpoint_name]
                method = endpoint.get("method", method)
                path = endpoint.get("path", path)
                
                # Merge parameters
                if "params" in endpoint:
                    endpoint_params = endpoint["params"]
                    # Replace {param} placeholders with values from kwargs
                    for key, value in endpoint_params.items():
                        if isinstance(value, str) and re.match(r'\{.+\}', value):
                            param_name = value[1:-1]  # Remove { }
                            if param_name in kwargs:
                                endpoint_params[key] = kwargs[param_name]
                    params = {**endpoint_params, **params}
                
                # Check for request body template
                if "body_template" in endpoint and json_data is None and data is None:
                    template = endpoint["body_template"]
                    json_data = template
                    
                    # Replace {param} placeholders with values from kwargs
                    if isinstance(json_data, dict):
                        json_data = self._process_template_dict(json_data, kwargs)
            
            # Merge authentication parameters
            params = {**self.auth_params, **params}
            
            # Make request
            try:
                if method == APIMethod.GET:
                    response = await self.client.get(path, params=params, headers=headers)
                elif method == APIMethod.POST:
                    response = await self.client.post(
                        path, params=params, data=data, json=json_data, headers=headers
                    )
                elif method == APIMethod.PUT:
                    response = await self.client.put(
                        path, params=params, data=data, json=json_data, headers=headers
                    )
                elif method == APIMethod.PATCH:
                    response = await self.client.patch(
                        path, params=params, data=data, json=json_data, headers=headers
                    )
                elif method == APIMethod.DELETE:
                    response = await self.client.delete(path, params=params, headers=headers)
                elif method == APIMethod.HEAD:
                    response = await self.client.head(path, params=params, headers=headers)
                elif method == APIMethod.OPTIONS:
                    response = await self.client.options(path, params=params, headers=headers)
                else:
                    return ConnectorResult.error_result(f"Unsupported HTTP method: {method}")
                
                # Parse response
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = response.text
                else:
                    response_data = response.text
                
                # Handle errors
                if response.status_code >= 400:
                    return ConnectorResult.error_result(
                        f"API error: {response.status_code} {response.reason_phrase}",
                        metadata={
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "data": response_data,
                        }
                    )
                
                return ConnectorResult.success_result(
                    data=response_data,
                    metadata={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                        "elapsed": response.elapsed.total_seconds(),
                    }
                )
            except httpx.RequestError as e:
                return ConnectorResult.error_result(
                    f"Request error: {str(e)}",
                    metadata={
                        "method": method,
                        "path": path,
                        "error_type": type(e).__name__,
                    }
                )
        except Exception as e:
            logger.error(f"Error executing REST API request: {str(e)}")
            return ConnectorResult.error_result(f"Error executing request: {str(e)}")
    
    async def query(self, **kwargs) -> ConnectorResult:
        """
        Query data from the REST API.
        
        This is a convenience alias for executing a GET request.
        
        Args:
            **kwargs: Parameters for the query
                - path: API endpoint path
                - params: Query parameters
                - headers: Additional headers
            
        Returns:
            Result of the query
        """
        # Set method to GET and delegate to execute
        kwargs["method"] = APIMethod.GET
        return await self.execute(**kwargs)
    
    async def get_metadata(self, **kwargs) -> ConnectorResult:
        """
        Get metadata about the REST API connection.
        
        Args:
            **kwargs: Parameters for the metadata retrieval
            
        Returns:
            Result containing metadata
        """
        metadata_type = kwargs.get("type", "connection")
        
        if metadata_type == "connection":
            # Return connection metadata
            if not self.connection_config:
                return ConnectorResult.error_result("No connection configuration available")
            
            return ConnectorResult.success_result(
                data={
                    "base_url": self.connection_config.params.get("base_url"),
                    "status": self.connection_config.status,
                    "auth_type": self.connection_config.credentials.get("auth_type", APIAuthType.NONE),
                    "last_connected": self.connection_config.last_connected,
                    "endpoints": list(self.endpoints.keys()),
                }
            )
        elif metadata_type == "endpoints":
            # Return endpoints information
            if not self.endpoints:
                return ConnectorResult.error_result("No endpoints available")
            
            sanitized_endpoints = {}
            for name, endpoint in self.endpoints.items():
                # Remove sensitive information
                sanitized_endpoint = {
                    "method": endpoint.get("method", "GET"),
                    "path": endpoint.get("path", ""),
                    "description": endpoint.get("description", ""),
                }
                
                sanitized_endpoints[name] = sanitized_endpoint
            
            return ConnectorResult.success_result(data=sanitized_endpoints)
        else:
            return ConnectorResult.error_result(f"Unsupported metadata type: {metadata_type}")
    
    def add_endpoint(self, name: str, endpoint_config: Dict[str, Any]) -> None:
        """
        Add a saved endpoint.
        
        Args:
            name: Name of the endpoint
            endpoint_config: Configuration for the endpoint
        """
        self.endpoints[name] = endpoint_config
    
    def _process_template_dict(self, template: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a template dictionary, replacing placeholders with parameter values.
        
        Args:
            template: Template dictionary
            params: Parameter values
            
        Returns:
            Processed dictionary
        """
        result = {}
        
        for key, value in template.items():
            if isinstance(value, dict):
                result[key] = self._process_template_dict(value, params)
            elif isinstance(value, list):
                result[key] = [
                    self._process_template_dict(item, params) if isinstance(item, dict) 
                    else item for item in value
                ]
            elif isinstance(value, str) and re.match(r'\{.+\}', value):
                param_name = value[1:-1]  # Remove { }
                if param_name in params:
                    result[key] = params[param_name]
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result