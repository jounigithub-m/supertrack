"""
Agent framework for the Supertrack platform.

This package provides a framework for building AI agents that can process
user queries, orchestrate workflows, extract metadata, and more.
"""

# Base agent types and interfaces
from .base_agent import (
    Agent,
    AgentType,
    MessageRole,
    Message,
    AgentOptions,
    AgentResponse,
    SessionState,
    AIModelInterface,
)

# Model implementations
from .openai_model import OpenAIModel, OpenAIModelError

# Agent implementations
from .query_agent import QueryAgent
from .extraction_agent import (
    MetadataExtractionAgent,
    ExtractionField,
    ExtractionSchema,
    DocumentType,
    DocumentProcessor,
)
from .orchestrator_agent import (
    OrchestratorAgent,
    Task,
    TaskStatus,
    Workflow,
    WorkflowStatus,
    WorkflowEngine,
)
from .connector_agent import (
    ConnectorAgent,
    ConnectorType,
    ConnectionStatus,
    ConnectionConfig,
    ConnectorResult,
)
from .rest_api_connector import (
    RestAPIConnector,
    APIAuthType,
    APIMethod,
)
from .oauth2_connector import (
    OAuth2Connector,
    OAuth2FlowType,
    OAuth2TokenType,
)

# Session management
from .session_manager import (
    SessionStorageInterface,
    InMemorySessionStorage,
    CosmosDBSessionStorage,
    SessionManager,
)

__all__ = [
    # Base types
    'Agent',
    'AgentType',
    'MessageRole',
    'Message',
    'AgentOptions',
    'AgentResponse',
    'SessionState',
    'AIModelInterface',
    
    # Model implementations
    'OpenAIModel',
    'OpenAIModelError',
    
    # Agent implementations
    'QueryAgent',
    'MetadataExtractionAgent',
    'ExtractionField',
    'ExtractionSchema',
    'DocumentType',
    'DocumentProcessor',
    'OrchestratorAgent',
    'Task',
    'TaskStatus',
    'Workflow',
    'WorkflowStatus',
    'WorkflowEngine',
    'ConnectorAgent',
    'ConnectorType',
    'ConnectionStatus',
    'ConnectionConfig',
    'ConnectorResult',
    'RestAPIConnector',
    'APIAuthType',
    'APIMethod',
    'OAuth2Connector',
    'OAuth2FlowType', 
    'OAuth2TokenType',
    
    # Session management
    'SessionStorageInterface',
    'InMemorySessionStorage',
    'CosmosDBSessionStorage',
    'SessionManager',
]