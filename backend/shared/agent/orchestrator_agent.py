"""
Orchestrator agent implementation for coordinating workflows.
"""

import logging
import json
import asyncio
import copy
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
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


class TaskStatus(str, Enum):
    """Status of tasks in a workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """Status of workflows."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Task:
    """A task in a workflow."""
    
    def __init__(
        self,
        id: str,
        agent_type: AgentType,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        retry_limit: int = 3,
    ):
        """
        Initialize a task.
        
        Args:
            id: Task ID
            agent_type: Type of agent to execute the task
            name: Optional name of the task
            description: Optional description of the task
            params: Optional parameters for the task
            dependencies: Optional list of task IDs that must complete before this task
            timeout: Optional timeout for the task in seconds
            retry_limit: Number of times to retry the task on failure
        """
        self.id = id
        self.agent_type = agent_type
        self.name = name or id
        self.description = description or ""
        self.params = params or {}
        self.dependencies = dependencies or []
        self.timeout = timeout
        self.retry_limit = retry_limit
        
        # Runtime attributes
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.retry_count = 0
        self.session_id = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "params": self.params,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_limit": self.retry_limit,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary."""
        task = cls(
            id=data["id"],
            agent_type=AgentType(data["agent_type"]),
            name=data.get("name"),
            description=data.get("description"),
            params=data.get("params", {}),
            dependencies=data.get("dependencies", []),
            timeout=data.get("timeout"),
            retry_limit=data.get("retry_limit", 3),
        )
        
        # Set runtime attributes
        task.status = TaskStatus(data.get("status", TaskStatus.PENDING))
        task.start_time = data.get("start_time")
        task.end_time = data.get("end_time")
        task.result = data.get("result")
        task.error = data.get("error")
        task.retry_count = data.get("retry_count", 0)
        task.session_id = data.get("session_id")
        
        return task


class Workflow:
    """A workflow definition."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str] = None,
        tasks: Optional[List[Task]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a workflow.
        
        Args:
            id: Workflow ID
            name: Name of the workflow
            description: Optional description of the workflow
            tasks: Optional list of tasks in the workflow
            metadata: Optional metadata for the workflow
        """
        self.id = id
        self.name = name
        self.description = description or ""
        self.tasks = tasks or []
        self.metadata = metadata or {}
        
        # Runtime attributes
        self.status = WorkflowStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error = None
        self.current_task_id = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasks": [task.to_dict() for task in self.tasks],
            "metadata": self.metadata,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "current_task_id": self.current_task_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create from dictionary."""
        workflow = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            tasks=[Task.from_dict(task) for task in data.get("tasks", [])],
            metadata=data.get("metadata", {}),
        )
        
        # Set runtime attributes
        workflow.status = WorkflowStatus(data.get("status", WorkflowStatus.PENDING))
        workflow.start_time = data.get("start_time")
        workflow.end_time = data.get("end_time")
        workflow.error = data.get("error")
        workflow.current_task_id = data.get("current_task_id")
        
        return workflow
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            The task or None if not found
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_next_tasks(self) -> List[Task]:
        """
        Get the next tasks that are ready to execute.
        
        Returns:
            List of tasks that are ready to execute
        """
        ready_tasks = []
        
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                # Skip tasks that are not pending
                continue
            
            # Check if all dependencies are completed
            dependencies_completed = True
            
            for dep_id in task.dependencies:
                dep_task = self.get_task(dep_id)
                
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    dependencies_completed = False
                    break
            
            if dependencies_completed:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def is_complete(self) -> bool:
        """
        Check if the workflow is complete.
        
        Returns:
            True if all tasks are completed, failed, or cancelled
        """
        for task in self.tasks:
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
        return True
    
    def has_failed_tasks(self) -> bool:
        """
        Check if the workflow has any failed tasks.
        
        Returns:
            True if any task has failed
        """
        for task in self.tasks:
            if task.status == TaskStatus.FAILED:
                return True
        return False


class WorkflowEngine:
    """
    Engine for executing workflows.
    
    This class is responsible for executing workflows and delegating tasks
    to the appropriate agents.
    """
    
    def __init__(self, session_manager, tenant_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize the workflow engine.
        
        Args:
            session_manager: Session manager for creating agent sessions
            tenant_id: Optional tenant ID
            user_id: Optional user ID
        """
        self.session_manager = session_manager
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.workflow = None
        self.active_tasks = set()
        self.on_task_complete = None
        self.on_task_failed = None
        self.on_workflow_complete = None
        self.on_workflow_failed = None
        self.is_running = False
    
    def set_workflow(self, workflow: Workflow) -> None:
        """
        Set the workflow to execute.
        
        Args:
            workflow: Workflow to execute
        """
        self.workflow = workflow
    
    def set_callback(self, event_type: str, callback: Callable) -> None:
        """
        Set a callback for workflow events.
        
        Args:
            event_type: Type of event to trigger the callback
            callback: Callback function
        """
        if event_type == "task_complete":
            self.on_task_complete = callback
        elif event_type == "task_failed":
            self.on_task_failed = callback
        elif event_type == "workflow_complete":
            self.on_workflow_complete = callback
        elif event_type == "workflow_failed":
            self.on_workflow_failed = callback
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    async def execute(self) -> Workflow:
        """
        Execute the workflow.
        
        Returns:
            The executed workflow
            
        Raises:
            ValueError: If no workflow is set
        """
        if not self.workflow:
            raise ValueError("No workflow set")
        
        # Initialize workflow
        self.workflow.status = WorkflowStatus.IN_PROGRESS
        self.workflow.start_time = time.time()
        self.is_running = True
        
        try:
            # Execute tasks
            while self.is_running and not self.workflow.is_complete():
                # Get next tasks
                next_tasks = self.workflow.get_next_tasks()
                
                if not next_tasks:
                    # No tasks ready to execute
                    if self.active_tasks:
                        # Wait for active tasks to complete
                        await asyncio.sleep(0.1)
                    else:
                        # No tasks ready and no active tasks, workflow is stuck
                        logger.warning("Workflow is stuck with no runnable tasks")
                        self.workflow.status = WorkflowStatus.FAILED
                        self.workflow.error = "Workflow is stuck with no runnable tasks"
                        break
                
                # Start tasks
                for task in next_tasks:
                    asyncio.create_task(self._execute_task(task))
                    self.active_tasks.add(task.id)
            
            # Check final status
            if self.workflow.is_complete():
                if self.workflow.has_failed_tasks():
                    self.workflow.status = WorkflowStatus.FAILED
                    self.workflow.error = "One or more tasks failed"
                    
                    if self.on_workflow_failed:
                        await self.on_workflow_failed(self.workflow)
                else:
                    self.workflow.status = WorkflowStatus.COMPLETED
                    
                    if self.on_workflow_complete:
                        await self.on_workflow_complete(self.workflow)
            
            self.workflow.end_time = time.time()
            return self.workflow
        
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            self.workflow.status = WorkflowStatus.FAILED
            self.workflow.error = str(e)
            self.workflow.end_time = time.time()
            
            if self.on_workflow_failed:
                await self.on_workflow_failed(self.workflow)
            
            return self.workflow
        finally:
            self.is_running = False
    
    def stop(self) -> None:
        """Stop the workflow execution."""
        self.is_running = False
        self.workflow.status = WorkflowStatus.CANCELLED
    
    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task.
        
        Args:
            task: Task to execute
        """
        if not self.is_running:
            return
        
        task.status = TaskStatus.IN_PROGRESS
        task.start_time = time.time()
        
        try:
            # Create agent for task
            agent_params = {
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
            }
            
            # Add task parameters
            agent_params.update(task.params)
            
            # Create agent session
            agent = await self.session_manager.create_session(
                agent_type=task.agent_type,
                metadata={
                    "workflow_id": self.workflow.id,
                    "task_id": task.id,
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                },
                **agent_params,
            )
            
            # Store session ID
            task.session_id = agent.session_id
            
            # Execute task
            prompt = task.params.get("prompt", "")
            
            if not prompt:
                prompt = f"Execute task: {task.name}\n{task.description}"
            
            # Process with appropriate parameters
            response = await agent.process(prompt, **task.params)
            
            # Store result
            task.result = {
                "content": response.content,
                "metadata": response.metadata,
            }
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            
            # Trigger callback
            if self.on_task_complete:
                await self.on_task_complete(task)
        
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            
            # Increment retry count
            task.retry_count += 1
            
            if task.retry_count < task.retry_limit:
                # Retry task
                logger.info(f"Retrying task {task.id} (attempt {task.retry_count + 1})")
                task.status = TaskStatus.PENDING
                task.error = f"Error executing task: {str(e)}. Retrying..."
            else:
                # Mark as failed
                task.status = TaskStatus.FAILED
                task.error = f"Error executing task: {str(e)}"
                
                # Trigger callback
                if self.on_task_failed:
                    await self.on_task_failed(task)
        
        finally:
            task.end_time = time.time()
            self.active_tasks.discard(task.id)


class OrchestratorAgent(Agent):
    """
    Agent for orchestrating workflows.
    
    This agent is designed to coordinate complex workflows by delegating
    tasks to specialized agents and managing the overall workflow execution.
    """
    
    @property
    def agent_type(self) -> AgentType:
        """Get the type of agent."""
        return AgentType.ORCHESTRATOR
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None,
        model: Optional[OpenAIModel] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_manager = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the orchestrator agent.
        
        Args:
            session_id: Optional ID for the session. If not provided, a new ID will be generated.
            options: Optional configuration options for the agent.
            model: OpenAI model instance to use for generating responses.
            tenant_id: ID of the tenant this agent is operating for.
            user_id: ID of the user this agent is operating for.
            session_manager: Session manager for creating agent sessions.
            system_prompt: Custom system prompt to use for the agent.
        """
        super().__init__(session_id, options)
        
        self.model = model
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.session_manager = session_manager
        
        # Default system prompt
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # Session storage
        self.session_storage = None
        
        # Active workflows
        self.workflows = {}
        self.engines = {}
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for the orchestrator agent.
        
        Returns:
            Default system prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to orchestrate
        complex workflows by coordinating specialized agents. Follow these guidelines:
        
        1. Help users define and manage workflows
        2. Parse workflow definitions from natural language descriptions
        3. Execute workflows by delegating tasks to appropriate agents
        4. Track workflow progress and report status
        5. Handle errors and provide recovery options
        6. Suggest workflow optimizations
        
        You can help with:
        1. Creating new workflows
        2. Executing existing workflows
        3. Modifying workflows
        4. Troubleshooting failed workflows
        5. Recommending workflow improvements
        
        Please provide clear and structured responses about workflow status and next steps.
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
            # Handle workflow-related commands
            workflow_action = kwargs.get("workflow_action")
            
            if workflow_action:
                if workflow_action == "create":
                    return await self._create_workflow(message, **kwargs)
                elif workflow_action == "execute":
                    return await self._execute_workflow(**kwargs)
                elif workflow_action == "status":
                    return await self._get_workflow_status(**kwargs)
                elif workflow_action == "stop":
                    return await self._stop_workflow(**kwargs)
            
            # Generate response
            response_text = await self.model.generate(
                self.session_state.messages,
                self.options
            )
            
            # Parse workflow definitions if present
            workflow_definition = self._extract_workflow_definition(response_text)
            
            # Add assistant message to session
            await self.add_assistant_message(response_text)
            
            # Save session
            await self.save_session()
            
            # Return response
            metadata = {
                "timestamp": time.time(),
            }
            
            if workflow_definition:
                metadata["workflow_definition"] = workflow_definition
            
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
    
    def _extract_workflow_definition(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract workflow definition from text.
        
        Args:
            text: Text that may contain a workflow definition
            
        Returns:
            Extracted workflow definition or None if not found
        """
        try:
            # Look for workflow definition patterns
            start_marker = "```workflow"
            end_marker = "```"
            
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return None
            
            start_idx += len(start_marker)
            end_idx = text.find(end_marker, start_idx)
            
            if end_idx == -1:
                return None
            
            workflow_json = text[start_idx:end_idx].strip()
            return json.loads(workflow_json)
        except Exception as e:
            logger.warning(f"Error extracting workflow definition: {str(e)}")
            return None
    
    async def _create_workflow(self, message: str, **kwargs) -> AgentResponse:
        """
        Create a new workflow.
        
        Args:
            message: User message describing the workflow
            **kwargs: Additional parameters
            
        Returns:
            Agent response with workflow information
        """
        workflow_data = kwargs.get("workflow_definition")
        
        if not workflow_data:
            # Ask the model to help generate a workflow definition
            await self.add_system_message(
                "Please create a workflow definition based on the user's request. "
                "Format the workflow definition as JSON inside ```workflow ``` code blocks."
            )
            
            response_text = await self.model.generate(
                self.session_state.messages,
                self.options
            )
            
            # Extract workflow definition
            workflow_data = self._extract_workflow_definition(response_text)
            
            if not workflow_data:
                # Add assistant message to session
                await self.add_assistant_message(response_text)
                
                # Save session
                await self.save_session()
                
                return AgentResponse(
                    content=response_text,
                    session_id=self.session_id,
                    metadata={
                        "timestamp": time.time(),
                    }
                )
        
        # Create workflow from definition
        try:
            # Generate ID if not provided
            if "id" not in workflow_data:
                workflow_data["id"] = str(uuid.uuid4())
            
            # Create tasks
            tasks = []
            for task_data in workflow_data.get("tasks", []):
                task = Task(
                    id=task_data.get("id", str(uuid.uuid4())),
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
            
            # Store workflow
            self.workflows[workflow.id] = workflow
            
            # Generate response
            response_text = f"""
            I've created a new workflow:
            
            Name: {workflow.name}
            ID: {workflow.id}
            Description: {workflow.description}
            
            The workflow contains {len(workflow.tasks)} tasks:
            """
            
            for task in workflow.tasks:
                response_text += f"\n- {task.name} ({task.agent_type})"
            
            response_text += "\n\nYou can execute this workflow using the workflow_action='execute' parameter."
            
            # Add assistant message to session
            await self.add_assistant_message(response_text)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=response_text,
                session_id=self.session_id,
                metadata={
                    "workflow_id": workflow.id,
                    "workflow": workflow.to_dict(),
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            error_message = f"I'm sorry, I encountered an error while creating the workflow: {str(e)}"
            
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
    
    async def _execute_workflow(self, **kwargs) -> AgentResponse:
        """
        Execute a workflow.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Agent response with execution information
        """
        workflow_id = kwargs.get("workflow_id")
        
        if not workflow_id:
            error_message = "Workflow ID is required to execute a workflow."
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": "workflow_id_required",
                    "timestamp": time.time(),
                }
            )
        
        # Get workflow
        workflow = self.workflows.get(workflow_id)
        
        if not workflow:
            error_message = f"Workflow with ID {workflow_id} not found."
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": "workflow_not_found",
                    "timestamp": time.time(),
                }
            )
        
        # Create a copy of the workflow for execution
        execution_workflow = copy.deepcopy(workflow)
        
        # Create engine
        engine = WorkflowEngine(
            session_manager=self.session_manager,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
        
        # Set workflow
        engine.set_workflow(execution_workflow)
        
        # Store engine
        self.engines[workflow_id] = engine
        
        # Start execution (don't await it)
        task = asyncio.create_task(engine.execute())
        
        # Generate response
        response_text = f"""
        I'm executing workflow "{execution_workflow.name}" (ID: {execution_workflow.id}).
        
        The workflow contains {len(execution_workflow.tasks)} tasks:
        """
        
        for task in execution_workflow.tasks:
            response_text += f"\n- {task.name} ({task.agent_type})"
        
        response_text += "\n\nYou can check the status of this workflow using the workflow_action='status' parameter."
        
        # Add assistant message to session
        await self.add_assistant_message(response_text)
        
        # Save session
        await self.save_session()
        
        return AgentResponse(
            content=response_text,
            session_id=self.session_id,
            metadata={
                "workflow_id": workflow_id,
                "status": execution_workflow.status,
                "timestamp": time.time(),
            }
        )
    
    async def _get_workflow_status(self, **kwargs) -> AgentResponse:
        """
        Get workflow status.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Agent response with workflow status
        """
        workflow_id = kwargs.get("workflow_id")
        
        if not workflow_id:
            error_message = "Workflow ID is required to check workflow status."
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": "workflow_id_required",
                    "timestamp": time.time(),
                }
            )
        
        # Get engine
        engine = self.engines.get(workflow_id)
        
        if not engine or not engine.workflow:
            # Check if workflow exists
            workflow = self.workflows.get(workflow_id)
            
            if not workflow:
                error_message = f"Workflow with ID {workflow_id} not found."
                
                # Add error message to session
                await self.add_assistant_message(error_message)
                
                # Save session
                await self.save_session()
                
                return AgentResponse(
                    content=error_message,
                    session_id=self.session_id,
                    metadata={
                        "error": "workflow_not_found",
                        "timestamp": time.time(),
                    }
                )
            
            # Workflow exists but hasn't been executed
            response_text = f"""
            Workflow "{workflow.name}" (ID: {workflow_id}) has not been executed yet.
            
            You can execute this workflow using the workflow_action='execute' parameter.
            """
            
            # Add assistant message to session
            await self.add_assistant_message(response_text)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=response_text,
                session_id=self.session_id,
                metadata={
                    "workflow_id": workflow_id,
                    "status": workflow.status,
                    "timestamp": time.time(),
                }
            )
        
        # Get workflow
        workflow = engine.workflow
        
        # Generate response
        response_text = f"""
        Status of workflow "{workflow.name}" (ID: {workflow.id}):
        
        Status: {workflow.status}
        """
        
        if workflow.start_time:
            start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(workflow.start_time))
            response_text += f"\nStart time: {start_time_str}"
        
        if workflow.end_time:
            end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(workflow.end_time))
            response_text += f"\nEnd time: {end_time_str}"
            
            duration = workflow.end_time - workflow.start_time
            response_text += f"\nDuration: {duration:.2f} seconds"
        
        if workflow.error:
            response_text += f"\nError: {workflow.error}"
        
        response_text += "\n\nTasks:"
        
        for task in workflow.tasks:
            response_text += f"\n- {task.name} ({task.agent_type}): {task.status}"
            
            if task.error:
                response_text += f" - Error: {task.error}"
        
        # Add assistant message to session
        await self.add_assistant_message(response_text)
        
        # Save session
        await self.save_session()
        
        # Create tasks info
        tasks_info = []
        for task in workflow.tasks:
            tasks_info.append({
                "id": task.id,
                "name": task.name,
                "agent_type": task.agent_type,
                "status": task.status,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "error": task.error,
                "session_id": task.session_id,
            })
        
        return AgentResponse(
            content=response_text,
            session_id=self.session_id,
            metadata={
                "workflow_id": workflow_id,
                "status": workflow.status,
                "start_time": workflow.start_time,
                "end_time": workflow.end_time,
                "error": workflow.error,
                "tasks": tasks_info,
                "timestamp": time.time(),
            }
        )
    
    async def _stop_workflow(self, **kwargs) -> AgentResponse:
        """
        Stop a workflow.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Agent response with stop information
        """
        workflow_id = kwargs.get("workflow_id")
        
        if not workflow_id:
            error_message = "Workflow ID is required to stop a workflow."
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": "workflow_id_required",
                    "timestamp": time.time(),
                }
            )
        
        # Get engine
        engine = self.engines.get(workflow_id)
        
        if not engine or not engine.workflow:
            error_message = f"No active workflow found with ID {workflow_id}."
            
            # Add error message to session
            await self.add_assistant_message(error_message)
            
            # Save session
            await self.save_session()
            
            return AgentResponse(
                content=error_message,
                session_id=self.session_id,
                metadata={
                    "error": "workflow_not_found",
                    "timestamp": time.time(),
                }
            )
        
        # Get workflow
        workflow = engine.workflow
        
        # Stop workflow
        engine.stop()
        
        # Generate response
        response_text = f"""
        I've stopped workflow "{workflow.name}" (ID: {workflow.id}).
        
        Status: {workflow.status}
        """
        
        # Add assistant message to session
        await self.add_assistant_message(response_text)
        
        # Save session
        await self.save_session()
        
        return AgentResponse(
            content=response_text,
            session_id=self.session_id,
            metadata={
                "workflow_id": workflow_id,
                "status": workflow.status,
                "timestamp": time.time(),
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