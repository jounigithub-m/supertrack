# Supertrack Connector Endpoints

This directory contains the Azure Functions that implement the connector API for the Supertrack platform. These endpoints allow integration with external systems via standardized connectors.

## Available Endpoints

### Main Connector Endpoint (`/api/v1/connectors`)

The main connector endpoint provides:
- List of available connector types
- Schema information for connector configuration
- Configuration validation

**Endpoints:**
- `GET /api/v1/connectors`: List all available connector types
- `GET /api/v1/connectors/{connector_type}`: Get configuration schema for a specific connector type
- `POST /api/v1/connectors/{connector_type}/validate`: Validate a connector configuration

### OAuth Connector Endpoint (`/api/v1/connectors/oauth`)

The OAuth connector endpoint handles authentication and authorization for OAuth-based connectors:
- OAuth2 flow initiation
- Callback handling
- Connection management

**Endpoints:**
- `GET /api/v1/connectors/oauth`: List all OAuth connections
- `GET /api/v1/connectors/oauth/{connection_id}`: Get details of a specific connection
- `POST /api/v1/connectors/oauth`: Create a new OAuth connection
- `DELETE /api/v1/connectors/oauth/{connection_id}`: Delete a connection
- `POST /api/v1/connectors/oauth/{connection_id}/refresh`: Refresh a connection's tokens
- `POST /api/v1/connectors/oauth/{connection_id}/test`: Test a connection
- `GET /api/v1/connectors/oauth/callback`: OAuth callback endpoint

### Operations Endpoint (`/api/v1/connectors/operations`)

The operations endpoint allows interaction with connected systems:
- Query execution
- Operation execution
- Metadata retrieval
- Message processing
- Session state management

**Endpoints:**
- `POST /api/v1/connectors/operations/{connection_id}/query`: Execute a query
- `POST /api/v1/connectors/operations/{connection_id}/execute`: Execute an operation
- `GET /api/v1/connectors/operations/{connection_id}/metadata`: Get metadata from the connection
- `POST /api/v1/connectors/operations/{connection_id}/message`: Send a message to the connector
- `GET /api/v1/connectors/operations/{connection_id}/state`: Get session state
- `POST /api/v1/connectors/operations/{connection_id}/account`: Set the active account

## Supported Connector Types

### Meta (Facebook/Instagram)

The Meta connector provides access to:
- Facebook Ads data
- Instagram Ads data
- Facebook Pages (organic content)
- Instagram Business accounts (organic content)

### Google Ads

The Google Ads connector provides access to Google Ads data and reporting.

## Authentication

All endpoints require authentication via an Azure AD token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The OAuth callback endpoint is the only exception, which allows anonymous access.

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": "Error message"
}
```

Successful responses follow a standard format:

```json
{
  "success": true,
  "data": { ... },
  "metadata": { ... }
}
```

## Session Management

Connectors support session-based interactions, allowing for stateful operations across multiple requests. Session IDs are returned in responses and can be provided in subsequent requests to maintain state.