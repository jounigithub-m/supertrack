"""
Connector operations endpoints for the Supertrack platform.

This Azure Function provides endpoints for performing operations on connectors:
1. Executing queries against external systems
2. Getting metadata from connected systems
3. Running specific connector actions
4. Handling state management for connector sessions
"""

import logging
import json
import os
import time
import asyncio
from typing import Dict, List, Optional, Union, Any
import azure.functions as func

from backend.shared.auth import (
    validate_token_from_header,
    get_user_from_request,
    create_tenant_context_from_request,
    tenant_required,
)
from backend.shared.agent import (
    ConnectorAgent,
    MetaConnector,
    GoogleAdsConnector,
    ConnectorType,
    ConnectionConfig,
    ConnectionStatus,
    ConnectorResult,
)
from backend.shared.agent.session_manager import (
    SessionManager,
    CosmosDBSessionStorage,
    InMemorySessionStorage,
)

# Set up logging
logger = logging.getLogger("supertrack.connectors.operations")

# Environment check
IS_PRODUCTION = os.environ.get("SUPERTRACK_ENV", "development") == "production"
IS_STAGING = os.environ.get("SUPERTRACK_ENV", "development") == "staging"
IS_DEVELOPMENT = not (IS_PRODUCTION or IS_STAGING)

# Azure Cosmos DB Configuration
COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT")
COSMOS_KEY = os.environ.get("COSMOS_KEY")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "supertrack")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER_CONNECTIONS", "connections")

# Session manager instance
session_manager = None

# Connector type mapping
CONNECTOR_TYPE_MAP = {
    "meta": MetaConnector,
    "facebook": MetaConnector,
    "instagram": MetaConnector,
    "google_ads": GoogleAdsConnector,
}

async def initialize_session_manager():
    """Initialize the session manager."""
    global session_manager
    
    if not session_manager:
        if IS_PRODUCTION or IS_STAGING:
            # Use Cosmos DB storage in production/staging
            if COSMOS_ENDPOINT and COSMOS_KEY:
                try:
                    # Initialize Cosmos DB client
                    from azure.cosmos import CosmosClient, PartitionKey
                    
                    # Create client
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
                    
                    # Use Cosmos DB storage
                    storage = CosmosDBSessionStorage(container)
                except Exception as e:
                    logger.error(f"Error initializing Cosmos DB: {str(e)}")
                    # Fallback to in-memory storage
                    storage = InMemorySessionStorage()
            else:
                # Fallback to in-memory storage
                storage = InMemorySessionStorage()
        else:
            # Use in-memory storage in development
            storage = InMemorySessionStorage()
        
        # Create session manager
        session_manager = SessionManager(storage)
        
        # Register connector types
        session_manager.register_agent_type("connector", ConnectorAgent)
        session_manager.register_agent_type("meta", MetaConnector)
        session_manager.register_agent_type("google_ads", GoogleAdsConnector)
        
        logger.info("Session manager initialized")

async def get_connection_from_cosmos(tenant_id: str, connection_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a connection from Cosmos DB.
    
    Args:
        tenant_id: Tenant ID
        connection_id: Connection ID
        
    Returns:
        Connection data or None if not found
    """
    if COSMOS_ENDPOINT and COSMOS_KEY:
        try:
            # Initialize Cosmos DB client
            from azure.cosmos import CosmosClient
            
            # Create client
            cosmos_client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
            
            # Get database
            database = cosmos_client.get_database_client(COSMOS_DATABASE)
            
            # Get container
            container = database.get_container_client(COSMOS_CONTAINER)
            
            # Query for connection
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
        except Exception as e:
            logger.error(f"Error getting connection from Cosmos DB: {str(e)}")
    
    return None

async def create_connector_from_connection(
    tenant_id: str, 
    user_id: str, 
    connection_id: str, 
    session_id: Optional[str] = None
) -> Optional[ConnectorAgent]:
    """
    Create a connector from a connection.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        connection_id: Connection ID
        session_id: Optional session ID
        
    Returns:
        Connector instance or None if not found
    """
    # Initialize session manager
    if not session_manager:
        await initialize_session_manager()
    
    # Get connection data
    connection_data = await get_connection_from_cosmos(tenant_id, connection_id)
    
    if not connection_data:
        return None
    
    # Check connection status
    status = connection_data.get("status")
    if status != ConnectionStatus.CONNECTED:
        logger.warning(f"Connection {connection_id} is not connected (status: {status})")
        return None
    
    # Get connector type
    connector_type = connection_data.get("connector_type")
    if not connector_type or connector_type not in CONNECTOR_TYPE_MAP:
        logger.error(f"Unknown connector type: {connector_type}")
        return None
    
    # Create connection config
    connection_config = ConnectionConfig(
        id=connection_data.get("id"),
        name=connection_data.get("name", f"{connector_type.capitalize()} Connection"),
        connector_type=ConnectorType(connection_data.get("connector_type", ConnectorType.REST_API)),
        params=connection_data.get("params", {}),
        credentials=connection_data.get("credentials", {}),
        metadata=connection_data.get("metadata", {}),
    )
    
    # Create connector instance
    connector_class = CONNECTOR_TYPE_MAP.get(connector_type)
    
    connector = connector_class(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        connection_config=connection_config,
    )
    
    # Initialize the connector
    await connector.initialize()
    
    return connector

@tenant_required
async def handle_query(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to query a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get query parameters
        query = req_body.get("query")
        parameters = req_body.get("parameters", {})
        session_id = req_body.get("session_id")
        
        if not query:
            return func.HttpResponse(
                json.dumps({"error": "query is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Create connector
        connector = await create_connector_from_connection(
            tenant_id,
            user_id,
            connection_id,
            session_id
        )
        
        if not connector:
            return func.HttpResponse(
                json.dumps({"error": "Connection not found or not connected"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Execute query
        result = await connector.query(query, parameters)
        
        return func.HttpResponse(
            json.dumps({
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "metadata": result.metadata,
                "session_id": connector.session_id,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error executing query: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_execute(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to execute an operation on a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get operation parameters
        operation = req_body.get("operation")
        parameters = req_body.get("parameters", {})
        session_id = req_body.get("session_id")
        
        if not operation:
            return func.HttpResponse(
                json.dumps({"error": "operation is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Create connector
        connector = await create_connector_from_connection(
            tenant_id,
            user_id,
            connection_id,
            session_id
        )
        
        if not connector:
            return func.HttpResponse(
                json.dumps({"error": "Connection not found or not connected"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Execute operation
        result = await connector.execute(operation, parameters)
        
        return func.HttpResponse(
            json.dumps({
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "metadata": result.metadata,
                "session_id": connector.session_id,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error executing operation: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error executing operation: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_metadata(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to get metadata from a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Get query parameters
        session_id = req.params.get("session_id")
        refresh = req.params.get("refresh", "false").lower() == "true"
        
        # Create connector
        connector = await create_connector_from_connection(
            tenant_id,
            user_id,
            connection_id,
            session_id
        )
        
        if not connector:
            return func.HttpResponse(
                json.dumps({"error": "Connection not found or not connected"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Get metadata
        result = await connector.get_metadata(refresh=refresh)
        
        return func.HttpResponse(
            json.dumps({
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "metadata": result.metadata,
                "session_id": connector.session_id,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error getting metadata: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error getting metadata: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_message(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to send a message to a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get message parameters
        message = req_body.get("message")
        session_id = req_body.get("session_id")
        
        if not message:
            return func.HttpResponse(
                json.dumps({"error": "message is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Create connector
        connector = await create_connector_from_connection(
            tenant_id,
            user_id,
            connection_id,
            session_id
        )
        
        if not connector:
            return func.HttpResponse(
                json.dumps({"error": "Connection not found or not connected"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Process message
        result = await connector.process_message(message)
        
        return func.HttpResponse(
            json.dumps({
                "message": result,
                "session_id": connector.session_id,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error processing message: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_session_state(req: func.HttpRequest, connection_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to get session state from a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Get session ID
        session_id = req.params.get("session_id")
        
        if not session_id:
            return func.HttpResponse(
                json.dumps({"error": "session_id is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Initialize session manager
        if not session_manager:
            await initialize_session_manager()
        
        # Get session
        session = await session_manager.get_session(session_id)
        
        if not session:
            return func.HttpResponse(
                json.dumps({"error": "Session not found"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Check if session belongs to this tenant
        if session.tenant_id != tenant_id:
            return func.HttpResponse(
                json.dumps({"error": "Session not found for this tenant"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Get agent
        agent = session.agent
        
        if not agent or not isinstance(agent, ConnectorAgent):
            return func.HttpResponse(
                json.dumps({"error": "No connector agent found in session"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Get session state
        state = agent.get_session_state()
        
        return func.HttpResponse(
            json.dumps({
                "session_id": session_id,
                "state": state,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error getting session state: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error getting session state: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

@tenant_required
async def handle_set_active_account(
    req: func.HttpRequest, 
    connection_id: str, 
    tenant_context=None
) -> func.HttpResponse:
    """
    Handle POST request to set active account for a connector.
    
    Args:
        req: HTTP request
        connection_id: Connection ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    tenant_id = tenant_context.tenant_id
    user_id = tenant_context.user_id
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get account parameters
        account_id = req_body.get("account_id")
        session_id = req_body.get("session_id")
        
        if not account_id:
            return func.HttpResponse(
                json.dumps({"error": "account_id is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Create connector
        connector = await create_connector_from_connection(
            tenant_id,
            user_id,
            connection_id,
            session_id
        )
        
        if not connector:
            return func.HttpResponse(
                json.dumps({"error": "Connection not found or not connected"}),
                mimetype="application/json",
                status_code=404
            )
        
        # Check if connector has set_active_account method
        if not hasattr(connector, "set_active_account"):
            return func.HttpResponse(
                json.dumps({"error": "Connector does not support setting active account"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Set active account
        result = await connector.set_active_account(account_id)
        
        return func.HttpResponse(
            json.dumps({
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "metadata": result.metadata,
                "session_id": connector.session_id,
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error setting active account: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error setting active account: {str(e)}"}),
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
    
    # Validate token
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
        if len(segments) < 1:
            return func.HttpResponse(
                json.dumps({"error": "Missing connection ID"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Get connection ID
        connection_id = segments[0]
        
        # Route based on operation
        if len(segments) < 2:
            return func.HttpResponse(
                json.dumps({"error": "Missing operation"}),
                mimetype="application/json",
                status_code=400
            )
        
        operation = segments[1]
        
        if operation == "query" and req.method == "POST":
            return await handle_query(req, connection_id)
        elif operation == "execute" and req.method == "POST":
            return await handle_execute(req, connection_id)
        elif operation == "metadata" and req.method == "GET":
            return await handle_metadata(req, connection_id)
        elif operation == "message" and req.method == "POST":
            return await handle_message(req, connection_id)
        elif operation == "state" and req.method == "GET":
            return await handle_session_state(req, connection_id)
        elif operation == "account" and req.method == "POST":
            return await handle_set_active_account(req, connection_id)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown operation: {operation}"}),
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