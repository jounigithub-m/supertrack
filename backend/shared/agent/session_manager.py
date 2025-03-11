"""
Session manager for agent persistence and retrieval.
"""

import logging
import json
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple, Type
import time
import uuid
import os
import datetime

from .base_agent import (
    AgentType,
    MessageRole,
    Message,
    AgentOptions,
    AgentResponse,
    SessionState,
    Agent,
)

# Configure logging
logger = logging.getLogger(__name__)


class SessionStorageInterface:
    """
    Interface for session storage providers.
    
    This interface defines the methods that storage providers must implement
    to be used by the session manager.
    """
    
    async def initialize(self) -> None:
        """Initialize the storage provider."""
        pass
    
    async def save_session(self, session_state: SessionState) -> None:
        """
        Save a session state.
        
        Args:
            session_state: The session state to save
        """
        pass
    
    async def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load a session state.
        
        Args:
            session_id: ID of the session to load
            
        Returns:
            The session state or None if not found
        """
        pass
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    async def list_sessions(
        self, 
        agent_type: Optional[AgentType] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filtering.
        
        Args:
            agent_type: Optional filter by agent type
            tenant_id: Optional filter by tenant ID
            user_id: Optional filter by user ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session metadata
        """
        pass


class InMemorySessionStorage(SessionStorageInterface):
    """
    In-memory implementation of session storage.
    
    This implementation stores sessions in memory and is suitable for
    development and testing purposes.
    """
    
    def __init__(self):
        """Initialize the in-memory storage."""
        self.sessions = {}
        self.metadata = {}
    
    async def initialize(self) -> None:
        """Initialize the storage provider."""
        # Nothing to initialize for in-memory storage
        pass
    
    async def save_session(self, session_state: SessionState) -> None:
        """
        Save a session state.
        
        Args:
            session_state: The session state to save
        """
        session_dict = session_state.to_dict()
        session_id = session_dict["session_id"]
        
        self.sessions[session_id] = session_dict
        
        # Extract metadata
        self.metadata[session_id] = {
            "session_id": session_id,
            "agent_type": session_dict["agent_type"],
            "created_at": session_dict["created_at"],
            "updated_at": session_dict["updated_at"],
            "metadata": session_dict["metadata"],
        }
        
        logger.info(f"Saved session {session_id} to in-memory storage")
    
    async def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load a session state.
        
        Args:
            session_id: ID of the session to load
            
        Returns:
            The session state or None if not found
        """
        session_dict = self.sessions.get(session_id)
        
        if not session_dict:
            logger.warning(f"Session {session_id} not found in storage")
            return None
        
        return SessionState.from_dict(session_dict)
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            True if deleted, False if not found
        """
        if session_id not in self.sessions:
            return False
        
        del self.sessions[session_id]
        
        if session_id in self.metadata:
            del self.metadata[session_id]
        
        logger.info(f"Deleted session {session_id} from in-memory storage")
        return True
    
    async def list_sessions(
        self, 
        agent_type: Optional[AgentType] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filtering.
        
        Args:
            agent_type: Optional filter by agent type
            tenant_id: Optional filter by tenant ID
            user_id: Optional filter by user ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session metadata
        """
        results = []
        
        for session_id, meta in self.metadata.items():
            # Apply filters
            if agent_type and meta["agent_type"] != agent_type:
                continue
                
            # Check tenant_id and user_id in metadata
            session_metadata = meta.get("metadata", {})
            
            if tenant_id and session_metadata.get("tenant_id") != tenant_id:
                continue
                
            if user_id and session_metadata.get("user_id") != user_id:
                continue
                
            results.append(meta)
        
        # Sort by updated_at (most recent first)
        results.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        
        # Apply pagination
        paginated = results[offset:offset+limit]
        
        return paginated


class CosmosDBSessionStorage(SessionStorageInterface):
    """
    CosmosDB implementation of session storage.
    
    This implementation stores sessions in Azure Cosmos DB and is suitable for
    production use.
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        database_name: str = "supertrack",
        container_name: str = "agent_sessions",
    ):
        """
        Initialize the CosmosDB storage.
        
        Args:
            connection_string: Optional CosmosDB connection string
            endpoint: Optional CosmosDB endpoint
            key: Optional CosmosDB key
            database_name: Name of the database
            container_name: Name of the container
        """
        self.connection_string = connection_string
        self.endpoint = endpoint
        self.key = key
        self.database_name = database_name
        self.container_name = container_name
        self.client = None
        self.container = None
    
    async def initialize(self) -> None:
        """
        Initialize the storage provider.
        
        This method connects to CosmosDB and ensures the required database and container exist.
        """
        try:
            # In a real implementation, this would connect to Cosmos DB
            # For now, we'll log a message
            logger.info(f"Initializing CosmosDB session storage (database: {self.database_name}, container: {self.container_name})")
            logger.info("This is a placeholder implementation - no actual CosmosDB connection will be established")
            
            # In a real implementation:
            # from azure.cosmos.aio import CosmosClient
            # self.client = CosmosClient.from_connection_string(self.connection_string)
            # database = self.client.get_database_client(self.database_name)
            # self.container = database.get_container_client(self.container_name)
        except Exception as e:
            logger.error(f"Error initializing CosmosDB session storage: {str(e)}")
            raise
    
    async def save_session(self, session_state: SessionState) -> None:
        """
        Save a session state.
        
        Args:
            session_state: The session state to save
        """
        try:
            # In a real implementation, this would save to Cosmos DB
            session_dict = session_state.to_dict()
            session_id = session_dict["session_id"]
            
            # Add required Cosmos DB fields
            document = {
                "id": session_id,
                "session_id": session_id,
                "document_type": "agent_session",
                "agent_type": session_dict["agent_type"],
                "created_at": session_dict["created_at"],
                "updated_at": session_dict["updated_at"],
                "metadata": session_dict["metadata"],
                "session_data": session_dict,
                "ttl": 2592000,  # 30 days in seconds
            }
            
            logger.info(f"Simulating save of session {session_id} to CosmosDB")
            # In a real implementation:
            # await self.container.upsert_item(document)
        except Exception as e:
            logger.error(f"Error saving session to CosmosDB: {str(e)}")
            raise
    
    async def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load a session state.
        
        Args:
            session_id: ID of the session to load
            
        Returns:
            The session state or None if not found
        """
        try:
            # In a real implementation, this would load from Cosmos DB
            logger.info(f"Simulating load of session {session_id} from CosmosDB")
            
            # In a real implementation:
            # query = f"SELECT * FROM c WHERE c.id = '{session_id}'"
            # results = self.container.query_items(query, enable_cross_partition_query=True)
            # items = [item async for item in results]
            # if not items:
            #     return None
            # session_data = items[0].get("session_data", {})
            # return SessionState.from_dict(session_data)
            
            # For now, return None to simulate session not found
            return None
        except Exception as e:
            logger.error(f"Error loading session from CosmosDB: {str(e)}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # In a real implementation, this would delete from Cosmos DB
            logger.info(f"Simulating deletion of session {session_id} from CosmosDB")
            
            # In a real implementation:
            # await self.container.delete_item(session_id, partition_key=session_id)
            
            # For now, return True to simulate successful deletion
            return True
        except Exception as e:
            logger.error(f"Error deleting session from CosmosDB: {str(e)}")
            return False
    
    async def list_sessions(
        self, 
        agent_type: Optional[AgentType] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filtering.
        
        Args:
            agent_type: Optional filter by agent type
            tenant_id: Optional filter by tenant ID
            user_id: Optional filter by user ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session metadata
        """
        try:
            # In a real implementation, this would query Cosmos DB
            logger.info(f"Simulating listing of sessions from CosmosDB")
            
            # Build query
            query = "SELECT c.id, c.agent_type, c.created_at, c.updated_at, c.metadata FROM c WHERE c.document_type = 'agent_session'"
            
            if agent_type:
                query += f" AND c.agent_type = '{agent_type}'"
                
            if tenant_id:
                query += f" AND c.metadata.tenant_id = '{tenant_id}'"
                
            if user_id:
                query += f" AND c.metadata.user_id = '{user_id}'"
                
            query += f" ORDER BY c.updated_at DESC OFFSET {offset} LIMIT {limit}"
            
            logger.info(f"Query: {query}")
            
            # In a real implementation:
            # results = self.container.query_items(query, enable_cross_partition_query=True)
            # items = [item async for item in results]
            # return items
            
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error listing sessions from CosmosDB: {str(e)}")
            return []


class SessionManager:
    """
    Manager for agent sessions.
    
    This class provides functionality for creating, retrieving, and managing
    agent sessions.
    """
    
    def __init__(
        self,
        storage_provider: SessionStorageInterface,
        agent_factories: Dict[AgentType, Type[Agent]] = None,
    ):
        """
        Initialize the session manager.
        
        Args:
            storage_provider: Storage provider for session persistence
            agent_factories: Dictionary mapping agent types to agent factory functions
        """
        self.storage = storage_provider
        self.agent_factories = agent_factories or {}
        self.active_sessions = {}
    
    async def initialize(self) -> None:
        """Initialize the session manager."""
        await self.storage.initialize()
    
    def register_agent_factory(self, agent_type: AgentType, agent_class: Type[Agent]) -> None:
        """
        Register an agent factory for a specific agent type.
        
        Args:
            agent_type: Type of agent
            agent_class: Agent class to use for this type
        """
        self.agent_factories[agent_type] = agent_class
    
    async def create_session(
        self,
        agent_type: AgentType,
        options: Optional[AgentOptions] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Agent:
        """
        Create a new agent session.
        
        Args:
            agent_type: Type of agent to create
            options: Optional configuration options
            metadata: Optional metadata for the session
            **kwargs: Additional arguments to pass to the agent constructor
            
        Returns:
            The created agent
            
        Raises:
            ValueError: If the agent type is not registered
        """
        if agent_type not in self.agent_factories:
            raise ValueError(f"No agent factory registered for type {agent_type}")
        
        agent_class = self.agent_factories[agent_type]
        
        # Create a new agent
        agent = agent_class(
            options=options,
            **kwargs,
        )
        
        # Initialize agent
        await agent.initialize()
        
        # Add metadata
        if metadata:
            agent.session_state.metadata.update(metadata)
        
        # Save session
        await self.storage.save_session(agent.session_state)
        
        # Add to active sessions
        self.active_sessions[agent.session_id] = agent
        
        return agent
    
    async def get_session(self, session_id: str) -> Optional[Agent]:
        """
        Get an existing agent session.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            The retrieved agent or None if not found
            
        Raises:
            ValueError: If the agent type is not registered
        """
        # Check if session is already active
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Load session from storage
        session_state = await self.storage.load_session(session_id)
        
        if not session_state:
            return None
        
        # Get agent type
        agent_type = session_state.agent_type
        
        if agent_type not in self.agent_factories:
            raise ValueError(f"No agent factory registered for type {agent_type}")
        
        agent_class = self.agent_factories[agent_type]
        
        # Create agent with existing session ID
        agent = agent_class(session_id=session_id)
        
        # Initialize agent
        await agent.initialize()
        
        # Load session state
        agent.session_state = session_state
        
        # Add to active sessions
        self.active_sessions[session_id] = agent
        
        return agent
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete an agent session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Delete from storage
        return await self.storage.delete_session(session_id)
    
    async def list_sessions(
        self, 
        agent_type: Optional[AgentType] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filtering.
        
        Args:
            agent_type: Optional filter by agent type
            tenant_id: Optional filter by tenant ID
            user_id: Optional filter by user ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session metadata
        """
        return await self.storage.list_sessions(
            agent_type=agent_type,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )