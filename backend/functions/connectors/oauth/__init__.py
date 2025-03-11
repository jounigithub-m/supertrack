"""
OAuth2 connector management endpoints for the Supertrack platform.

This Azure Function provides HTTP endpoints for:
1. Initiating OAuth2 authorization flows
2. Handling OAuth2 callbacks (redirect URIs)
3. Managing OAuth2 connections
"""

import logging
import json
import os
import uuid
import time
import asyncio
from typing import Dict, List, Optional, Union, Any
import azure.functions as func
from azure.cosmos import CosmosClient, PartitionKey
from urllib.parse import urlencode, parse_qs, urlparse

from backend.shared.auth import (
    validate_token_from_header,
    get_user_from_request,
    create_tenant_context_from_request,
    tenant_required,
)
from backend.shared.agent import (
    OAuth2Connector,
    MetaConnector,
    GoogleAdsConnector,
    ConnectorType,
    ConnectionConfig,
    ConnectionStatus,
    OAuth2FlowType,
)
from backend.shared.agent.session_manager import (
    SessionManager,
    CosmosDBSessionStorage,
    InMemorySessionStorage,
)

# Set up logging
logger = logging.getLogger("supertrack.connectors.oauth")

# Environment check
IS_PRODUCTION = os.environ.get("SUPERTRACK_ENV", "development") == "production"
IS_STAGING = os.environ.get("SUPERTRACK_ENV", "development") == "staging"
IS_DEVELOPMENT = not (IS_PRODUCTION or IS_STAGING)

# Azure Cosmos DB Configuration
COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT")
COSMOS_KEY = os.environ.get("COSMOS_KEY")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "supertrack")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER_CONNECTIONS", "connections")

# OAuth2 Configuration
OAUTH_REDIRECT_URI = os.environ.get(
    "OAUTH_REDIRECT_URI", 
    "http://localhost:7071/api/v1/connectors/oauth/callback"
)
OAUTH_FRONTEND_CALLBACK = os.environ.get(
    "OAUTH_FRONTEND_CALLBACK",
    "http://localhost:3000/connections/callback"
)

# Session manager instance
session_manager = None
cosmos_client = None
database = None
container = None

# Connection storage in memory for development if needed
memory_connections = {}

# Connector type mapping
CONNECTOR_TYPE_MAP = {
    "meta": MetaConnector,
    "facebook": MetaConnector,
    "instagram": MetaConnector,
    "google_ads": GoogleAdsConnector,
}

# Product type mapping for Meta
META_PRODUCT_TYPE_MAP = {
    "facebook_ads": "facebook_ads",
    "instagram_ads": "instagram_ads",
    "facebook": "facebook_organic",
    "instagram": "instagram_organic",
}

async def initialize_cosmos():
    """Initialize Cosmos DB client."""
    global cosmos_client, database, container
    
    if not cosmos_client and COSMOS_ENDPOINT and COSMOS_KEY:
        try:
            # Initialize Cosmos DB client
            cosmos_client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
            
            # Get or create database
            database = cosmos_client.get_database_client(COSMOS_DATABASE)
            
            # Get or create container
            try:
                container = database.get_container_client(COSMOS_CONTAINER)
                logger.info(f"Connected to container {COSMOS_CONTAINER}")
            except Exception:
                container = database.create_container(
                    id=COSMOS_CONTAINER,
                    partition_key=PartitionKey(path="/tenantId"),
                    offer_throughput=400
                )
                logger.info(f"Created container {COSMOS_CONTAINER}")
        except Exception as e:
            logger.error(f"Error initializing Cosmos DB: {str(e)}")
            cosmos_client = None
            database = None
            container = None

async def initialize_session_manager():
    """Initialize the session manager."""
    global session_manager
    
    if not session_manager:
        if IS_PRODUCTION or IS_STAGING:
            if not container:
                await initialize_cosmos()
            
            # Use Cosmos DB storage in production/staging
            if container:
                storage = CosmosDBSessionStorage(container)
            else:
                # Fallback to in-memory storage if Cosmos isn't configured
                storage = InMemorySessionStorage()
        else:
            # Use in-memory storage in development
            storage = InMemorySessionStorage()
        
        # Create session manager
        session_manager = SessionManager(storage)
        
        # Register connector types
        session_manager.register_agent_type("oauth2", OAuth2Connector)
        session_manager.register_agent_type("meta", MetaConnector)
        session_manager.register_agent_type("google_ads", GoogleAdsConnector)
        
        logger.info("Session manager initialized")

async def save_connection(tenant_id: str, user_id: str, connection_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a connection to storage.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        connection_data: Connection data
        
    Returns:
        Saved connection data
    """
    # Add tenant and user IDs
    connection_data["tenantId"] = tenant_id
    connection_data["userId"] = user_id
    
    # Add timestamps
    if "createdAt" not in connection_data:
        connection_data["createdAt"] = time.time()
    
    connection_data["updatedAt"] = time.time()
    
    if IS_PRODUCTION or IS_STAGING:
        if not container:
            await initialize_cosmos()
        
        if container:
            # Save to Cosmos DB
            try:
                if "id" in connection_data and connection_data["id"]:
                    # Update existing connection
                    response = container.upsert_item(body=connection_data)
                else:
                    # Create new connection
                    if "id" not in connection_data or not connection_data["id"]:
                        connection_data["id"] = str(uuid.uuid4())
                    
                    response = container.create_item(body=connection_data)
                
                logger.info(f"Saved connection {connection_data['id']} to Cosmos DB")
                return response
            except Exception as e:
                logger.error(f"Error saving connection to Cosmos DB: {str(e)}")
                if "memory_connections" not in globals():
                    global memory_connections
                    memory_connections = {}
                
                memory_connections[connection_data["id"]] = connection_data
                return connection_data
    else:
        # Save to memory
        if "id" not in connection_data or not connection_data["id"]:
            connection_data["id"] = str(uuid.uuid4())
        
        memory_connections[connection_data["id"]] = connection_data
        return connection_data

async def get_connection(tenant_id: str, connection_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a connection from storage.
    
    Args:
        tenant_id: Tenant ID
        connection_id: Connection ID
        
    Returns:
        Connection data or None if not found
    """
    if IS_PRODUCTION or IS_STAGING:
        if not container:
            await initialize_cosmos()
        
        if container:
            # Get from Cosmos DB
            try:
                query = f"SELECT * FROM c WHERE c.id = @id AND c.tenantId = @tenantId"
                parameters = [
                    {"name": "@id", "value": connection_id},
                    {"name": "@tenantId", "value": tenant_id}
                ]
                
                results = list(container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False
                ))
                
                if results:
                    return results[0]
                return None
            except Exception as e:
                logger.error(f"Error getting connection from Cosmos DB: {str(e)}")
                return memory_connections.get(connection_id)
    else:
        # Get from memory
        return memory_connections.get(connection_id)

async def list_connections(tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List connections for a tenant.
    
    Args:
        tenant_id: Tenant ID
        filters: Optional filters
        
    Returns:
        List of connections
    """
    if IS_PRODUCTION or IS_STAGING:
        if not container:
            await initialize_cosmos()
        
        if container:
            # Get from Cosmos DB
            try:
                query = "SELECT * FROM c WHERE c.tenantId = @tenantId"
                parameters = [{"name": "@tenantId", "value": tenant_id}]
                
                # Add filters if provided
                if filters:
                    for key, value in filters.items():
                        if key != "tenantId":
                            query += f" AND c.{key} = @{key}"
                            parameters.append({"name": f"@{key}", "value": value})
                
                results = list(container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False
                ))
                
                return results
            except Exception as e:
                logger.error(f"Error listing connections from Cosmos DB: {str(e)}")
                # Fallback to memory
                return [conn for conn in memory_connections.values() 
                        if conn.get("tenantId") == tenant_id and 
                        all(conn.get(k) == v for k, v in (filters or {}).items())]
    else:
        # Get from memory
        return [conn for conn in memory_connections.values() 
                if conn.get("tenantId") == tenant_id and 
                all(conn.get(k) == v for k, v in (filters or {}).items())]

async def delete_connection(tenant_id: str, connection_id: str) -> bool:
    """
    Delete a connection from storage.
    
    Args:
        tenant_id: Tenant ID
        connection_id: Connection ID
        
    Returns:
        True if deleted, False otherwise
    """
    if IS_PRODUCTION or IS_STAGING:
        if not container:
            await initialize_cosmos()
        
        if container:
            # Delete from Cosmos DB
            try:
                # First, get the connection to verify tenant
                connection = await get_connection(tenant_id, connection_id)
                
                if not connection:
                    return False
                
                # Delete the connection
                container.delete_item(item=connection_id, partition_key=tenant_id)
                logger.info(f"Deleted connection {connection_id} from Cosmos DB")
                
                # Also remove from memory cache if present
                if connection_id in memory_connections:
                    del memory_connections[connection_id]
                
                return True
            except Exception as e:
                logger.error(f"Error deleting connection from Cosmos DB: {str(e)}")
                
                # Try to delete from memory as fallback
                if connection_id in memory_connections:
                    conn = memory_connections[connection_id]
                    if conn.get("tenantId") == tenant_id:
                        del memory_connections[connection_id]
                        return True
                return False
    else:
        # Delete from memory
        if connection_id in memory_connections:
            conn = memory_connections[connection_id]
            if conn.get("tenantId") == tenant_id:
                del memory_connections[connection_id]
                return True
        return False

async def create_oauth_connector(connector_type: str, tenant_id: str, user_id: str, config: Dict[str, Any]) -> OAuth2Connector:
    """
    Create an OAuth2 connector instance.
    
    Args:
        connector_type: Type of connector
        tenant_id: Tenant ID
        user_id: User ID
        config: Configuration data
        
    Returns:
        OAuth2Connector instance
    """
    # Initialize session manager if needed
    if not session_manager:
        await initialize_session_manager()
    
    # Create connection config
    connection_config = ConnectionConfig(
        id=config.get("id", str(uuid.uuid4())),
        name=config.get("name", f"{connector_type.capitalize()} Connection"),
        connector_type=ConnectorType(config.get("connector_type", ConnectorType.REST_API)),
        params=config.get("params", {}),
        credentials=config.get("credentials", {}),
        metadata=config.get("metadata", {}),
    )
    
    # Set default redirect URI if not provided
    if "redirect_uri" not in connection_config.params:
        connection_config.params["redirect_uri"] = OAUTH_REDIRECT_URI
    
    # Create connector instance
    connector_class = CONNECTOR_TYPE_MAP.get(connector_type, OAuth2Connector)
    
    connector = connector_class(
        session_id=config.get("session_id"),
        tenant_id=tenant_id,
        user_id=user_id,
        connection_config=connection_config,
    )
    
    # Initialize the connector
    await connector.initialize()
    
    return connector

async def start_oauth_flow(tenant_id: str, user_id: str, connector_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start the OAuth2 flow.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        connector_type: Type of connector
        config: Configuration data
        
    Returns:
        Authorization URL and session data
    """
    # Create connector
    connector = await create_oauth_connector(connector_type, tenant_id, user_id, config)
    
    # Connect to start authorization
    result = await connector.connect()
    
    if not result.success:
        return {
            "success": False,
            "error": result.error,
            "metadata": result.metadata,
        }
    
    # Check if we need user authorization
    if result.metadata and result.metadata.get("requires_user_action"):
        # Get authorization URL and state
        auth_url = result.data.get("authorization_url")
        auth_state = result.data.get("auth_state")
        
        if not auth_url:
            return {
                "success": False,
                "error": "No authorization URL provided",
            }
        
        # Save connection state
        connection_data = {
            "id": connector.connection_config.id,
            "name": connector.connection_config.name,
            "connector_type": connector_type,
            "status": ConnectionStatus.CONNECTING,
            "auth_state": auth_state,
            "params": connector.connection_config.params,
            "credentials": connector.connection_config.credentials,
            "metadata": connector.connection_config.metadata,
            "session_id": connector.session_id,
        }
        
        await save_connection(tenant_id, user_id, connection_data)
        
        # Return authorization URL
        return {
            "success": True,
            "requires_authorization": True,
            "authorization_url": auth_url,
            "auth_state": auth_state,
            "connection_id": connector.connection_config.id,
        }
    else:
        # Already connected
        connection_data = {
            "id": connector.connection_config.id,
            "name": connector.connection_config.name,
            "connector_type": connector_type,
            "status": ConnectionStatus.CONNECTED,
            "params": connector.connection_config.params,
            "credentials": connector.connection_config.credentials,
            "metadata": connector.connection_config.metadata,
            "session_id": connector.session_id,
        }
        
        await save_connection(tenant_id, user_id, connection_data)
        
        return {
            "success": True,
            "requires_authorization": False,
            "message": "Connected successfully",
            "connection_id": connector.connection_config.id,
            "metadata": result.metadata,
        }

async def handle_oauth_callback(
    tenant_id: str, 
    user_id: str, 
    connection_id: str, 
    callback_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle the OAuth2 callback.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        connection_id: Connection ID
        callback_params: Callback parameters
        
    Returns:
        Result of the callback
    """
    # Get connection data
    connection_data = await get_connection(tenant_id, connection_id)
    
    if not connection_data:
        return {
            "success": False,
            "error": "Connection not found",
        }
    
    # Verify state parameter
    auth_state = connection_data.get("auth_state")
    callback_state = callback_params.get("state")
    
    if auth_state and callback_state and auth_state != callback_state:
        return {
            "success": False,
            "error": "Invalid state parameter",
        }
    
    # Create connector
    connector_type = connection_data.get("connector_type")
    
    connector = await create_oauth_connector(
        connector_type,
        tenant_id,
        user_id,
        connection_data
    )
    
    # Handle authorization response
    result = await connector.handle_authorization_response(callback_params)
    
    if not result.success:
        # Update connection status to error
        connection_data["status"] = ConnectionStatus.ERROR
        connection_data["error"] = result.error
        
        await save_connection(tenant_id, user_id, connection_data)
        
        return {
            "success": False,
            "error": result.error,
            "metadata": result.metadata,
        }
    
    # Update connection data
    connection_data["status"] = ConnectionStatus.CONNECTED
    connection_data["error"] = None
    connection_data["auth_state"] = None  # Clear auth state
    connection_data["credentials"] = connector.connection_config.credentials
    connection_data["last_connected"] = time.time()
    
    # Save updated connection
    await save_connection(tenant_id, user_id, connection_data)
    
    # Initialize account data for specific connector types
    if connector_type in ["meta", "facebook", "instagram", "google_ads"]:
        # Get account data
        account_result = await connector.get_metadata()
        
        if account_result.success and account_result.data:
            # Update metadata
            connection_data["metadata"].update(account_result.data)
            
            # Save again with account data
            await save_connection(tenant_id, user_id, connection_data)
    
    return {
        "success": True,
        "message": "Authorization successful",
        "connection_id": connection_id,
        "metadata": result.metadata,
    }

@tenant_required
async def handle_list_connections(req: func.HttpRequest, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to list connections.
    
    Args:
        req: HTTP request
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    # Parse query parameters
    status = req.params.get("status")
    connector_type = req.params.get("connector_type")
    
    # Build filters
    filters = {}
    if status:
        filters["status"] = status
    if connector_type:
        filters["connector_type"] = connector_type
    
    # Get connections
    connections = await list_connections(tenant_id, filters)
    
    # Sanitize sensitive information
    sanitized_connections = []
    for conn in connections:
        # Filter out sensitive data
        if "credentials" in conn:
            credentials = conn["credentials"].copy()
            for key in list(credentials.keys()):
                if key in ["client_secret", "api_key", "password", "token", "refresh_token"]:
                    credentials[key] = "[REDACTED]"
            conn = {**conn, "credentials": credentials}
        
        sanitized_connections.append(conn)
    
    return func.HttpResponse(
        json.dumps({"connections": sanitized_connections}),
        mimetype="application/json",
        status_code=200
    )

@tenant_required
async def handle_get_connection(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to get a connection.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    
    # Get connection
    connection = await get_connection(tenant_id, connection_id)
    
    if not connection:
        return func.HttpResponse(
            json.dumps({"error": "Connection not found"}),
            mimetype="application/json",
            status_code=404
        )
    
    # Sanitize sensitive information
    if "credentials" in connection:
        credentials = connection["credentials"].copy()
        for key in list(credentials.keys()):
            if key in ["client_secret", "api_key", "password", "token", "refresh_token"]:
                credentials[key] = "[REDACTED]"
        connection = {**connection, "credentials": credentials}
    
    return func.HttpResponse(
        json.dumps({"connection": connection}),
        mimetype="application/json",
        status_code=200
    )

@tenant_required
async def handle_create_connection(req: func.HttpRequest, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to create a connection.
    
    Args:
        req: HTTP request
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get required fields
        connector_type = req_body.get("connector_type")
        name = req_body.get("name")
        
        if not connector_type:
            return func.HttpResponse(
                json.dumps({"error": "connector_type is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        if not name:
            return func.HttpResponse(
                json.dumps({"error": "name is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Set OAuth2 configuration
        config = {
            "name": name,
            "connector_type": ConnectorType.REST_API,
            "params": req_body.get("params", {}),
            "credentials": req_body.get("credentials", {}),
            "metadata": req_body.get("metadata", {}),
        }
        
        # Handle special cases for Meta
        if connector_type in ["meta", "facebook", "instagram"]:
            # Add product types for Meta
            product_types = req_body.get("product_types", [])
            
            if not product_types:
                # Infer product type from connector type
                if connector_type == "facebook":
                    product_types = ["facebook_organic"]
                elif connector_type == "instagram":
                    product_types = ["instagram_organic"]
                elif connector_type == "meta":
                    product_types = ["facebook_ads", "instagram_ads"]
            
            # Map product types to Meta format
            meta_product_types = []
            for product_type in product_types:
                if product_type in META_PRODUCT_TYPE_MAP:
                    meta_product_types.append(META_PRODUCT_TYPE_MAP[product_type])
            
            config["params"]["product_types"] = meta_product_types
        
        # Start OAuth flow
        result = await start_oauth_flow(tenant_id, user_id, connector_type, config)
        
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error creating connection: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error creating connection: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_delete_connection(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle DELETE request to delete a connection.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    
    # Delete connection
    success = await delete_connection(tenant_id, connection_id)
    
    if not success:
        return func.HttpResponse(
            json.dumps({"error": "Connection not found or could not be deleted"}),
            mimetype="application/json",
            status_code=404
        )
    
    return func.HttpResponse(
        json.dumps({"success": True, "message": "Connection deleted successfully"}),
        mimetype="application/json",
        status_code=200
    )

async def handle_oauth_callback_request(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle OAuth2 callback request.
    
    Args:
        req: HTTP request
        
    Returns:
        HTTP response
    """
    # Get query parameters
    params = dict(req.params)
    connection_id = params.get("connection_id")
    
    # Additional parameters from URL fragment
    fragment = req.params.get("_fragment")
    if fragment:
        # Parse fragment parameters
        fragment_params = parse_qs(fragment)
        for key, value in fragment_params.items():
            if key not in params:
                params[key] = value[0] if len(value) == 1 else value
    
    if not connection_id:
        # Redirect to frontend with error
        redirect_url = f"{OAUTH_FRONTEND_CALLBACK}?error=missing_connection_id"
        return func.HttpResponse(
            body="",
            status_code=302,
            headers={"Location": redirect_url}
        )
    
    try:
        # Get connection data
        connection_data = None
        
        # Try all tenants (since we don't have tenant context in callback)
        if IS_PRODUCTION or IS_STAGING:
            if not container:
                await initialize_cosmos()
            
            if container:
                # Query Cosmos DB for this connection ID
                query = f"SELECT * FROM c WHERE c.id = @id"
                parameters = [{"name": "@id", "value": connection_id}]
                
                results = list(container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                if results:
                    connection_data = results[0]
        else:
            # Check memory connections
            if connection_id in memory_connections:
                connection_data = memory_connections[connection_id]
        
        if not connection_data:
            # Redirect to frontend with error
            redirect_url = f"{OAUTH_FRONTEND_CALLBACK}?error=connection_not_found&connection_id={connection_id}"
            return func.HttpResponse(
                body="",
                status_code=302,
                headers={"Location": redirect_url}
            )
        
        # Get tenant and user ID
        tenant_id = connection_data.get("tenantId")
        user_id = connection_data.get("userId")
        
        # Handle callback
        result = await handle_oauth_callback(tenant_id, user_id, connection_id, params)
        
        # Redirect to frontend
        redirect_params = {
            "connection_id": connection_id,
            "success": "true" if result.get("success") else "false",
        }
        
        if not result.get("success"):
            redirect_params["error"] = result.get("error", "Unknown error")
        
        redirect_url = f"{OAUTH_FRONTEND_CALLBACK}?{urlencode(redirect_params)}"
        
        return func.HttpResponse(
            body="",
            status_code=302,
            headers={"Location": redirect_url}
        )
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}")
        
        # Redirect to frontend with error
        redirect_url = f"{OAUTH_FRONTEND_CALLBACK}?error={str(e)}&connection_id={connection_id}"
        return func.HttpResponse(
            body="",
            status_code=302,
            headers={"Location": redirect_url}
        )

@tenant_required
async def handle_refresh_connection(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to refresh a connection.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    # Get connection
    connection_data = await get_connection(tenant_id, connection_id)
    
    if not connection_data:
        return func.HttpResponse(
            json.dumps({"error": "Connection not found"}),
            mimetype="application/json",
            status_code=404
        )
    
    try:
        # Create connector
        connector_type = connection_data.get("connector_type")
        
        connector = await create_oauth_connector(
            connector_type,
            tenant_id,
            user_id,
            connection_data
        )
        
        # Reconnect
        result = await connector.connect()
        
        if not result.success:
            # Update connection status to error
            connection_data["status"] = ConnectionStatus.ERROR
            connection_data["error"] = result.error
            
            await save_connection(tenant_id, user_id, connection_data)
            
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error": result.error,
                    "metadata": result.metadata,
                }),
                mimetype="application/json",
                status_code=200
            )
        
        # Check if we need user authorization
        if result.metadata and result.metadata.get("requires_user_action"):
            # Get authorization URL and state
            auth_url = result.data.get("authorization_url")
            auth_state = result.data.get("auth_state")
            
            if not auth_url:
                return func.HttpResponse(
                    json.dumps({
                        "success": False,
                        "error": "No authorization URL provided",
                    }),
                    mimetype="application/json",
                    status_code=200
                )
            
            # Update connection state
            connection_data["status"] = ConnectionStatus.CONNECTING
            connection_data["auth_state"] = auth_state
            
            await save_connection(tenant_id, user_id, connection_data)
            
            # Return authorization URL
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "requires_authorization": True,
                    "authorization_url": auth_url,
                    "auth_state": auth_state,
                    "connection_id": connection_id,
                }),
                mimetype="application/json",
                status_code=200
            )
        else:
            # Updated connection data
            connection_data["status"] = ConnectionStatus.CONNECTED
            connection_data["error"] = None
            connection_data["credentials"] = connector.connection_config.credentials
            connection_data["last_connected"] = time.time()
            
            # Save updated connection
            await save_connection(tenant_id, user_id, connection_data)
            
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "Connection refreshed successfully",
                    "metadata": result.metadata,
                }),
                mimetype="application/json",
                status_code=200
            )
    except Exception as e:
        logger.error(f"Error refreshing connection: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error refreshing connection: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_test_connection(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to test a connection.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    # Get connection
    connection_data = await get_connection(tenant_id, connection_id)
    
    if not connection_data:
        return func.HttpResponse(
            json.dumps({"error": "Connection not found"}),
            mimetype="application/json",
            status_code=404
        )
    
    try:
        # Create connector
        connector_type = connection_data.get("connector_type")
        
        connector = await create_oauth_connector(
            connector_type,
            tenant_id,
            user_id,
            connection_data
        )
        
        # Get metadata
        result = await connector.get_metadata()
        
        return func.HttpResponse(
            json.dumps({
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "metadata": result.metadata,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error testing connection: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main entry point for the Azure Function.
    
    Args:
        req: HTTP request
        
    Returns:
        HTTP response
    """
    # Get route segments
    route = req.route_params.get("route", "")
    segments = route.strip("/").split("/")
    
    # Initialize Cosmos DB
    await initialize_cosmos()
    
    # Handle callback route separately (no authentication required)
    if segments and segments[0] == "callback":
        return await handle_oauth_callback_request(req)
    
    # Validate token for other routes
    try:
        token_result = validate_token_from_header(req.headers)
        if not token_result["valid"]:
            return func.HttpResponse(
                json.dumps({"error": token_result["error"]}),
                mimetype="application/json",
                status_code=401
            )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"Authentication error: {str(e)}"}),
            mimetype="application/json",
            status_code=401
        )
    
    # Route request
    try:
        if req.method == "GET":
            if len(segments) == 0:
                # List connections
                return await handle_list_connections(req)
            else:
                # Get specific connection
                connection_id = segments[0]
                return await handle_get_connection(req, connection_id)
        elif req.method == "POST":
            if len(segments) == 0:
                # Create connection
                return await handle_create_connection(req)
            elif len(segments) > 1 and segments[1] == "refresh":
                # Refresh connection
                connection_id = segments[0]
                return await handle_refresh_connection(req, connection_id)
            elif len(segments) > 1 and segments[1] == "test":
                # Test connection
                connection_id = segments[0]
                return await handle_test_connection(req, connection_id)
        elif req.method == "DELETE":
            if len(segments) > 0:
                # Delete connection
                connection_id = segments[0]
                return await handle_delete_connection(req, connection_id)
        
        return func.HttpResponse(
            json.dumps({"error": "Not found"}),
            mimetype="application/json",
            status_code=404
        )
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error handling request: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )