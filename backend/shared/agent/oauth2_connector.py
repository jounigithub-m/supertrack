"""
OAuth2 connector implementation for authenticated API access.

This module provides OAuth2 authentication support for the connector agent,
enabling secure access to OAuth2-protected services including:
- Social media APIs (Meta, LinkedIn, TikTok)
- Advertising platforms (Google Ads, Facebook Ads)
- Marketing tools (HubSpot, Active Campaign)
- Analytics services (Google Search Console, Matomo)
"""

import logging
import json
import asyncio
import httpx
import time
import uuid
import base64
import secrets
import hashlib
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from urllib.parse import urlencode, urlparse, parse_qs
from enum import Enum

from .connector_agent import (
    ConnectorAgent,
    ConnectorType,
    ConnectionStatus,
    ConnectionConfig,
    ConnectorResult,
)
from .base_agent import AgentOptions, OpenAIModel

# Configure logging
logger = logging.getLogger(__name__)


class OAuth2FlowType(str, Enum):
    """OAuth2 authorization flow types."""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"
    IMPLICIT = "implicit"
    DEVICE_CODE = "device_code"


class OAuth2TokenType(str, Enum):
    """OAuth2 token types."""
    BEARER = "Bearer"
    MAC = "MAC"
    BASIC = "Basic"


class OAuth2Connector(ConnectorAgent):
    """
    Connector agent for OAuth2 authentication.
    
    This agent provides integration with OAuth2-protected services,
    handling authorization flows, token management, and authenticated requests.
    """
    
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
        Initialize the OAuth2 connector agent.
        
        Args:
            session_id: Optional ID for the session
            options: Optional configuration options
            model: OpenAI model instance
            tenant_id: ID of the tenant
            user_id: ID of the user
            connection_config: Configuration for the OAuth2 connection
            system_prompt: Custom system prompt
        """
        super().__init__(
            session_id=session_id,
            options=options,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            connection_config=connection_config,
            system_prompt=system_prompt or self._get_oauth2_prompt(),
        )
        
        # HTTP client
        self.client = None
        
        # OAuth2 state
        self.auth_flow = None
        self.token_info = None
        self.auth_state = None
        self.pkce_verifier = None
    
    def _get_oauth2_prompt(self) -> str:
        """
        Get the system prompt for the OAuth2 connector.
        
        Returns:
            System prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        connect to OAuth2-protected services. Follow these guidelines:
        
        1. Guide users through OAuth2 authorization processes
        2. Help configure OAuth2 settings for different services
        3. Assist with token management and refresh
        4. Provide troubleshooting for OAuth2 connection issues
        5. Explain OAuth2 concepts and security best practices
        
        You can help with:
        1. Setting up OAuth2 client credentials
        2. Generating authorization URLs
        3. Explaining authorization flows
        4. Managing tokens securely
        5. Implementing best practices for token refresh and expiration
        
        Please provide clear, structured guidance regarding OAuth2 authorization processes,
        token management, and any authentication errors that occur.
        """
    
    async def connect(self) -> ConnectorResult:
        """
        Connect to the OAuth2 service by initiating the appropriate flow.
        
        Returns:
            Result of the connection attempt
        """
        if not self.connection_config:
            return ConnectorResult.error_result("No connection configuration provided")
        
        try:
            # Update status
            self.connection_config.status = ConnectionStatus.CONNECTING
            
            # Initialize client
            self.client = httpx.AsyncClient()
            
            # Get OAuth2 params
            flow_type = self.connection_config.params.get("flow_type", OAuth2FlowType.AUTHORIZATION_CODE)
            self.auth_flow = flow_type
            
            # Get client credentials
            client_id = self.connection_config.credentials.get("client_id")
            client_secret = self.connection_config.credentials.get("client_secret")
            
            if not client_id:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = "Client ID is required"
                return ConnectorResult.error_result("Client ID is required")
            
            # Handle different OAuth2 flows
            if flow_type == OAuth2FlowType.AUTHORIZATION_CODE:
                # Check if we already have a valid token
                existing_token = self.connection_config.credentials.get("access_token")
                existing_expires_at = self.connection_config.credentials.get("expires_at")
                
                if existing_token and existing_expires_at and time.time() < existing_expires_at - 300:
                    # Token is still valid (with 5-minute buffer)
                    self.token_info = {
                        "access_token": existing_token,
                        "token_type": self.connection_config.credentials.get("token_type", OAuth2TokenType.BEARER),
                        "expires_at": existing_expires_at,
                        "refresh_token": self.connection_config.credentials.get("refresh_token"),
                    }
                    
                    # Set up client with token
                    self._setup_authenticated_client()
                    
                    # Update connection status
                    self.connection_config.status = ConnectionStatus.CONNECTED
                    self.connection_config.last_connected = time.time()
                    self.connection = self.client
                    
                    return ConnectorResult.success_result(
                        data={"message": "Connected using existing token"},
                        metadata={
                            "token_valid_until": time.strftime(
                                "%Y-%m-%d %H:%M:%S", 
                                time.localtime(existing_expires_at)
                            )
                        }
                    )
                
                # Try to refresh token if available
                existing_refresh_token = self.connection_config.credentials.get("refresh_token")
                if existing_refresh_token:
                    refresh_result = await self._refresh_token(
                        client_id, 
                        client_secret, 
                        existing_refresh_token
                    )
                    
                    if refresh_result.success:
                        # Token refreshed successfully
                        return ConnectorResult.success_result(
                            data={"message": "Connected using refreshed token"},
                            metadata={
                                "token_valid_until": time.strftime(
                                    "%Y-%m-%d %H:%M:%S", 
                                    time.localtime(self.token_info["expires_at"])
                                )
                            }
                        )
                
                # Need to authorize - prepare authorization URL
                authorization_url = self._prepare_authorization_url()
                
                self.connection_config.status = ConnectionStatus.CONNECTING
                
                return ConnectorResult.success_result(
                    data={
                        "message": "Authorization required",
                        "authorization_url": authorization_url,
                        "auth_state": self.auth_state,
                    },
                    metadata={
                        "flow_type": flow_type,
                        "requires_user_action": True,
                    }
                )
            
            elif flow_type == OAuth2FlowType.CLIENT_CREDENTIALS:
                # This flow doesn't require user interaction
                if not client_secret:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "Client secret is required for client credentials flow"
                    return ConnectorResult.error_result("Client secret is required for client credentials flow")
                
                # Get token endpoint
                token_endpoint = self.connection_config.params.get("token_endpoint")
                if not token_endpoint:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = "Token endpoint is required"
                    return ConnectorResult.error_result("Token endpoint is required")
                
                # Get scopes
                scopes = self.connection_config.params.get("scopes", [])
                scope_str = " ".join(scopes) if isinstance(scopes, list) else scopes
                
                # Request parameters
                data = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
                
                if scope_str:
                    data["scope"] = scope_str
                    
                # Custom parameters
                custom_params = self.connection_config.params.get("custom_token_params", {})
                data.update(custom_params)
                
                # Request token
                try:
                    response = await self.client.post(token_endpoint, data=data)
                    response.raise_for_status()
                    token_data = response.json()
                except Exception as e:
                    self.connection_config.status = ConnectionStatus.ERROR
                    self.connection_config.error = f"Error requesting token: {str(e)}"
                    return ConnectorResult.error_result(f"Error requesting token: {str(e)}")
                
                # Store token information
                self.token_info = self._process_token_response(token_data)
                
                # Set up client with token
                self._setup_authenticated_client()
                
                # Update connection status
                self.connection_config.status = ConnectionStatus.CONNECTED
                self.connection_config.last_connected = time.time()
                self.connection = self.client
                
                # Update token in credentials
                self.connection_config.credentials["access_token"] = self.token_info["access_token"]
                self.connection_config.credentials["token_type"] = self.token_info["token_type"]
                self.connection_config.credentials["expires_at"] = self.token_info["expires_at"]
                if "refresh_token" in self.token_info:
                    self.connection_config.credentials["refresh_token"] = self.token_info["refresh_token"]
                
                return ConnectorResult.success_result(
                    data={"message": "Connected successfully"},
                    metadata={
                        "token_valid_until": time.strftime(
                            "%Y-%m-%d %H:%M:%S", 
                            time.localtime(self.token_info["expires_at"])
                        )
                    }
                )
            else:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = f"Unsupported OAuth2 flow type: {flow_type}"
                return ConnectorResult.error_result(f"Unsupported OAuth2 flow type: {flow_type}")
        except Exception as e:
            logger.error(f"Error connecting to OAuth2 service: {str(e)}")
            self.connection_config.status = ConnectionStatus.ERROR
            self.connection_config.error = str(e)
            return ConnectorResult.error_result(f"Error connecting to OAuth2 service: {str(e)}")
    
    def _prepare_authorization_url(self) -> str:
        """
        Prepare the authorization URL for the authorization code flow.
        
        Returns:
            Authorization URL
        """
        # Get authorization endpoint
        authorization_endpoint = self.connection_config.params.get("authorization_endpoint")
        if not authorization_endpoint:
            raise ValueError("Authorization endpoint is required")
        
        # Get client ID
        client_id = self.connection_config.credentials.get("client_id")
        if not client_id:
            raise ValueError("Client ID is required")
        
        # Get redirect URI
        redirect_uri = self.connection_config.params.get("redirect_uri")
        if not redirect_uri:
            raise ValueError("Redirect URI is required")
        
        # Get scopes
        scopes = self.connection_config.params.get("scopes", [])
        scope_str = " ".join(scopes) if isinstance(scopes, list) else scopes
        
        # Generate state for CSRF protection
        self.auth_state = secrets.token_urlsafe(32)
        
        # Prepare PKCE if enabled
        use_pkce = self.connection_config.params.get("use_pkce", False)
        code_challenge = None
        code_challenge_method = None
        
        if use_pkce:
            # Generate PKCE verifier and challenge
            self.pkce_verifier = secrets.token_urlsafe(64)
            pkce_sha256 = hashlib.sha256(self.pkce_verifier.encode()).digest()
            code_challenge = base64.urlsafe_b64encode(pkce_sha256).decode().rstrip("=")
            code_challenge_method = "S256"
        
        # Prepare authorization parameters
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": self.auth_state,
        }
        
        if scope_str:
            params["scope"] = scope_str
        
        if use_pkce:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        
        # Add custom parameters
        custom_params = self.connection_config.params.get("custom_auth_params", {})
        params.update(custom_params)
        
        # Construct URL
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"
        
        return authorization_url
    
    async def handle_authorization_response(self, url_or_params: Union[str, Dict[str, Any]]) -> ConnectorResult:
        """
        Handle the authorization response from the OAuth2 provider.
        
        Args:
            url_or_params: Full redirect URL or parameters from the redirect
            
        Returns:
            Result of the authorization
        """
        try:
            # Extract parameters from URL if a URL is provided
            if isinstance(url_or_params, str):
                parsed = urlparse(url_or_params)
                params = parse_qs(parsed.query)
                # Convert lists to single values
                params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in params.items()}
            else:
                params = url_or_params
            
            # Check for errors
            if "error" in params:
                error = params.get("error")
                error_description = params.get("error_description", "No description provided")
                
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = f"Authorization error: {error} - {error_description}"
                
                return ConnectorResult.error_result(
                    f"Authorization error: {error}",
                    metadata={"error_description": error_description}
                )
            
            # Validate state to prevent CSRF
            if self.auth_state and params.get("state") != self.auth_state:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = "Invalid state parameter"
                
                return ConnectorResult.error_result("Invalid state parameter")
            
            # Check for authorization code
            code = params.get("code")
            if not code:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = "No authorization code received"
                
                return ConnectorResult.error_result("No authorization code received")
            
            # Exchange code for token
            client_id = self.connection_config.credentials.get("client_id")
            client_secret = self.connection_config.credentials.get("client_secret")
            redirect_uri = self.connection_config.params.get("redirect_uri")
            token_endpoint = self.connection_config.params.get("token_endpoint")
            
            if not client_id or not token_endpoint:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = "Missing client ID or token endpoint"
                
                return ConnectorResult.error_result("Missing client ID or token endpoint")
            
            # Prepare token request
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
            }
            
            # Add client secret if available
            if client_secret:
                data["client_secret"] = client_secret
            
            # Add PKCE verifier if available
            if self.pkce_verifier:
                data["code_verifier"] = self.pkce_verifier
            
            # Custom parameters
            custom_params = self.connection_config.params.get("custom_token_params", {})
            data.update(custom_params)
            
            headers = {}
            
            # Use HTTP Basic Authentication if configured
            use_basic_auth = self.connection_config.params.get("use_basic_auth", False)
            if use_basic_auth and client_id and client_secret:
                auth_string = f"{client_id}:{client_secret}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
                # Remove from request body
                if "client_secret" in data:
                    del data["client_secret"]
            
            # Request token
            try:
                response = await self.client.post(token_endpoint, data=data, headers=headers)
                response.raise_for_status()
                token_data = response.json()
            except Exception as e:
                self.connection_config.status = ConnectionStatus.ERROR
                self.connection_config.error = f"Error exchanging code for token: {str(e)}"
                
                return ConnectorResult.error_result(f"Error exchanging code for token: {str(e)}")
            
            # Process token response
            self.token_info = self._process_token_response(token_data)
            
            # Set up client with token
            self._setup_authenticated_client()
            
            # Update connection status
            self.connection_config.status = ConnectionStatus.CONNECTED
            self.connection_config.last_connected = time.time()
            self.connection = self.client
            
            # Update token in credentials
            self.connection_config.credentials["access_token"] = self.token_info["access_token"]
            self.connection_config.credentials["token_type"] = self.token_info["token_type"]
            self.connection_config.credentials["expires_at"] = self.token_info["expires_at"]
            if "refresh_token" in self.token_info:
                self.connection_config.credentials["refresh_token"] = self.token_info["refresh_token"]
            
            # Clear auth state and PKCE verifier
            self.auth_state = None
            self.pkce_verifier = None
            
            return ConnectorResult.success_result(
                data={"message": "Authorization successful"},
                metadata={
                    "token_valid_until": time.strftime(
                        "%Y-%m-%d %H:%M:%S", 
                        time.localtime(self.token_info["expires_at"])
                    ),
                    "scopes": token_data.get("scope", "").split() if "scope" in token_data else None,
                }
            )
        except Exception as e:
            logger.error(f"Error handling authorization response: {str(e)}")
            self.connection_config.status = ConnectionStatus.ERROR
            self.connection_config.error = str(e)
            
            return ConnectorResult.error_result(f"Error handling authorization response: {str(e)}")
    
    def _process_token_response(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the token response from the OAuth2 provider.
        
        Args:
            token_data: Token response data
            
        Returns:
            Processed token information
        """
        # Calculate expiration
        expires_in = token_data.get("expires_in")
        expires_at = None
        
        if expires_in:
            expires_at = time.time() + int(expires_in)
        else:
            # Default 1 hour if not specified
            expires_at = time.time() + 3600
        
        # Extract token type
        token_type = token_data.get("token_type", OAuth2TokenType.BEARER)
        
        # Normalize token type
        if isinstance(token_type, str):
            token_type = token_type.capitalize()
        
        # Create token info
        token_info = {
            "access_token": token_data["access_token"],
            "token_type": token_type,
            "expires_at": expires_at,
        }
        
        # Add refresh token if available
        if "refresh_token" in token_data:
            token_info["refresh_token"] = token_data["refresh_token"]
        
        # Add id token if available (OpenID Connect)
        if "id_token" in token_data:
            token_info["id_token"] = token_data["id_token"]
        
        # Add scope if available
        if "scope" in token_data:
            token_info["scope"] = token_data["scope"]
        
        # Add raw response for reference
        token_info["raw_response"] = token_data
        
        return token_info
    
    async def _refresh_token(self, client_id: str, client_secret: Optional[str], refresh_token: str) -> ConnectorResult:
        """
        Refresh the OAuth2 token.
        
        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret (optional)
            refresh_token: Refresh token
            
        Returns:
            Result of the token refresh
        """
        token_endpoint = self.connection_config.params.get("token_endpoint")
        
        if not token_endpoint:
            return ConnectorResult.error_result("Token endpoint is required for token refresh")
        
        # Prepare token refresh request
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
        
        # Add client secret if available
        if client_secret:
            data["client_secret"] = client_secret
        
        headers = {}
        
        # Use HTTP Basic Authentication if configured
        use_basic_auth = self.connection_config.params.get("use_basic_auth", False)
        if use_basic_auth and client_id and client_secret:
            auth_string = f"{client_id}:{client_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
            # Remove from request body
            if "client_secret" in data:
                del data["client_secret"]
        
        try:
            response = await self.client.post(token_endpoint, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
        except Exception as e:
            return ConnectorResult.error_result(f"Error refreshing token: {str(e)}")
        
        # Process token response
        self.token_info = self._process_token_response(token_data)
        
        # Set up client with token
        self._setup_authenticated_client()
        
        # Update connection status
        self.connection_config.status = ConnectionStatus.CONNECTED
        self.connection_config.last_connected = time.time()
        self.connection = self.client
        
        # Update token in credentials
        self.connection_config.credentials["access_token"] = self.token_info["access_token"]
        self.connection_config.credentials["token_type"] = self.token_info["token_type"]
        self.connection_config.credentials["expires_at"] = self.token_info["expires_at"]
        if "refresh_token" in self.token_info:
            self.connection_config.credentials["refresh_token"] = self.token_info["refresh_token"]
        
        return ConnectorResult.success_result(
            data={"message": "Token refreshed successfully"},
            metadata={
                "token_valid_until": time.strftime(
                    "%Y-%m-%d %H:%M:%S", 
                    time.localtime(self.token_info["expires_at"])
                )
            }
        )
    
    def _setup_authenticated_client(self) -> None:
        """
        Set up the HTTP client with authentication.
        """
        if not self.token_info:
            raise ValueError("No token information available")
        
        # Close existing client if available
        if self.client:
            asyncio.create_task(self.client.aclose())
        
        # Create new client
        base_url = self.connection_config.params.get("api_base_url", "")
        
        # Set up authentication
        headers = {}
        token_type = self.token_info["token_type"]
        access_token = self.token_info["access_token"]
        
        if token_type.lower() == "bearer":
            headers["Authorization"] = f"Bearer {access_token}"
        elif token_type.lower() == "basic":
            headers["Authorization"] = f"Basic {access_token}"
        elif token_type.lower() == "mac":
            # MAC authentication is complex and varies by implementation
            # This is just a basic placeholder
            headers["Authorization"] = f"MAC id={access_token}"
        else:
            # Default to bearer
            headers["Authorization"] = f"{token_type} {access_token}"
        
        # Add custom headers
        custom_headers = self.connection_config.params.get("custom_headers", {})
        headers.update(custom_headers)
        
        # Create client
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=self.connection_config.params.get("timeout", 30.0),
        )
    
    async def disconnect(self) -> ConnectorResult:
        """
        Disconnect from the OAuth2 service.
        
        Returns:
            Result of the disconnection attempt
        """
        if not self.client:
            return ConnectorResult.success_result({"message": "Already disconnected"})
        
        try:
            # Check if there's a revocation endpoint
            revocation_endpoint = self.connection_config.params.get("revocation_endpoint")
            client_id = self.connection_config.credentials.get("client_id")
            client_secret = self.connection_config.credentials.get("client_secret")
            
            # Revoke token if possible
            if revocation_endpoint and self.token_info and client_id:
                token = self.token_info.get("access_token")
                
                if token:
                    data = {
                        "token": token,
                        "client_id": client_id,
                        "token_type_hint": "access_token",
                    }
                    
                    if client_secret:
                        data["client_secret"] = client_secret
                    
                    try:
                        await self.client.post(revocation_endpoint, data=data)
                    except Exception as e:
                        logger.warning(f"Error revoking token: {str(e)}")
            
            # Close HTTP client
            await self.client.aclose()
            
            # Clear state
            self.client = None
            self.connection = None
            self.token_info = None
            self.auth_state = None
            self.pkce_verifier = None
            
            # Update status
            self.connection_config.status = ConnectionStatus.DISCONNECTED
            
            return ConnectorResult.success_result({"message": "Disconnected successfully"})
        except Exception as e:
            logger.error(f"Error disconnecting from OAuth2 service: {str(e)}")
            return ConnectorResult.error_result(f"Error disconnecting: {str(e)}")
    
    async def execute(self, **kwargs) -> ConnectorResult:
        """
        Execute a request to the API with OAuth2 authentication.
        
        Args:
            **kwargs: Parameters for the request
                - method: HTTP method (GET, POST, etc.)
                - path: API endpoint path
                - params: Query parameters
                - data: Request body for POST/PUT/PATCH
                - json: JSON request body for POST/PUT/PATCH
                - headers: Additional headers
            
        Returns:
            Result of the request
        """
        if not self.is_connected():
            # Check if token needs refresh
            refresh_token = self.connection_config.credentials.get("refresh_token")
            client_id = self.connection_config.credentials.get("client_id")
            client_secret = self.connection_config.credentials.get("client_secret")
            
            if refresh_token and client_id:
                refresh_result = await self._refresh_token(client_id, client_secret, refresh_token)
                if not refresh_result.success:
                    return ConnectorResult.error_result("Not connected and token refresh failed")
            else:
                return ConnectorResult.error_result("Not connected to OAuth2 service")
        
        try:
            # Get request parameters
            method = kwargs.get("method", "GET").upper()
            path = kwargs.get("path", "")
            params = kwargs.get("params", {})
            data = kwargs.get("data")
            json_data = kwargs.get("json")
            files = kwargs.get("files")
            headers = kwargs.get("headers", {})
            
            # Make request
            try:
                response = None
                
                if method == "GET":
                    response = await self.client.get(path, params=params, headers=headers)
                elif method == "POST":
                    response = await self.client.post(
                        path, params=params, data=data, json=json_data, files=files, headers=headers
                    )
                elif method == "PUT":
                    response = await self.client.put(
                        path, params=params, data=data, json=json_data, files=files, headers=headers
                    )
                elif method == "PATCH":
                    response = await self.client.patch(
                        path, params=params, data=data, json=json_data, files=files, headers=headers
                    )
                elif method == "DELETE":
                    response = await self.client.delete(
                        path, params=params, data=data, json=json_data, headers=headers
                    )
                elif method == "HEAD":
                    response = await self.client.head(path, params=params, headers=headers)
                elif method == "OPTIONS":
                    response = await self.client.options(path, params=params, headers=headers)
                else:
                    return ConnectorResult.error_result(f"Unsupported HTTP method: {method}")
                
                # Parse response
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = response.text
                else:
                    response_data = response.text
                
                # Check for token expiration error
                if response.status_code == 401:
                    # Try to refresh token
                    refresh_token = self.connection_config.credentials.get("refresh_token")
                    client_id = self.connection_config.credentials.get("client_id")
                    client_secret = self.connection_config.credentials.get("client_secret")
                    
                    if refresh_token and client_id:
                        refresh_result = await self._refresh_token(client_id, client_secret, refresh_token)
                        
                        if refresh_result.success:
                            # Retry request with new token
                            return await self.execute(**kwargs)
                    
                    # Token refresh failed or not possible
                    return ConnectorResult.error_result(
                        "Authentication error: Token expired or invalid",
                        metadata={
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "requires_reauthorization": True,
                        }
                    )
                
                # Handle other errors
                if response.status_code >= 400:
                    return ConnectorResult.error_result(
                        f"API error: {response.status_code} {response.reason_phrase}",
                        metadata={
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "data": response_data,
                        }
                    )
                
                return ConnectorResult.success_result(
                    data=response_data,
                    metadata={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                        "elapsed": response.elapsed.total_seconds(),
                    }
                )
            except httpx.RequestError as e:
                return ConnectorResult.error_result(
                    f"Request error: {str(e)}",
                    metadata={
                        "method": method,
                        "path": path,
                        "error_type": type(e).__name__,
                    }
                )
        except Exception as e:
            logger.error(f"Error executing OAuth2 API request: {str(e)}")
            return ConnectorResult.error_result(f"Error executing request: {str(e)}")
    
    async def query(self, **kwargs) -> ConnectorResult:
        """
        Query data using OAuth2 authentication.
        
        This is a convenience alias for executing a GET request.
        
        Args:
            **kwargs: Parameters for the query
                - path: API endpoint path
                - params: Query parameters
                - headers: Additional headers
            
        Returns:
            Result of the query
        """
        # Set method to GET and delegate to execute
        kwargs["method"] = "GET"
        return await self.execute(**kwargs)
    
    async def get_metadata(self, **kwargs) -> ConnectorResult:
        """
        Get metadata about the OAuth2 connection.
        
        Args:
            **kwargs: Parameters for the metadata retrieval
            
        Returns:
            Result containing metadata
        """
        metadata_type = kwargs.get("type", "connection")
        
        if metadata_type == "connection":
            # Return connection metadata
            if not self.connection_config:
                return ConnectorResult.error_result("No connection configuration available")
            
            # Create sanitized version without sensitive data
            sanitized_credentials = {}
            if self.connection_config.credentials:
                for key, value in self.connection_config.credentials.items():
                    if key in ("client_id", "token_type", "expires_at"):
                        sanitized_credentials[key] = value
                    elif key == "access_token" and value:
                        sanitized_credentials[key] = "[REDACTED]"
                    elif key == "refresh_token" and value:
                        sanitized_credentials[key] = "[REDACTED]"
                    elif key == "client_secret" and value:
                        sanitized_credentials[key] = "[REDACTED]"
            
            token_info = None
            if self.token_info:
                # Calculate token expiration
                expires_at = self.token_info.get("expires_at")
                expires_in = 0
                
                if expires_at:
                    expires_in = max(0, int(expires_at - time.time()))
                
                token_info = {
                    "token_type": self.token_info.get("token_type"),
                    "expires_in": expires_in,
                    "has_refresh_token": "refresh_token" in self.token_info,
                }
            
            return ConnectorResult.success_result(
                data={
                    "flow_type": self.auth_flow,
                    "status": self.connection_config.status,
                    "last_connected": self.connection_config.last_connected,
                    "credentials": sanitized_credentials,
                    "token_info": token_info,
                }
            )
        else:
            return ConnectorResult.error_result(f"Unsupported metadata type: {metadata_type}")