"""
Authentication and authorization components for the Supertrack platform.
"""

from .jwt_utils import (
    token_validator, validate_token_from_header, get_user_from_request,
    generate_token_for_user, JWTValidationError
)
from .tenant_context import (
    TenantContext, TenantRole, get_current_tenant, require_tenant_context,
    get_user_tenants, create_tenant_context_from_request, tenant_required
)

__all__ = [
    'token_validator', 'validate_token_from_header', 'get_user_from_request',
    'generate_token_for_user', 'JWTValidationError',
    'TenantContext', 'TenantRole', 'get_current_tenant', 'require_tenant_context',
    'get_user_tenants', 'create_tenant_context_from_request', 'tenant_required',
]