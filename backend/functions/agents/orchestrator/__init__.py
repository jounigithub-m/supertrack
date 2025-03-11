"""
Azure Function endpoint for the orchestrator agent API.
"""

import logging
import json
import azure.functions as func
import asyncio
from typing import Dict, Any, Optional, List
import time
import os

from backend.shared.agent import (
    AgentType,
    AgentOptions,
    OrchestratorAgent,
    Task,
    Workflow,
    WorkflowStatus,
    OpenAIModel,
    SessionManager,
    InMemorySessionStorage,
    CosmosDBSessionStorage,
)
from backend.shared.auth import (
    validate_token_from_header,
    get_user_from_request,
    create_tenant_context_from_request,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize session manager (global instance)
storage_provider = None
session_manager = None


async def initialize_session_manager():
    """Initialize the session manager if not already initialized."""
    global storage_provider, session_manager
    
    if session_manager is not None:
        return session_manager
    
    # Determine which storage provider to use based on environment
    env = os.environ.get("ENVIRONMENT", "development")
    
    if env == "production" or env == "staging":
        # Use CosmosDB in production and staging
        cosmos_connection_string = os.environ.get("COSMOSDB_CONNECTION_STRING")
        cosmos_database = os.environ.get("COSMOSDB_DATABASE", "supertrack")
        cosmos_container = os.environ.get("COSMOSDB_SESSIONS_CONTAINER", "agent_sessions")
        
        storage_provider = CosmosDBSessionStorage(
            connection_string=cosmos_connection_string,
            database_name=cosmos_database,
            container_name=cosmos_container,
        )
    else:
        # Use in-memory storage for development
        storage_provider = InMemorySessionStorage()
    
    # Create session manager
    session_manager = SessionManager(storage_provider)
    
    # Register agent types
    session_manager.register_agent_factory(AgentType.ORCHESTRATOR, OrchestratorAgent)
    session_manager.register_agent_factory(AgentType.QUERY, lambda **kwargs: kwargs)
    session_manager.register_agent_factory(AgentType.METADATA_EXTRACTION, lambda **kwargs: kwargs)
    
    # Initialize session manager
    await session_manager.initialize()
    
    return session_manager


async def create_orchestrator_agent(tenant_id: str, user_id: str) -> OrchestratorAgent:
    """
    Create a new orchestrator agent.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        
    Returns:
        The created orchestrator agent
    """
    # Get session manager
    session_manager = await initialize_session_manager()
    
    # Create OpenAI model
    model = OpenAIModel()
    await model.initialize()
    
    # Create agent options
    options = AgentOptions(
        temperature=0.0,
        timeout=60.0,
    )
    
    # Create metadata
    metadata = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "created_at": time.time(),
    }
    
    # Create agent
    agent = await session_manager.create_session(
        agent_type=AgentType.ORCHESTRATOR,
        options=options,
        metadata=metadata,
        model=model,
        tenant_id=tenant_id,
        user_id=user_id,
        session_manager=session_manager,
    )
    
    return agent


async def get_orchestrator_agent(session_id: str) -> Optional[OrchestratorAgent]:
    """
    Get an existing orchestrator agent.
    
    Args:
        session_id: Session ID
        
    Returns:
        The orchestrator agent or None if not found
    """
    # Get session manager
    session_manager = await initialize_session_manager()
    
    # Get agent
    agent = await session_manager.get_session(session_id)
    
    if agent and agent.agent_type == AgentType.ORCHESTRATOR:
        # Initialize session manager if needed
        if agent.session_manager is None:
            agent.session_manager = session_manager
        
        return agent
    
    return None


def parse_workflow_definition(workflow_data: Dict[str, Any]) -> Workflow:
    """
    Parse a workflow definition from request data.
    
    Args:
        workflow_data: Workflow data from request
        
    Returns:
        Parsed workflow
        
    Raises:
        ValueError: If the workflow definition is invalid
    """
    if not workflow_data.get("id"):
        raise ValueError("Workflow ID is required")
    
    if not workflow_data.get("name"):
        raise ValueError("Workflow name is required")
    
    # Parse tasks
    tasks = []
    for task_data in workflow_data.get("tasks", []):
        if not task_data.get("id"):
            raise ValueError("Task ID is required")
        
        if not task_data.get("agent_type"):
            raise ValueError("Task agent_type is required")
        
        task = Task(
            id=task_data["id"],
            agent_type=AgentType(task_data["agent_type"]),
            name=task_data.get("name"),
            description=task_data.get("description"),
            params=task_data.get("params", {}),
            dependencies=task_data.get("dependencies", []),
            timeout=task_data.get("timeout"),
            retry_limit=task_data.get("retry_limit", 3),
        )
        tasks.append(task)
    
    # Create workflow
    workflow = Workflow(
        id=workflow_data["id"],
        name=workflow_data["name"],
        description=workflow_data.get("description"),
        tasks=tasks,
        metadata=workflow_data.get("metadata", {}),
    )
    
    return workflow


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point.
    
    Args:
        req: HTTP request
        
    Returns:
        HTTP response
    """
    logger.info('Orchestrator agent function processed a request.')
    
    # Validate token
    try:
        token_claims = validate_token_from_header(req)
        user = get_user_from_request(req)
        
        # Create tenant context
        async with create_tenant_context_from_request(req) as tenant_context:
            tenant_id = tenant_context.tenant_id
            
            # Handle different HTTP methods
            if req.method == "POST":
                return await handle_post(req, tenant_id, user["id"])
            elif req.method == "GET":
                return await handle_get(req, tenant_id, user["id"])
            else:
                return func.HttpResponse(
                    body=json.dumps({"error": "Method not allowed"}),
                    status_code=405,
                    mimetype="application/json"
                )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def handle_post(req: func.HttpRequest, tenant_id: str, user_id: str) -> func.HttpResponse:
    """
    Handle POST requests.
    
    Args:
        req: HTTP request
        tenant_id: Tenant ID
        user_id: User ID
        
    Returns:
        HTTP response
    """
    try:
        # Parse request body
        req_body = req.get_json()
        
        # Check if session_id is provided
        session_id = req_body.get("session_id")
        message = req_body.get("message", "")
        
        # Get workflow action
        workflow_action = req_body.get("workflow_action")
        workflow_id = req_body.get("workflow_id")
        workflow_definition = req_body.get("workflow_definition")
        
        # Get or create agent
        if session_id:
            # Get existing agent
            agent = await get_orchestrator_agent(session_id)
            
            if not agent:
                return func.HttpResponse(
                    body=json.dumps({"error": "Session not found"}),
                    status_code=404,
                    mimetype="application/json"
                )
            
            # Check if agent belongs to the same tenant and user
            metadata = agent.session_state.metadata
            
            if metadata.get("tenant_id") != tenant_id or metadata.get("user_id") != user_id:
                return func.HttpResponse(
                    body=json.dumps({"error": "Unauthorized to access this session"}),
                    status_code=403,
                    mimetype="application/json"
                )
        else:
            # Create new agent
            agent = await create_orchestrator_agent(tenant_id, user_id)
        
        # Process message
        workflow_params = {}
        
        if workflow_action:
            workflow_params["workflow_action"] = workflow_action
        
        if workflow_id:
            workflow_params["workflow_id"] = workflow_id
        
        if workflow_definition:
            workflow_params["workflow_definition"] = workflow_definition
        
        # Process message with workflow parameters
        response = await agent.process(message, **workflow_params)
        
        # Return response
        return func.HttpResponse(
            body=json.dumps({
                "session_id": agent.session_id,
                "response": response.content,
                "metadata": response.metadata,
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error handling POST request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def handle_get(req: func.HttpRequest, tenant_id: str, user_id: str) -> func.HttpResponse:
    """
    Handle GET requests.
    
    Args:
        req: HTTP request
        tenant_id: Tenant ID
        user_id: User ID
        
    Returns:
        HTTP response
    """
    try:
        # Parse query parameters
        session_id = req.params.get("session_id")
        workflow_id = req.params.get("workflow_id")
        
        if not session_id:
            # List all sessions for this tenant and user
            session_manager = await initialize_session_manager()
            
            sessions = await session_manager.list_sessions(
                agent_type=AgentType.ORCHESTRATOR,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            
            return func.HttpResponse(
                body=json.dumps({"sessions": sessions}),
                status_code=200,
                mimetype="application/json"
            )
        
        # Get specific session
        agent = await get_orchestrator_agent(session_id)
        
        if not agent:
            return func.HttpResponse(
                body=json.dumps({"error": "Session not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
        # Check if agent belongs to the same tenant and user
        metadata = agent.session_state.metadata
        
        if metadata.get("tenant_id") != tenant_id or metadata.get("user_id") != user_id:
            return func.HttpResponse(
                body=json.dumps({"error": "Unauthorized to access this session"}),
                status_code=403,
                mimetype="application/json"
            )
        
        if workflow_id:
            # Get workflow status
            response = await agent.process(
                "Get workflow status",
                workflow_action="status",
                workflow_id=workflow_id,
            )
            
            return func.HttpResponse(
                body=json.dumps({
                    "session_id": agent.session_id,
                    "response": response.content,
                    "metadata": response.metadata,
                }),
                status_code=200,
                mimetype="application/json"
            )
        else:
            # Return session information
            messages = [message.to_dict() for message in agent.session_state.messages]
            
            workflows = {}
            for workflow_id, workflow in agent.workflows.items():
                workflows[workflow_id] = workflow.to_dict()
            
            return func.HttpResponse(
                body=json.dumps({
                    "session_id": agent.session_id,
                    "agent_type": agent.agent_type,
                    "created_at": agent.session_state.created_at,
                    "updated_at": agent.session_state.updated_at,
                    "metadata": agent.session_state.metadata,
                    "messages": messages,
                    "workflows": workflows,
                }),
                status_code=200,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error handling GET request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )