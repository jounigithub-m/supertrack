"""
Query agent implementation for processing natural language queries.
"""

import logging
import json
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple
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


class QueryAgent(Agent):
    """
    Agent for processing natural language queries.
    
    This agent is designed to answer user questions, perform data analysis,
    and generate insights based on available data sources.
    """
    
    @property
    def agent_type(self) -> AgentType:
        """Get the type of agent."""
        return AgentType.QUERY
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None,
        model: Optional[OpenAIModel] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        data_source_ids: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the query agent.
        
        Args:
            session_id: Optional ID for the session. If not provided, a new ID will be generated.
            options: Optional configuration options for the agent.
            model: OpenAI model instance to use for generating responses.
            tenant_id: ID of the tenant this agent is operating for.
            user_id: ID of the user this agent is operating for.
            data_source_ids: List of data source IDs to use for answering queries.
            system_prompt: Custom system prompt to use for the agent.
        """
        super().__init__(session_id, options)
        
        self.model = model
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.data_source_ids = data_source_ids or []
        
        # Default system prompt
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # Session storage
        self.session_storage = None
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for the query agent.
        
        Returns:
            Default system prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        analyze data, answer questions, and generate insights. Follow these guidelines:
        
        1. Answer questions accurately based on available data
        2. If you're unsure or don't have sufficient data, admit it
        3. Keep responses concise and focused
        4. Format data for clarity using tables or bullet points when appropriate
        5. Provide sources for your information when possible
        6. Do not make up information that isn't in the provided data
        7. If asked about complex analyses that require more processing, explain what information 
           you would need and how you would approach the analysis
        
        You have access to the following data sources:
        {data_sources}
        
        When referencing specific data, cite the source clearly.
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
            # Format system prompt with available data sources
            data_sources_info = await self._get_data_sources_info()
            formatted_prompt = self.system_prompt.format(data_sources=data_sources_info)
            
            await self.add_system_message(formatted_prompt)
    
    async def _get_data_sources_info(self) -> str:
        """
        Get information about available data sources.
        
        Returns:
            Formatted string with data sources information
        """
        # In a real implementation, this would query the database for data source information
        # For now, return a placeholder
        if not self.data_source_ids:
            return "No specific data sources have been specified."
        
        # This would be replaced with actual data source information
        return f"- {len(self.data_source_ids)} data sources available for analysis"
    
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
        
        # Add user message to session
        await self.add_user_message(message)
        
        try:
            # Enrich the context with relevant data
            await self._enrich_context(message)
            
            # Generate response
            response_text = await self.model.generate(
                self.session_state.messages,
                self.options
            )
            
            # Add assistant message to session
            await self.add_assistant_message(response_text)
            
            # Save session
            await self.save_session()
            
            # Return response
            return AgentResponse(
                content=response_text,
                session_id=self.session_id,
                metadata={
                    "timestamp": time.time(),
                }
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
    
    async def _enrich_context(self, message: str) -> None:
        """
        Enrich the context with relevant data for answering the query.
        
        Args:
            message: The user message to process
        """
        # In a real implementation, this method would:
        # 1. Analyze the query to determine what data is needed
        # 2. Query databases or vector stores for relevant information
        # 3. Add the retrieved information to the context through function messages
        
        # For now, we'll add a placeholder function message
        if self.data_source_ids:
            await self.add_function_message(
                name="retrieve_data",
                content=json.dumps({
                    "result": "Data retrieval simulated for demo purposes. In a real implementation, "
                              "this would contain actual data retrieved from the specified sources.",
                    "sources": self.data_source_ids,
                }),
                metadata={
                    "data_sources": self.data_source_ids,
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
    
    async def process_stream(self, message: str, **kwargs) -> AsyncIterator[str]:
        """
        Process a user message and generate a streaming response.
        
        Args:
            message: The user message to process
            **kwargs: Additional parameters for processing
            
        Returns:
            AsyncIterator for streaming the response
        """
        # Initialize if not already initialized
        if not self.model:
            await self.initialize()
        
        # Add user message to session
        await self.add_user_message(message)
        
        try:
            # Enrich the context with relevant data
            await self._enrich_context(message)
            
            # Generate streaming response
            response_stream = await self.model.generate_stream(
                self.session_state.messages,
                self.options
            )
            
            # Buffer for collecting the full response
            response_buffer = []
            
            async for chunk in response_stream:
                response_buffer.append(chunk)
                yield chunk
            
            # Concatenate the full response
            full_response = "".join(response_buffer)
            
            # Add assistant message to session
            await self.add_assistant_message(full_response)
            
            # Save session
            await self.save_session()
        
        except Exception as e:
            logger.error(f"Error processing streaming message: {str(e)}")
            error_message = f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            yield error_message