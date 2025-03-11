"""
Base agent interfaces and abstract classes for agent framework.
"""

import logging
import abc
import asyncio
from typing import Any, Dict, List, Optional, Set, Union, Tuple
import json
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict

# Configure logging
logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents in the system."""
    QUERY = "query"
    ORCHESTRATOR = "orchestrator"
    METADATA_EXTRACTION = "metadata_extraction"
    CONNECTOR = "connector"
    INVESTIGATION = "investigation"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """Roles for messages in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"
    DATA = "data"


@dataclass
class Message:
    """A message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "name": self.name,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=MessageRole(data["role"]),
            content=data["content"],
            name=data.get("name"),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class SessionState:
    """State for an agent session."""
    session_id: str
    agent_type: AgentType
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            agent_type=AgentType(data["agent_type"]),
            messages=[Message.from_dict(msg) for msg in data.get("messages", [])],
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
    
    def add_message(self, message: Message) -> None:
        """Add a message to the session state."""
        self.messages.append(message)
        self.updated_at = time.time()


@dataclass
class AgentOptions:
    """Options for configuring an agent."""
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    stream: bool = False
    timeout: float = 60.0
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentOptions':
        """Create from dictionary."""
        return cls(
            temperature=data.get("temperature", 0.0),
            max_tokens=data.get("max_tokens"),
            stream=data.get("stream", False),
            timeout=data.get("timeout", 60.0),
            retry_attempts=data.get("retry_attempts", 3),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: str
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create from dictionary."""
        return cls(
            content=data["content"],
            session_id=data["session_id"],
            metadata=data.get("metadata", {}),
        )


class Agent(abc.ABC):
    """
    Abstract base class for all agents.
    
    Agents are responsible for processing user inputs, generating responses,
    and maintaining session state.
    """
    
    def __init__(
        self, 
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None
    ):
        """
        Initialize the agent.
        
        Args:
            session_id: Optional ID for the session. If not provided, a new ID will be generated.
            options: Optional configuration options for the agent.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.options = options or AgentOptions()
        self.session_state = SessionState(
            session_id=self.session_id,
            agent_type=self.agent_type,
        )
    
    @property
    @abc.abstractmethod
    def agent_type(self) -> AgentType:
        """Get the type of agent."""
        pass
    
    @abc.abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent with necessary resources.
        
        This method should be called before using the agent.
        """
        pass
    
    @abc.abstractmethod
    async def process(self, message: str, **kwargs) -> AgentResponse:
        """
        Process a user message and generate a response.
        
        Args:
            message: The user message to process
            **kwargs: Additional parameters for processing
            
        Returns:
            The agent's response
        """
        pass
    
    @abc.abstractmethod
    async def save_session(self) -> None:
        """
        Save the current session state.
        
        This method should be called to persist the session state.
        """
        pass
    
    @abc.abstractmethod
    async def load_session(self, session_id: str) -> None:
        """
        Load a session state.
        
        Args:
            session_id: ID of the session to load
        """
        pass
    
    async def add_system_message(self, content: str) -> None:
        """
        Add a system message to the session.
        
        Args:
            content: Content of the system message
        """
        message = Message(
            role=MessageRole.SYSTEM,
            content=content,
        )
        self.session_state.add_message(message)
    
    async def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a user message to the session.
        
        Args:
            content: Content of the user message
            metadata: Optional metadata for the message
        """
        message = Message(
            role=MessageRole.USER,
            content=content,
            metadata=metadata or {},
        )
        self.session_state.add_message(message)
    
    async def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an assistant message to the session.
        
        Args:
            content: Content of the assistant message
            metadata: Optional metadata for the message
        """
        message = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            metadata=metadata or {},
        )
        self.session_state.add_message(message)
    
    async def add_function_message(self, content: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a function message to the session.
        
        Args:
            content: Content of the function message
            name: Name of the function
            metadata: Optional metadata for the message
        """
        message = Message(
            role=MessageRole.FUNCTION,
            content=content,
            name=name,
            metadata=metadata or {},
        )
        self.session_state.add_message(message)
    
    async def get_messages(self) -> List[Message]:
        """
        Get all messages in the session.
        
        Returns:
            List of messages
        """
        return self.session_state.messages
    
    async def get_last_message(self) -> Optional[Message]:
        """
        Get the last message in the session.
        
        Returns:
            The last message or None if no messages
        """
        messages = self.session_state.messages
        return messages[-1] if messages else None


class AIModelInterface(abc.ABC):
    """
    Abstract interface for AI models used by agents.
    
    This interface defines the methods that AI models must implement
    to be used by agents.
    """
    
    @abc.abstractmethod
    async def initialize(self) -> None:
        """Initialize the AI model."""
        pass
    
    @abc.abstractmethod
    async def generate(
        self, 
        messages: List[Message], 
        options: Optional[AgentOptions] = None
    ) -> str:
        """
        Generate a response from the AI model.
        
        Args:
            messages: List of messages for context
            options: Optional configuration options
            
        Returns:
            Generated response
        """
        pass
    
    @abc.abstractmethod
    async def generate_stream(
        self, 
        messages: List[Message], 
        options: Optional[AgentOptions] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the AI model.
        
        Args:
            messages: List of messages for context
            options: Optional configuration options
            
        Returns:
            AsyncIterator for streaming the response
        """
        pass
    
    @abc.abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        pass


class AsyncIterator:
    """Async iterator for streaming responses."""
    
    def __init__(self, iterable):
        """Initialize with an iterable."""
        self.iterable = iterable
        self.iterator = None
    
    def __aiter__(self):
        """Return self as async iterator."""
        return self
    
    async def __anext__(self):
        """Get next item."""
        if self.iterator is None:
            self.iterator = iter(self.iterable)
        
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration