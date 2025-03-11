"""
Metadata extraction agent implementation for document processing.
"""

import logging
import json
import asyncio
import tempfile
import os
from typing import Any, Dict, List, Optional, Union, Tuple, Set
import time
import uuid

from .base_agent import (
    Agent,
    AgentType,
    MessageRole,
    Message,
    AgentOptions,
    AgentResponse,
    SessionState,
)
from .openai_model import OpenAIModel

# Configure logging
logger = logging.getLogger(__name__)


class DocumentType:
    """Document types that can be processed."""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ExtractionField:
    """Definition of a field to extract from documents."""
    
    def __init__(
        self,
        name: str,
        description: str,
        field_type: str = "string",
        required: bool = False,
        examples: Optional[List[str]] = None,
    ):
        """
        Initialize an extraction field.
        
        Args:
            name: Field name
            description: Description of the field
            field_type: Data type of the field
            required: Whether the field is required
            examples: Example values for the field
        """
        self.name = name
        self.description = description
        self.field_type = field_type
        self.required = required
        self.examples = examples or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.field_type,
            "required": self.required,
            "examples": self.examples,
        }


class ExtractionSchema:
    """Schema defining fields to extract from documents."""
    
    def __init__(
        self,
        name: str,
        description: str,
        fields: List[ExtractionField],
    ):
        """
        Initialize an extraction schema.
        
        Args:
            name: Schema name
            description: Description of the schema
            fields: List of fields to extract
        """
        self.name = name
        self.description = description
        self.fields = fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "fields": [field.to_dict() for field in self.fields],
        }


class DocumentProcessor:
    """Base class for document processors."""
    
    def __init__(self):
        """Initialize the document processor."""
        pass
    
    async def process(self, document_path: str, document_type: str) -> str:
        """
        Process a document and extract its text content.
        
        Args:
            document_path: Path to the document
            document_type: Type of document
            
        Returns:
            Extracted text content
        """
        raise NotImplementedError("Document processor not implemented")


class DefaultDocumentProcessor(DocumentProcessor):
    """Default implementation of document processor."""
    
    def __init__(self):
        """Initialize the default document processor."""
        super().__init__()
    
    async def process(self, document_path: str, document_type: str) -> str:
        """
        Process a document and extract its text content.
        
        Args:
            document_path: Path to the document
            document_type: Type of document
            
        Returns:
            Extracted text content
        """
        if document_type == DocumentType.PDF:
            return await self._process_pdf(document_path)
        elif document_type == DocumentType.TEXT:
            return await self._process_text(document_path)
        elif document_type == DocumentType.JSON:
            return await self._process_json(document_path)
        else:
            logger.warning(f"Unsupported document type: {document_type}")
            return f"Document type {document_type} is not supported by the default processor."
    
    async def _process_pdf(self, document_path: str) -> str:
        """
        Process a PDF document.
        
        Args:
            document_path: Path to the PDF document
            
        Returns:
            Extracted text content
        """
        try:
            # In a real implementation, this would use PyPDF2 or similar
            logger.info(f"Processing PDF document: {document_path}")
            
            # For demo purposes, we'll return a placeholder
            return f"[PDF Content extracted from {document_path}]"
        except Exception as e:
            logger.error(f"Error processing PDF document: {str(e)}")
            return f"Error processing PDF document: {str(e)}"
    
    async def _process_text(self, document_path: str) -> str:
        """
        Process a text document.
        
        Args:
            document_path: Path to the text document
            
        Returns:
            Extracted text content
        """
        try:
            # Simple text file reading
            logger.info(f"Processing text document: {document_path}")
            
            with open(document_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error processing text document: {str(e)}")
            return f"Error processing text document: {str(e)}"
    
    async def _process_json(self, document_path: str) -> str:
        """
        Process a JSON document.
        
        Args:
            document_path: Path to the JSON document
            
        Returns:
            Extracted text content
        """
        try:
            # Read and format JSON
            logger.info(f"Processing JSON document: {document_path}")
            
            with open(document_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return json.dumps(data, indent=2)
        except Exception as e:
            logger.error(f"Error processing JSON document: {str(e)}")
            return f"Error processing JSON document: {str(e)}"


class MetadataExtractionAgent(Agent):
    """
    Agent for extracting metadata from documents.
    
    This agent is designed to process documents and extract structured
    metadata according to a predefined schema.
    """
    
    @property
    def agent_type(self) -> AgentType:
        """Get the type of agent."""
        return AgentType.METADATA_EXTRACTION
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None,
        model: Optional[OpenAIModel] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        document_processor: Optional[DocumentProcessor] = None,
        extraction_schema: Optional[ExtractionSchema] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the metadata extraction agent.
        
        Args:
            session_id: Optional ID for the session. If not provided, a new ID will be generated.
            options: Optional configuration options for the agent.
            model: OpenAI model instance to use for generating responses.
            tenant_id: ID of the tenant this agent is operating for.
            user_id: ID of the user this agent is operating for.
            document_processor: Document processor to use for extracting text content.
            extraction_schema: Schema defining fields to extract from documents.
            system_prompt: Custom system prompt to use for the agent.
        """
        super().__init__(session_id, options)
        
        self.model = model
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.document_processor = document_processor or DefaultDocumentProcessor()
        self.extraction_schema = extraction_schema
        
        # Default system prompt
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # Session storage
        self.session_storage = None
        
        # Current document being processed
        self.current_document = None
        self.current_document_content = None
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for the metadata extraction agent.
        
        Returns:
            Default system prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to extract 
        structured metadata from documents according to a specific schema. Follow these guidelines:
        
        1. Extract information accurately based on the provided schema
        2. If you're unsure about a field value, indicate uncertainty
        3. Format the extracted data as JSON
        4. Provide confidence scores for uncertain extractions
        5. If a required field cannot be found, explain why
        6. For dates, use ISO format (YYYY-MM-DD)
        7. For amounts, include the currency symbol or code if available
        
        You will be provided with:
        1. The text content of a document
        2. A schema defining the fields to extract
        
        Please return the extracted metadata as a valid JSON object following the schema.
        """
    
    async def initialize(self) -> None:
        """
        Initialize the agent with necessary resources.
        
        This method initializes the AI model and adds the system prompt to the session.
        """
        if not self.model:
            # Initialize with default model if none provided
            self.model = OpenAIModel()
        
        await self.model.initialize()
        
        # Initialize session storage
        # This would connect to a database in production
        self.session_storage = {}
        
        # Add system prompt if no messages exist yet
        if not self.session_state.messages:
            await self.add_system_message(self.system_prompt)
            
            # Add extraction schema if provided
            if self.extraction_schema:
                schema_message = f"""
                Please extract the following fields from the document:
                
                Schema: {self.extraction_schema.name}
                Description: {self.extraction_schema.description}
                Fields:
                """
                
                for field in self.extraction_schema.fields:
                    required_text = "Required" if field.required else "Optional"
                    examples_text = ""
                    
                    if field.examples:
                        examples_text = f"Examples: {', '.join(field.examples)}"
                    
                    schema_message += f"""
                    - {field.name} ({field.field_type}, {required_text})
                      {field.description}
                      {examples_text}
                    """
                
                await self.add_system_message(schema_message)
    
    async def process(self, message: str, **kwargs) -> AgentResponse:
        """
        Process a user message and generate a response.
        
        Args:
            message: The user message to process
            **kwargs: Additional parameters for processing
            
        Returns:
            The agent's response
        """
        # Initialize if not already initialized
        if not self.model or not hasattr(self.model, 'client') or not self.model.client:
            await self.initialize()
        
        # Check if this is a document processing request
        document_path = kwargs.get("document_path")
        document_type = kwargs.get("document_type", DocumentType.UNKNOWN)
        
        # Add user message to session
        await self.add_user_message(message)
        
        try:
            # Process document if provided
            if document_path:
                await self._process_document(document_path, document_type)
            
            # Generate response
            response_text = await self.model.generate(
                self.session_state.messages,
                self.options
            )
            
            # Extract structured data from response if it contains JSON
            extracted_data = self._extract_json_from_text(response_text)
            
            # Add assistant message to session
            await self.add_assistant_message(response_text)
            
            # Save session
            await self.save_session()
            
            # Return response with extracted data in metadata
            metadata = {
                "timestamp": time.time(),
            }
            
            if extracted_data:
                metadata["extracted_data"] = extracted_data
            
            return AgentResponse(
                content=response_text,
                session_id=self.session_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_message = f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": str(e),
                    "timestamp": time.time(),
                }
            )
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from text.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON object or None if not found
        """
        try:
            # Look for JSON patterns (between curly braces)
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
            
            return None
        except Exception as e:
            logger.warning(f"Error extracting JSON from text: {str(e)}")
            return None
    
    async def _process_document(self, document_path: str, document_type: str) -> None:
        """
        Process a document and add its content to the session.
        
        Args:
            document_path: Path to the document
            document_type: Type of document
        """
        try:
            # Extract text content from document
            document_content = await self.document_processor.process(document_path, document_type)
            
            # Store current document info
            self.current_document = {
                "path": document_path,
                "type": document_type,
                "processed_at": time.time(),
            }
            self.current_document_content = document_content
            
            # Add document content as function message
            await self.add_function_message(
                name="extract_document_text",
                content=json.dumps({
                    "document_path": document_path,
                    "document_type": document_type,
                    "content": document_content[:1000] + ("..." if len(document_content) > 1000 else ""),
                    "content_length": len(document_content),
                }),
                metadata={
                    "document_path": document_path,
                    "document_type": document_type,
                }
            )
            
            # If content is very long, break it up into chunks for the model
            if len(document_content) > 10000:
                await self._process_long_document(document_content)
            else:
                # Add full content as user message
                await self.add_user_message(
                    f"Please extract metadata from this document:\n\n{document_content}",
                    metadata={
                        "document_path": document_path,
                        "document_type": document_type,
                    }
                )
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    async def _process_long_document(self, content: str) -> None:
        """
        Process a long document by breaking it into chunks.
        
        Args:
            content: Document content
        """
        # Define chunk size
        chunk_size = 8000
        
        # Split content into chunks
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            chunk_message = f"Document chunk {i+1}/{len(chunks)}:\n\n{chunk}"
            
            await self.add_user_message(
                chunk_message,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )
            
            # If not the last chunk, add assistant acknowledgment
            if i < len(chunks) - 1:
                await self.add_assistant_message(
                    f"I've received chunk {i+1}/{len(chunks)} of the document. Please continue with the next chunk.",
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    }
                )
        
        # Final instruction after all chunks
        await self.add_user_message(
            "You've now received the complete document. Please extract the metadata according to the provided schema.",
            metadata={
                "instruction": "extract_metadata",
                "total_chunks": len(chunks),
            }
        )
    
    async def save_session(self) -> None:
        """
        Save the current session state.
        
        This method persists the session state to storage.
        """
        if not self.session_storage:
            # Initialize session storage if not already initialized
            self.session_storage = {}
        
        # Convert session state to dictionary
        session_dict = self.session_state.to_dict()
        
        # In a real implementation, this would save to a database
        self.session_storage[self.session_id] = session_dict
        
        logger.info(f"Saved session {self.session_id}")
    
    async def load_session(self, session_id: str) -> None:
        """
        Load a session state.
        
        Args:
            session_id: ID of the session to load
        """
        if not self.session_storage:
            # Initialize session storage if not already initialized
            self.session_storage = {}
        
        # In a real implementation, this would load from a database
        session_dict = self.session_storage.get(session_id)
        
        if not session_dict:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session ID and state
        self.session_id = session_id
        self.session_state = SessionState.from_dict(session_dict)
        
        logger.info(f"Loaded session {session_id}")