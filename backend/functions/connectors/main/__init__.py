"""
Main connector management endpoint for the Supertrack platform.

This Azure Function provides a central endpoint for:
1. Listing available connector types
2. Getting connector configuration schemas
3. Validating connector configurations
4. Redirecting to specific connector operations
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
import azure.functions as func

from backend.shared.auth import (
    validate_token_from_header,
    get_user_from_request,
    create_tenant_context_from_request,
    tenant_required,
)
from backend.shared.agent import (
    ConnectorType,
    ConnectionStatus,
    MetaConnector,
    GoogleAdsConnector,
)

# Set up logging
logger = logging.getLogger("supertrack.connectors.main")

# Available connector types
AVAILABLE_CONNECTORS = [
    {
        "id": "meta",
        "name": "Meta (Facebook/Instagram)",
        "description": "Connect to Meta platforms (Facebook Ads, Instagram Ads, Facebook Pages, Instagram Business)",
        "icon": "facebook",
        "categories": ["social_media", "advertising"],
        "auth_type": "oauth2",
        "variants": [
            {
                "id": "facebook_ads",
                "name": "Facebook Ads",
                "description": "Access Facebook advertising data and insights",
                "icon": "facebook",
                "categories": ["advertising"],
            },
            {
                "id": "instagram_ads",
                "name": "Instagram Ads",
                "description": "Access Instagram advertising data and insights",
                "icon": "instagram",
                "categories": ["advertising"],
            },
            {
                "id": "facebook_organic",
                "name": "Facebook Pages",
                "description": "Access Facebook page data, posts, and insights",
                "icon": "facebook",
                "categories": ["social_media"],
            },
            {
                "id": "instagram_organic",
                "name": "Instagram Business",
                "description": "Access Instagram business account data, media, and insights",
                "icon": "instagram",
                "categories": ["social_media"],
            }
        ]
    },
    {
        "id": "google_ads",
        "name": "Google Ads",
        "description": "Connect to Google Ads to access advertising data and insights",
        "icon": "google",
        "categories": ["advertising"],
        "auth_type": "oauth2",
        "variants": []
    }
]

# Configuration schemas
CONNECTOR_SCHEMAS = {
    "meta": {
        "type": "object",
        "required": ["app_id", "app_secret", "product_types"],
        "properties": {
            "app_id": {
                "type": "string",
                "title": "App ID",
                "description": "Meta App ID"
            },
            "app_secret": {
                "type": "string",
                "title": "App Secret",
                "description": "Meta App Secret",
                "format": "password"
            },
            "product_types": {
                "type": "array",
                "title": "Product Types",
                "description": "Meta product types to access",
                "items": {
                    "type": "string",
                    "enum": ["facebook_ads", "instagram_ads", "facebook_organic", "instagram_organic"]
                }
            }
        }
    },
    "google_ads": {
        "type": "object",
        "required": ["client_id", "client_secret", "developer_token"],
        "properties": {
            "client_id": {
                "type": "string",
                "title": "Client ID",
                "description": "Google OAuth Client ID"
            },
            "client_secret": {
                "type": "string",
                "title": "Client Secret",
                "description": "Google OAuth Client Secret",
                "format": "password"
            },
            "developer_token": {
                "type": "string",
                "title": "Developer Token",
                "description": "Google Ads Developer Token",
                "format": "password"
            }
        }
    }
}

@tenant_required
async def handle_list_connector_types(req: func.HttpRequest, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to list available connector types.
    
    Args:
        req: HTTP request
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    # Get filter parameters
    category = req.params.get("category")
    auth_type = req.params.get("auth_type")
    
    # Filter connectors
    connectors = AVAILABLE_CONNECTORS
    
    if category:
        connectors = [c for c in connectors if category in c.get("categories", [])]
    
    if auth_type:
        connectors = [c for c in connectors if c.get("auth_type") == auth_type]
    
    return func.HttpResponse(
        json.dumps({"connectors": connectors}),
        mimetype="application/json",
        status_code=200
    )

@tenant_required
async def handle_get_connector_schema(req: func.HttpRequest, connector_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle GET request to get configuration schema for a connector type.
    
    Args:
        req: HTTP request
        connector_id: Connector type ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    # Check if connector type exists
    if connector_id not in CONNECTOR_SCHEMAS:
        return func.HttpResponse(
            json.dumps({"error": f"Unknown connector type: {connector_id}"}),
            mimetype="application/json",
            status_code=404
        )
    
    # Get schema
    schema = CONNECTOR_SCHEMAS[connector_id]
    
    return func.HttpResponse(
        json.dumps({"schema": schema}),
        mimetype="application/json",
        status_code=200
    )

@tenant_required
async def handle_validate_connector_config(req: func.HttpRequest, connector_id: str, tenant_context=None) -> func.HttpResponse:
    """
    Handle POST request to validate a connector configuration.
    
    Args:
        req: HTTP request
        connector_id: Connector type ID
        tenant_context: Tenant context
        
    Returns:
        HTTP response
    """
    # Check if connector type exists
    if connector_id not in CONNECTOR_SCHEMAS:
        return func.HttpResponse(
            json.dumps({"error": f"Unknown connector type: {connector_id}"}),
            mimetype="application/json",
            status_code=404
        )
    
    try:
        # Parse request body
        req_body = await req.get_json()
        
        # Get configuration
        config = req_body.get("config", {})
        
        # Get schema
        schema = CONNECTOR_SCHEMAS[connector_id]
        
        # Validate required fields
        required_fields = schema.get("required", [])
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            return func.HttpResponse(
                json.dumps({
                    "valid": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }),
                mimetype="application/json",
                status_code=200
            )
        
        # Validate field types
        properties = schema.get("properties", {})
        type_errors = []
        
        for field, value in config.items():
            if field in properties:
                field_schema = properties[field]
                field_type = field_schema.get("type")
                
                if field_type == "string" and not isinstance(value, str):
                    type_errors.append(f"{field} should be a string")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    type_errors.append(f"{field} should be a number")
                elif field_type == "integer" and not isinstance(value, int):
                    type_errors.append(f"{field} should be an integer")
                elif field_type == "boolean" and not isinstance(value, bool):
                    type_errors.append(f"{field} should be a boolean")
                elif field_type == "array" and not isinstance(value, list):
                    type_errors.append(f"{field} should be an array")
                elif field_type == "object" and not isinstance(value, dict):
                    type_errors.append(f"{field} should be an object")
        
        if type_errors:
            return func.HttpResponse(
                json.dumps({
                    "valid": False,
                    "error": f"Type errors: {', '.join(type_errors)}"
                }),
                mimetype="application/json",
                status_code=200
            )
        
        # Configuration is valid
        return func.HttpResponse(
            json.dumps({"valid": True}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error validating configuration: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error validating configuration: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main entry point for the Azure Function.
    
    Args:
        req: HTTP request
        
    Returns:
        HTTP response
    """
    # Get route segments
    route = req.route_params.get("route", "")
    segments = route.strip("/").split("/")
    
    # Validate token
    try:
        token_result = validate_token_from_header(req.headers)
        if not token_result["valid"]:
            return func.HttpResponse(
                json.dumps({"error": token_result["error"]}),
                mimetype="application/json",
                status_code=401
            )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"Authentication error: {str(e)}"}),
            mimetype="application/json",
            status_code=401
        )
    
    # Route request
    try:
        if len(segments) == 0:
            # List connector types
            if req.method == "GET":
                return await handle_list_connector_types(req)
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Method not allowed"}),
                    mimetype="application/json",
                    status_code=405
                )
        else:
            # Get connector by ID
            connector_id = segments[0]
            
            if len(segments) == 1:
                # Get connector schema
                if req.method == "GET":
                    return await handle_get_connector_schema(req, connector_id)
                else:
                    return func.HttpResponse(
                        json.dumps({"error": "Method not allowed"}),
                        mimetype="application/json",
                        status_code=405
                    )
            elif len(segments) > 1 and segments[1] == "validate":
                # Validate connector configuration
                if req.method == "POST":
                    return await handle_validate_connector_config(req, connector_id)
                else:
                    return func.HttpResponse(
                        json.dumps({"error": "Method not allowed"}),
                        mimetype="application/json",
                        status_code=405
                    )
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Not found"}),
                    mimetype="application/json",
                    status_code=404
                )
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Error handling request: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )