"""
Authentication Middleware for Keycloak Integration
Handles request interception and token validation
"""
import logging
from flask import request, jsonify, g
from typing import Optional

from ..config.keycloak_config import keycloak_config
from ..utils.auth_utils import (
    extract_token_from_request,
    token_validator,
    get_user_info_from_token,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware class for handling authentication"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Process request before routing"""
        # Skip authentication for certain paths
        if self._should_skip_auth():
            return None
        
        # Skip if Keycloak is not enabled
        if not keycloak_config.enabled:
            return None
        
        # Try to get token from Authorization header first
        token = extract_token_from_request()
        
        # If no token in header, check session (for Keycloak flow)
        if not token:
            from flask import session
            token = session.get('access_token')
            if token:
                # Also set user info from session
                g.current_user = session.get('user_info', {})
                g.authenticated = True
                logger.debug(f"User authenticated from session: {g.current_user.get('username')}")
                return None
        
        if token:
            try:
                token_data = token_validator.validate_token(token)
                g.current_user = get_user_info_from_token(token_data)
                g.token_data = token_data
                g.authenticated = True
                logger.debug(f"User authenticated: {g.current_user.get('username')}")
            except AuthenticationError as e:
                logger.warning(f"Token validation failed: {e}")
                g.authenticated = False
                g.auth_error = str(e)
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'Invalid or expired token',
                    'auth_required': True
                }), 401
        else:
            # No token provided - require authentication
            g.authenticated = False
            logger.info(f"Authentication required for {request.path}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'Access token required',
                'auth_required': True,
                'auth_url': keycloak_config.get_auth_url()
            }), 401
    
    def after_request(self, response):
        """Process response after routing"""
        # Add CORS headers for Keycloak
        if keycloak_config.enabled:
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            # Add authentication headers
            if hasattr(g, 'current_user') and g.current_user:
                response.headers['X-User-ID'] = g.current_user.get('user_id', '')
                response.headers['X-Username'] = g.current_user.get('username', '')
        
        return response
    
    def _should_skip_auth(self) -> bool:
        """Determine if authentication should be skipped for this request"""
        # Skip for health checks
        if request.path in ['/health', '/api/health', '/ready']:
            return True
        
        # Skip for static files
        if request.path.startswith('/static/'):
            return True
        
        # Skip for auth endpoints
        if request.path.startswith('/api/auth/'):
            return True
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return True
        
        # Skip for root path and HTML pages (let frontend handle auth)
        if request.path in ['/', '/index.html'] or request.path.endswith('.html'):
            return True
        
        # Skip for frontend assets
        if request.path.endswith(('.js', '.css', '.ico', '.png', '.jpg', '.svg')):
            return True
        
        # Only protect API endpoints
        if not request.path.startswith('/api/'):
            return True
        
        return False


def create_auth_middleware(app):
    """Factory function to create and configure auth middleware"""
    middleware = AuthMiddleware(app)
    logger.info("Authentication middleware initialized")
    return middleware
