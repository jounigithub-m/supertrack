"""
Azure Function endpoint for the metadata extraction agent API.
"""

import logging
import json
import azure.functions as func
import asyncio
from typing import Dict, Any, Optional, List
import tempfile
import os
import time
import base64

from backend.shared.agent import (
    AgentType,
    AgentOptions,
    MetadataExtractionAgent,
    ExtractionField,
    ExtractionSchema,
    OpenAIModel,
    SessionManager,
    InMemorySessionStorage,
    CosmosDBSessionStorage,
)
from backend.shared.document import (
    DocumentType as DocType,
    DocumentProcessor,
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
document_processor = None


async def initialize_services():
    """Initialize the session manager and document processor if not already initialized."""
    global storage_provider, session_manager, document_processor
    
    if session_manager is not None and document_processor is not None:
        return session_manager, document_processor
    
    # Initialize document processor
    if document_processor is None:
        document_processor = DocumentProcessor()
    
    # Determine which storage provider to use based on environment
    if storage_provider is None:
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
    
    # Create session manager if not already initialized
    if session_manager is None:
        session_manager = SessionManager(storage_provider)
        
        # Register agent types
        session_manager.register_agent_factory(AgentType.METADATA_EXTRACTION, MetadataExtractionAgent)
        
        # Initialize session manager
        await session_manager.initialize()
    
    return session_manager, document_processor


def create_extraction_schema(schema_data: Dict[str, Any]) -> ExtractionSchema:
    """
    Create an extraction schema from request data.
    
    Args:
        schema_data: Schema data from request
        
    Returns:
        Extraction schema
    """
    name = schema_data.get("name", "Default Schema")
    description = schema_data.get("description", "")
    fields_data = schema_data.get("fields", [])
    
    fields = []
    
    for field_data in fields_data:
        field = ExtractionField(
            name=field_data.get("name", ""),
            description=field_data.get("description", ""),
            field_type=field_data.get("type", "string"),
            required=field_data.get("required", False),
            examples=field_data.get("examples", []),
        )
        fields.append(field)
    
    return ExtractionSchema(
        name=name,
        description=description,
        fields=fields,
    )


async def create_extraction_agent(
    tenant_id: str,
    user_id: str,
    extraction_schema: Optional[ExtractionSchema] = None,
) -> MetadataExtractionAgent:
    """
    Create a new metadata extraction agent.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        extraction_schema: Optional extraction schema
        
    Returns:
        The created extraction agent
    """
    # Get session manager
    session_manager, _ = await initialize_services()
    
    # Create OpenAI model
    model = OpenAIModel()
    await model.initialize()
    
    # Create agent options
    options = AgentOptions(
        temperature=0.0,
        timeout=120.0,
    )
    
    # Create metadata
    metadata = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "created_at": time.time(),
    }
    
    # Create agent
    agent = await session_manager.create_session(
        agent_type=AgentType.METADATA_EXTRACTION,
        options=options,
        metadata=metadata,
        model=model,
        tenant_id=tenant_id,
        user_id=user_id,
        extraction_schema=extraction_schema,
    )
    
    return agent


async def get_extraction_agent(session_id: str) -> Optional[MetadataExtractionAgent]:
    """
    Get an existing metadata extraction agent.
    
    Args:
        session_id: Session ID
        
    Returns:
        The extraction agent or None if not found
    """
    # Get session manager
    session_manager, _ = await initialize_services()
    
    # Get agent
    agent = await session_manager.get_session(session_id)
    
    if agent and agent.agent_type == AgentType.METADATA_EXTRACTION:
        return agent
    
    return None


async def process_document(
    agent: MetadataExtractionAgent,
    document_data: Dict[str, Any],
    prompt: str,
) -> Dict[str, Any]:
    """
    Process a document using the extraction agent.
    
    Args:
        agent: Metadata extraction agent
        document_data: Document data from request
        prompt: Prompt to send to the agent
        
    Returns:
        Processing result
    """
    try:
        # Get document processor
        _, document_processor = await initialize_services()
        
        # Check if document is provided as base64
        if "base64_content" in document_data:
            # Get document information
            doc_type_str = document_data.get("document_type", "unknown")
            filename = document_data.get("filename", "document")
            base64_content = document_data["base64_content"]
            
            # Convert document type
            try:
                doc_type = DocType(doc_type_str.lower())
            except ValueError:
                doc_type = DocType.UNKNOWN
            
            # Process document
            doc_content = await document_processor.process_base64(
                base64_content=base64_content,
                document_type=doc_type,
                filename=filename,
            )
            
            # Create a temporary file path
            temp_path = f"temp_{time.time()}_{filename}"
            
            # Process with agent
            response = await agent.process(
                message=prompt,
                document_path=temp_path,
                document_type=doc_type,
            )
            
            return {
                "session_id": agent.session_id,
                "response": response.content,
                "metadata": response.metadata,
                "document_info": {
                    "filename": filename,
                    "document_type": doc_type,
                    "content_length": len(doc_content.text),
                },
            }
        
        # If document path is provided (for development/testing)
        elif "document_path" in document_data:
            doc_path = document_data["document_path"]
            doc_type_str = document_data.get("document_type", "unknown")
            
            # Convert document type
            try:
                doc_type = DocType(doc_type_str.lower())
            except ValueError:
                doc_type = DocType.UNKNOWN
            
            # Detect document type if not specified
            if doc_type == DocType.UNKNOWN:
                doc_type = document_processor.detect_document_type(doc_path)
            
            # Process with agent
            response = await agent.process(
                message=prompt,
                document_path=doc_path,
                document_type=doc_type,
            )
            
            return {
                "session_id": agent.session_id,
                "response": response.content,
                "metadata": response.metadata,
                "document_info": {
                    "document_path": doc_path,
                    "document_type": doc_type,
                },
            }
        
        else:
            # No document provided
            response = await agent.process(prompt)
            
            return {
                "session_id": agent.session_id,
                "response": response.content,
                "metadata": response.metadata,
            }
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point.
    
    Args:
        req: HTTP request
        
    Returns:
        HTTP response
    """
    logger.info('Metadata extraction agent function processed a request.')
    
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
        
        # Get extraction schema if provided
        schema_data = req_body.get("extraction_schema")
        extraction_schema = None
        
        if schema_data:
            extraction_schema = create_extraction_schema(schema_data)
        
        # Check if session_id is provided
        session_id = req_body.get("session_id")
        prompt = req_body.get("prompt", "Please extract metadata from this document.")
        document_data = req_body.get("document", {})
        
        # Get or create agent
        if session_id:
            # Get existing agent
            agent = await get_extraction_agent(session_id)
            
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
            agent = await create_extraction_agent(tenant_id, user_id, extraction_schema)
        
        # Process document if provided
        if document_data:
            result = await process_document(agent, document_data, prompt)
            
            # Return response
            return func.HttpResponse(
                body=json.dumps(result),
                status_code=200,
                mimetype="application/json"
            )
        else:
            # Process message only
            response = await agent.process(prompt)
            
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
        
        if not session_id:
            # List all sessions for this tenant and user
            session_manager, _ = await initialize_services()
            
            sessions = await session_manager.list_sessions(
                agent_type=AgentType.METADATA_EXTRACTION,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            
            return func.HttpResponse(
                body=json.dumps({"sessions": sessions}),
                status_code=200,
                mimetype="application/json"
            )
        else:
            # Get specific session
            agent = await get_extraction_agent(session_id)
            
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
            
            # Return session information
            messages = [message.to_dict() for message in agent.session_state.messages]
            
            return func.HttpResponse(
                body=json.dumps({
                    "session_id": agent.session_id,
                    "agent_type": agent.agent_type,
                    "created_at": agent.session_state.created_at,
                    "updated_at": agent.session_state.updated_at,
                    "metadata": agent.session_state.metadata,
                    "messages": messages,
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