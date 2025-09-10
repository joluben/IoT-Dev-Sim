"""
Authentication Utilities for Keycloak Integration
Provides JWT validation, decorators, and user information extraction
"""
import jwt
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable
from flask import request, jsonify, g
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError

from ..config.keycloak_config import keycloak_config

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class TokenValidator:
    """Handles JWT token validation with Keycloak"""
    
    def __init__(self):
        self.keycloak_openid = keycloak_config.get_openid_client()
        self._public_key = None
    
    def get_public_key(self) -> Optional[str]:
        """Get Keycloak public key for token validation"""
        if not self.keycloak_openid:
            return None
        
        if not self._public_key:
            try:
                self._public_key = self.keycloak_openid.public_key()
                logger.debug("Retrieved Keycloak public key")
            except KeycloakError as e:
                logger.error(f"Failed to retrieve Keycloak public key: {e}")
                raise AuthenticationError(f"Cannot retrieve public key: {e}")
        
        return self._public_key
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return decoded payload"""
        if not self.keycloak_openid:
            raise AuthenticationError("Keycloak not configured")
        
        try:
            # Try JWT validation first
            try:
                # Get public key
                public_key = self.get_public_key()
                if not public_key:
                    raise AuthenticationError("Cannot retrieve public key")
                
                # Prepare key for JWT validation
                key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
                
                # Validate token - Skip audience verification for now
                decoded_token = jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    options={"verify_exp": True, "verify_aud": False}
                )
                
                logger.debug(f"Token validated for user: {decoded_token.get('preferred_username')}")
                return decoded_token
                
            except (jwt.InvalidTokenError, KeycloakError) as jwt_error:
                logger.warning(f"JWT validation failed, trying introspection: {jwt_error}")
                # Fallback to introspection
                return self.validate_token_with_introspection(token)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise AuthenticationError("Token has expired")
        except AuthenticationError:
            # Re-raise authentication errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise AuthenticationError(f"Token validation failed: {e}")
    
    def validate_token_with_introspection(self, token: str) -> Dict[str, Any]:
        """Validate token using Keycloak introspection endpoint as fallback"""
        if not self.keycloak_openid:
            raise AuthenticationError("Keycloak not configured")
        
        try:
            token_info = self.keycloak_openid.introspect(token)
            
            if not token_info.get('active', False):
                raise AuthenticationError("Token is not active")
            
            logger.debug(f"Token validated via introspection for user: {token_info.get('username')}")
            return token_info
            
        except KeycloakError as e:
            logger.error(f"Token introspection failed: {e}")
            raise AuthenticationError(f"Token introspection failed: {e}")
    
    def introspect_token(self, token: str) -> Dict[str, Any]:
        """Introspect token using Keycloak introspection endpoint"""
        return self.validate_token_with_introspection(token)


# Global token validator instance
token_validator = TokenValidator()


def extract_token_from_request() -> Optional[str]:
    """Extract Bearer token from request headers"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    if not auth_header.startswith('Bearer '):
        return None
    
    return auth_header[7:]  # Remove 'Bearer ' prefix


def get_user_info_from_token(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract user information from decoded token"""
    # Handle both JWT decoded tokens and introspection responses
    if 'preferred_username' in token_data:
        # JWT token format
        return {
            'user_id': token_data.get('sub'),
            'username': token_data.get('preferred_username'),
            'email': token_data.get('email'),
            'first_name': token_data.get('given_name'),
            'last_name': token_data.get('family_name'),
            'roles': token_data.get('realm_access', {}).get('roles', []),
            'client_roles': token_data.get('resource_access', {}).get(keycloak_config.client_id, {}).get('roles', [])
        }
    else:
        # Introspection response format
        return {
            'user_id': token_data.get('sub'),
            'username': token_data.get('username'),
            'email': token_data.get('email'),
            'first_name': token_data.get('given_name'),
            'last_name': token_data.get('family_name'),
            'roles': token_data.get('realm_access', {}).get('roles', []) if isinstance(token_data.get('realm_access'), dict) else [],
            'client_roles': []
        }


def has_role(user_roles: list, required_role: str) -> bool:
    """Check if user has required role"""
    return required_role in user_roles


def has_any_role(user_roles: list, required_roles: list) -> bool:
    """Check if user has any of the required roles"""
    return any(role in user_roles for role in required_roles)


def keycloak_auth_required(f: Callable) -> Callable:
    """Decorator to require Keycloak authentication for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip authentication if Keycloak is not enabled
        if not keycloak_config.enabled:
            return f(*args, **kwargs)
        
        try:
            # Extract token from request
            token = extract_token_from_request()
            if not token:
                return jsonify({'error': 'Authorization token required'}), 401
            
            # Validate token
            token_data = token_validator.validate_token(token)
            
            # Store user info in Flask g object for use in the route
            g.current_user = get_user_info_from_token(token_data)
            g.token_data = token_data
            
            return f(*args, **kwargs)
            
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            return jsonify({'error': 'Authentication service unavailable'}), 503
    
    return decorated_function


def require_role(required_role: str):
    """Decorator to require specific role for a route"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @keycloak_auth_required
        def decorated_function(*args, **kwargs):
            if not keycloak_config.enabled:
                return f(*args, **kwargs)
            
            user_roles = g.current_user.get('roles', [])
            client_roles = g.current_user.get('client_roles', [])
            all_roles = user_roles + client_roles
            
            if not has_role(all_roles, required_role):
                return jsonify({'error': f'Role "{required_role}" required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_any_role(required_roles: list):
    """Decorator to require any of the specified roles for a route"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @keycloak_auth_required
        def decorated_function(*args, **kwargs):
            if not keycloak_config.enabled:
                return f(*args, **kwargs)
            
            user_roles = g.current_user.get('roles', [])
            client_roles = g.current_user.get('client_roles', [])
            all_roles = user_roles + client_roles
            
            if not has_any_role(all_roles, required_roles):
                return jsonify({'error': f'One of these roles required: {", ".join(required_roles)}'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def conditional_auth_required(f: Callable) -> Callable:
    """Decorator that applies authentication only if Keycloak is enabled"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if keycloak_config.enabled:
            return keycloak_auth_required(f)(*args, **kwargs)
        else:
            return f(*args, **kwargs)
    
    return decorated_function
