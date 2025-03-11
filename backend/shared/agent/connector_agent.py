"""
Base connector agent implementation for external system integration.
"""

import logging
import json
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple, Set
import time
import uuid
from enum import Enum

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


class ConnectorType(str, Enum):
    """Types of connectors supported by the agent."""
    REST_API = "rest_api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CLOUD_STORAGE = "cloud_storage"
    MESSAGING = "messaging"
    EMAIL = "email"
    CUSTOM = "custom"


class ConnectionStatus(str, Enum):
    """Status of connections to external systems."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectionConfig:
    """Configuration for a connection to an external system."""
    
    def __init__(
        self,
        id: str,
        name: str,
        connector_type: ConnectorType,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize connection configuration.
        
        Args:
            id: Connection ID
            name: Connection name
            connector_type: Type of connector
            params: Connection parameters
            credentials: Optional credentials for authentication
            metadata: Optional metadata
        """
        self.id = id
        self.name = name
        self.connector_type = connector_type
        self.params = params
        self.credentials = credentials or {}
        self.metadata = metadata or {}
        
        # Runtime attributes
        self.status = ConnectionStatus.DISCONNECTED
        self.error = None
        self.last_connected = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "connector_type": self.connector_type,
            "params": self.params,
            "credentials": self.credentials,
            "metadata": self.metadata,
            "status": self.status,
            "error": self.error,
            "last_connected": self.last_connected,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionConfig':
        """Create from dictionary."""
        config = cls(
            id=data["id"],
            name=data["name"],
            connector_type=ConnectorType(data["connector_type"]),
            params=data.get("params", {}),
            credentials=data.get("credentials", {}),
            metadata=data.get("metadata", {}),
        )
        
        # Set runtime attributes
        config.status = ConnectionStatus(data.get("status", ConnectionStatus.DISCONNECTED))
        config.error = data.get("error")
        config.last_connected = data.get("last_connected")
        
        return config


class ConnectorResult:
    """Result from a connector operation."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize connector result.
        
        Args:
            success: Whether the operation was successful
            data: Optional result data
            error: Optional error message
            metadata: Optional metadata
        """
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorResult':
        """Create from dictionary."""
        result = cls(
            success=data["success"],
            data=data.get("data"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )
        
        result.timestamp = data.get("timestamp", time.time())
        
        return result
    
    @classmethod
    def success_result(cls, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> 'ConnectorResult':
        """Create a success result."""
        return cls(
            success=True,
            data=data,
            metadata=metadata,
        )
    
    @classmethod
    def error_result(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> 'ConnectorResult':
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata,
        )


class ConnectorAgent(Agent):
    """
    Base agent for connecting to external systems.
    
    This agent is designed to integrate with various external systems,
    providing a unified interface for data access and operations.
    """
    
    @property
    def agent_type(self) -> AgentType:
        """Get the type of agent."""
        return AgentType.CONNECTOR
    
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
        Initialize the connector agent.
        
        Args:
            session_id: Optional ID for the session
            options: Optional configuration options
            model: OpenAI model instance
            tenant_id: ID of the tenant
            user_id: ID of the user
            connection_config: Configuration for the connection
            system_prompt: Custom system prompt
        """
        super().__init__(session_id, options)
        
        self.model = model
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.connection_config = connection_config
        
        # Default system prompt
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # Session storage
        self.session_storage = None
        
        # Connection state
        self.connection = None
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for the connector agent.
        
        Returns:
            Default system prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        connect to and interact with external systems. Follow these guidelines:
        
        1. Help users establish connections to external systems
        2. Assist with formulating queries and operations for external systems
        3. Format data from external systems in a clear and useful way
        4. Suggest optimizations for operations
        5. Handle errors and provide troubleshooting assistance
        
        You can help with:
        1. Configuring connections
        2. Executing queries and operations
        3. Troubleshooting connection issues
        4. Data format conversion
        5. Explaining data structures from external systems
        
        Please provide clear and structured responses about connection status, data results,
        and any errors that occur.
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
        self.session_storage = {}
        
        # Add system prompt if no messages exist yet
        if not self.session_state.messages:
            await self.add_system_message(self.system_prompt)
            
            # Add connection info if available
            if self.connection_config:
                connection_msg = f"""
                I'll help you work with the following connection:
                
                Name: {self.connection_config.name}
                Type: {self.connection_config.connector_type}
                Status: {self.connection_config.status}
                
                What would you like to do with this connection?
                """
                
                await self.add_system_message(connection_msg)
    
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
            # Check for connector operations
            operation = kwargs.get("operation")
            
            result = None
            
            if operation:
                result = await self._handle_operation(operation, **kwargs)
                
                # Add operation and result as function messages
                await self.add_function_message(
                    name=operation,
                    content=json.dumps(result.to_dict()),
                    metadata={
                        "operation": operation,
                        "timestamp": time.time(),
                    }
                )
            
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
            metadata = {
                "timestamp": time.time(),
            }
            
            if result:
                metadata["operation_result"] = result.to_dict()
            
            if self.connection_config:
                metadata["connection"] = {
                    "id": self.connection_config.id,
                    "name": self.connection_config.name,
                    "type": self.connection_config.connector_type,
                    "status": self.connection_config.status,
                }
            
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
    
    async def _handle_operation(self, operation: str, **kwargs) -> ConnectorResult:
        """
        Handle a connector operation.
        
        Args:
            operation: The operation to perform
            **kwargs: Additional parameters for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            NotImplementedError: If the operation is not supported
        """
        # Connect/disconnect operations
        if operation == "connect":
            return await self.connect()
        elif operation == "disconnect":
            return await self.disconnect()
            
        # Check if connected for other operations
        if not self.is_connected():
            return ConnectorResult.error_result("Not connected to external system")
        
        # Handle other operations based on operation type
        if operation == "execute":
            return await self.execute(**kwargs)
        elif operation == "query":
            return await self.query(**kwargs)
        elif operation == "get_metadata":
            return await self.get_metadata(**kwargs)
        else:
            return ConnectorResult.error_result(f"Unsupported operation: {operation}")
    
    async def connect(self) -> ConnectorResult:
        """
        Connect to the external system.
        
        Returns:
            Result of the connection attempt
        """
        if not self.connection_config:
            return ConnectorResult.error_result("No connection configuration provided")
        
        try:
            # Update status
            self.connection_config.status = ConnectionStatus.CONNECTING
            
            # Implemented by subclasses
            return ConnectorResult.error_result("Connection not implemented in base agent")
        except Exception as e:
            logger.error(f"Error connecting: {str(e)}")
            self.connection_config.status = ConnectionStatus.ERROR
            self.connection_config.error = str(e)
            return ConnectorResult.error_result(f"Error connecting: {str(e)}")
    
    async def disconnect(self) -> ConnectorResult:
        """
        Disconnect from the external system.
        
        Returns:
            Result of the disconnection attempt
        """
        if not self.connection_config:
            return ConnectorResult.error_result("No connection configuration provided")
        
        try:
            # Implemented by subclasses
            self.connection_config.status = ConnectionStatus.DISCONNECTED
            self.connection = None
            return ConnectorResult.success_result(
                data={"message": "Disconnected successfully"},
            )
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            return ConnectorResult.error_result(f"Error disconnecting: {str(e)}")
    
    async def execute(self, **kwargs) -> ConnectorResult:
        """
        Execute an operation on the external system.
        
        Args:
            **kwargs: Parameters for the operation
            
        Returns:
            Result of the operation
        """
        # Implemented by subclasses
        return ConnectorResult.error_result("Execute operation not implemented in base agent")
    
    async def query(self, **kwargs) -> ConnectorResult:
        """
        Query data from the external system.
        
        Args:
            **kwargs: Parameters for the query
            
        Returns:
            Result of the query
        """
        # Implemented by subclasses
        return ConnectorResult.error_result("Query operation not implemented in base agent")
    
    async def get_metadata(self, **kwargs) -> ConnectorResult:
        """
        Get metadata from the external system.
        
        Args:
            **kwargs: Parameters for the metadata retrieval
            
        Returns:
            Result containing metadata
        """
        # Implemented by subclasses
        return ConnectorResult.error_result("Get metadata operation not implemented in base agent")
    
    def is_connected(self) -> bool:
        """
        Check if connected to the external system.
        
        Returns:
            True if connected, False otherwise
        """
        return (
            self.connection_config is not None and 
            self.connection_config.status == ConnectionStatus.CONNECTED and
            self.connection is not None
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