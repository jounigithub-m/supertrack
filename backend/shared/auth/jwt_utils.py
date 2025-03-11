"""
JWT token validation and handling utilities.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import json
import re

import msal
import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from ..utils.config import settings, get_required_setting

# Configure logging
logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    """Exception raised for JWT validation errors."""
    pass


class TokenValidator:
    """
    Utility for validating JWT tokens from Azure AD B2C.
    """
    
    def __init__(
        self,
        tenant_name: Optional[str] = None,
        client_id: Optional[str] = None
    ):
        """
        Initialize the token validator.
        
        Args:
            tenant_name: Azure AD B2C tenant name. Defaults to settings.
            client_id: Azure AD B2C client ID. Defaults to settings.
        """
        self.tenant_name = tenant_name or get_required_setting("AZURE_AD_B2C_TENANT_NAME")
        self.client_id = client_id or get_required_setting("AZURE_AD_B2C_CLIENT_ID")
        
        # Cache for OpenID configuration
        self._openid_config = None
        self._openid_config_timestamp = 0
        self._jwks = None
        self._jwks_timestamp = 0
        
        # Cache duration in seconds (1 hour)
        self._cache_ttl = 3600
    
    async def get_openid_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get the OpenID configuration from Azure AD B2C.
        
        Args:
            force_refresh: Force refresh the configuration even if cached
            
        Returns:
            OpenID configuration
        """
        # Check if we need to refresh the config
        current_time = time.time()
        if (
            self._openid_config is None or
            force_refresh or
            current_time - self._openid_config_timestamp > self._cache_ttl
        ):
            try:
                # Fetch the OpenID configuration
                config_url = f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/v2.0/.well-known/openid-configuration"
                response = requests.get(config_url)
                response.raise_for_status()
                
                self._openid_config = response.json()
                self._openid_config_timestamp = current_time
            except Exception as e:
                logger.error(f"Error fetching OpenID configuration: {str(e)}")
                raise
        
        return self._openid_config
    
    async def get_jwks(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get the JSON Web Key Set (JWKS) from Azure AD B2C.
        
        Args:
            force_refresh: Force refresh the JWKS even if cached
            
        Returns:
            JWKS
        """
        # Check if we need to refresh the JWKS
        current_time = time.time()
        if (
            self._jwks is None or
            force_refresh or
            current_time - self._jwks_timestamp > self._cache_ttl
        ):
            try:
                # Get the JWKS URI from the OpenID configuration
                openid_config = await self.get_openid_config(force_refresh)
                jwks_uri = openid_config.get("jwks_uri")
                
                if not jwks_uri:
                    raise JWTValidationError("JWKS URI not found in OpenID configuration")
                
                # Fetch the JWKS
                response = requests.get(jwks_uri)
                response.raise_for_status()
                
                self._jwks = response.json()
                self._jwks_timestamp = current_time
            except Exception as e:
                logger.error(f"Error fetching JWKS: {str(e)}")
                raise
        
        return self._jwks
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Decoded token claims if valid
            
        Raises:
            JWTValidationError: If token is invalid
        """
        if not token:
            raise JWTValidationError("Token is empty")
        
        try:
            # Decode token header without verification
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                raise JWTValidationError("No 'kid' found in token header")
            
            # Get the JWKS
            jwks = await self.get_jwks()
            
            # Find the signing key with matching kid
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = key
                    break
            
            if not signing_key:
                # If key not found, force refresh JWKS and try again
                jwks = await self.get_jwks(force_refresh=True)
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        signing_key = key
                        break
                        
                if not signing_key:
                    raise JWTValidationError(f"No signing key found for kid: {kid}")
            
            # Convert JWK to PEM format for PyJWT
            public_key = RSAAlgorithm.from_jwk(json.dumps(signing_key))
            
            # Get the issuer from OpenID configuration
            openid_config = await self.get_openid_config()
            issuer = openid_config.get("issuer")
            
            if not issuer:
                raise JWTValidationError("Issuer not found in OpenID configuration")
            
            # Validate the token
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "require": ["exp", "iat", "nbf", "aud", "iss"]
            }
            
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=issuer,
                options=options
            )
            
            return decoded
        except jwt.ExpiredSignatureError:
            raise JWTValidationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTValidationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            raise JWTValidationError(f"Error validating token: {str(e)}")
    
    async def extract_user_info(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from a validated token.
        
        Args:
            token: JWT token
            
        Returns:
            User information
        """
        # Validate the token first
        claims = await self.validate_token(token)
        
        # Extract user info
        user_info = {
            "id": claims.get("oid") or claims.get("sub"),
            "email": claims.get("emails", [""])[0] if isinstance(claims.get("emails"), list) else claims.get("email", ""),
            "name": claims.get("name", ""),
            "roles": claims.get("roles", []),
            "tenant_id": claims.get("tenant_id", ""),
            "tenant_access": claims.get("tenant_access", []),
        }
        
        return user_info


# Create a singleton instance
token_validator = TokenValidator()


async def validate_token_from_header(auth_header: Optional[str]) -> Dict[str, Any]:
    """
    Validate a token from an Authorization header.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        User information if token is valid
        
    Raises:
        JWTValidationError: If token is invalid or missing
    """
    if not auth_header:
        raise JWTValidationError("Authorization header missing")
    
    # Check for Bearer token
    match = re.match(r"Bearer\s+(.+)", auth_header)
    if not match:
        raise JWTValidationError("Invalid Authorization header format")
    
    token = match.group(1)
    
    # Validate the token and extract user info
    return await token_validator.extract_user_info(token)


async def get_user_from_request(request) -> Dict[str, Any]:
    """
    Get user information from a request.
    
    Args:
        request: HTTP request object
        
    Returns:
        User information if authenticated
        
    Raises:
        JWTValidationError: If not authenticated
    """
    # Get the Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Validate the token
    return await validate_token_from_header(auth_header)


async def generate_token_for_user(
    user_id: str,
    user_email: str,
    user_name: str,
    roles: List[str],
    tenant_id: Optional[str] = None,
    tenant_access: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Generate a JWT token for a user (development only).
    
    WARNING: This should only be used in development environments for testing.
    
    Args:
        user_id: User ID
        user_email: User email
        user_name: User name
        roles: User roles
        tenant_id: Current tenant ID
        tenant_access: List of tenant access entries
        
    Returns:
        JWT token
    """
    if not settings.is_development():
        raise ValueError("This function can only be used in development environments")
    
    # Set default values
    if tenant_access is None:
        tenant_access = []
    
    # Create payload
    payload = {
        "oid": user_id,
        "sub": user_id,
        "email": user_email,
        "emails": [user_email],
        "name": user_name,
        "roles": roles,
        "aud": settings.get_required_setting("AZURE_AD_B2C_CLIENT_ID"),
        "iss": f"https://{settings.get_required_setting('AZURE_AD_B2C_TENANT_NAME')}.b2clogin.com/{settings.get_required_setting('AZURE_AD_B2C_TENANT_NAME')}.onmicrosoft.com/v2.0/",
        "iat": int(time.time()),
        "nbf": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour
        "tenant_access": tenant_access,
    }
    
    if tenant_id:
        payload["tenant_id"] = tenant_id
    
    # Sign token with a simple secret for development
    secret = "dev-secret-key-not-for-production"
    
    return jwt.encode(payload, secret, algorithm="HS256")