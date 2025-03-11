"""
OpenAI model implementation for agent framework.
"""

import asyncio
import logging
import time
import json
from typing import Any, Dict, List, Optional, AsyncIterator, Union
import os
import httpx

from .base_agent import (
    Message, 
    MessageRole, 
    AgentOptions, 
    AIModelInterface,
    AsyncIterator as CustomAsyncIterator
)

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIModelError(Exception):
    """Error from OpenAI API."""
    pass


class OpenAIModel(AIModelInterface):
    """
    Implementation of AIModelInterface using OpenAI API.
    
    This class provides access to OpenAI's language models through
    their API with async support.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        Initialize OpenAI Model interface.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env variable)
            model: Model to use (default: gpt-4o)
            organization: OpenAI organization ID
            base_url: Base URL for OpenAI API (to support Azure OpenAI)
            timeout: Timeout for API requests in seconds
            embedding_model: Model to use for embeddings
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        self.organization = organization
        self.base_url = base_url or "https://api.openai.com/v1"
        self.timeout = timeout
        self.embedding_model = embedding_model
        self.client = None
    
    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Convert Message objects to OpenAI API format.
        
        Args:
            messages: List of Message objects
            
        Returns:
            List of message dictionaries in OpenAI format
        """
        openai_messages = []
        
        for msg in messages:
            openai_msg = {
                "role": msg.role,
                "content": msg.content,
            }
            
            if msg.name:
                openai_msg["name"] = msg.name
            
            openai_messages.append(openai_msg)
        
        return openai_messages
    
    async def _make_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any], 
        retry_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Make a request to the OpenAI API with retries.
        
        Args:
            endpoint: API endpoint
            data: Request data
            retry_attempts: Number of retry attempts
            
        Returns:
            API response
            
        Raises:
            OpenAIModelError: If the request fails after all retries
        """
        if not self.client:
            await self.initialize()
        
        attempts = 0
        last_error = None
        
        while attempts < retry_attempts:
            try:
                response = await self.client.post(
                    endpoint,
                    json=data,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_info = {}
                try:
                    error_info = e.response.json()
                except:
                    error_info = {"status": e.response.status_code, "detail": str(e)}
                
                logger.error(f"OpenAI API error: {error_info}")
                
                if e.response.status_code == 429:  # Rate limit
                    # Exponential backoff
                    wait_time = 2 ** attempts
                    logger.info(f"Rate limited. Waiting {wait_time} seconds before retry.")
                    await asyncio.sleep(wait_time)
                    attempts += 1
                    last_error = e
                    continue
                
                raise OpenAIModelError(f"OpenAI API error: {error_info}")
            except Exception as e:
                logger.error(f"Error making OpenAI request: {str(e)}")
                attempts += 1
                last_error = e
                await asyncio.sleep(1)
        
        if last_error:
            raise OpenAIModelError(f"Failed after {retry_attempts} attempts: {str(last_error)}")
        
        raise OpenAIModelError("Unknown error occurred")
    
    async def generate(
        self, 
        messages: List[Message], 
        options: Optional[AgentOptions] = None
    ) -> str:
        """
        Generate a response from the OpenAI model.
        
        Args:
            messages: List of messages for context
            options: Optional configuration options
            
        Returns:
            Generated response text
            
        Raises:
            OpenAIModelError: If the generation fails
        """
        options = options or AgentOptions()
        
        data = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": options.temperature,
        }
        
        if options.max_tokens:
            data["max_tokens"] = options.max_tokens
        
        try:
            response = await self._make_request(
                "/chat/completions",
                data,
                retry_attempts=options.retry_attempts,
            )
            
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise OpenAIModelError(f"Failed to generate response: {str(e)}")
    
    async def generate_stream(
        self, 
        messages: List[Message], 
        options: Optional[AgentOptions] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the OpenAI model.
        
        Args:
            messages: List of messages for context
            options: Optional configuration options
            
        Returns:
            AsyncIterator for streaming the response
            
        Raises:
            OpenAIModelError: If the generation fails
        """
        if not self.client:
            await self.initialize()
        
        options = options or AgentOptions()
        
        data = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": options.temperature,
            "stream": True,
        }
        
        if options.max_tokens:
            data["max_tokens"] = options.max_tokens
        
        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=data,
                timeout=options.timeout,
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_lines():
                    if not chunk.strip():
                        continue
                    
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                    
                    if chunk == "[DONE]":
                        break
                    
                    try:
                        content = json.loads(chunk)
                        delta = content.get("choices", [{}])[0].get("delta", {})
                        
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse chunk: {chunk}")
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise OpenAIModelError(f"Failed to stream response: {str(e)}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for text using OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            OpenAIModelError: If the embedding generation fails
        """
        data = {
            "model": self.embedding_model,
            "input": text,
        }
        
        try:
            response = await self._make_request(
                "/embeddings",
                data,
            )
            
            return response["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise OpenAIModelError(f"Failed to generate embeddings: {str(e)}")
    
    async def close(self) -> None:
        """Close the API client."""
        if self.client:
            await self.client.aclose()
            self.client = None