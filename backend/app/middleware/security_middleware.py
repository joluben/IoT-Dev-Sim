# =============================================================================
# DevSim Security Middleware
# =============================================================================
# Comprehensive security middleware for DevSim backend providing:
# - Security headers
# - HTTPS enforcement
# - Content Security Policy
# - Rate limiting integration
# =============================================================================

import os
from flask import request, make_response, current_app
from functools import wraps


class SecurityMiddleware:
    """Security middleware for DevSim Flask application"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Process request before handling"""
        # HTTPS enforcement in production
        if self._should_enforce_https():
            if not request.is_secure and not self._is_health_check():
                return self._redirect_to_https()
        
        # Additional security checks can be added here
        return None
    
    def after_request(self, response):
        """Add security headers to response"""
        # Add comprehensive security headers
        self._add_security_headers(response)
        
        # Add CORS headers if needed (handled by Flask-CORS but backup)
        self._add_cors_headers(response)
        
        return response
    
    def _should_enforce_https(self):
        """Check if HTTPS should be enforced"""
        config = current_app.config.get('DEVSIM_CONFIG')
        if config:
            return config.security.force_https and config.environment == 'production'
        return (
            current_app.config.get('FORCE_HTTPS', False) and
            os.getenv('FLASK_ENV') == 'production'
        )
    
    def _is_health_check(self):
        """Check if request is a health check"""
        return request.path.startswith('/api/health')
    
    def _redirect_to_https(self):
        """Redirect HTTP request to HTTPS"""
        url = request.url.replace('http://', 'https://', 1)
        return make_response('', 301, {'Location': url})
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers"""
        
        # Strict Transport Security (HSTS)
        if request.is_secure or self._should_enforce_https():
            config = current_app.config.get('DEVSIM_CONFIG')
            hsts_max_age = config.security.hsts_max_age if config else int(os.getenv('HSTS_MAX_AGE', '31536000'))
            response.headers['Strict-Transport-Security'] = f'max-age={hsts_max_age}; includeSubDomains'
        
        # X-Frame-Options - Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # X-Content-Type-Options - Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy - Control referrer information
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy - Control browser features
        permissions_policy = [
            'geolocation=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'gyroscope=()'
        ]
        
        # Content Security Policy (CSP)
        self._add_content_security_policy(response)
        
        # Additional security headers
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    
    def _add_content_security_policy(self, response):
        
        # Get allowed origins for CSP
        config = current_app.config.get('DEVSIM_CONFIG')
        if config:
            cors_origins = config.security.cors_origins
        else:
            cors_origins = os.getenv('CORS_ORIGINS', '').split(',')
            cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
        
        # Build CSP directives
        csp_directives = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],  # Allow inline scripts for SPA
            'style-src': ["'self'", "'unsafe-inline'"],   # Allow inline styles
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'", "wss:", "ws:"] + cors_origins,
            'media-src': ["'self'"],
            'object-src': ["'none'"],
            'child-src': ["'none'"],
            'frame-src': ["'none'"],
            'worker-src': ["'self'"],
            'manifest-src': ["'self'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'frame-ancestors': ["'none'"],
            'upgrade-insecure-requests': []
        }
        
        # Build CSP string
        csp_parts = []
        for directive, sources in csp_directives.items():
            if sources:
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(directive)
        
        csp_header = '; '.join(csp_parts)
        
        # Use Content-Security-Policy-Report-Only in development for testing
        config = current_app.config.get('DEVSIM_CONFIG')
        if config and config.environment == 'development':
            response.headers['Content-Security-Policy-Report-Only'] = csp_header
        else:
            response.headers['Content-Security-Policy'] = csp_header
    
    def _add_cors_headers(self, response):
        """Add CORS headers as backup (Flask-CORS should handle this)"""
        
        # Only add if Flask-CORS hasn't already added them
        if 'Access-Control-Allow-Origin' not in response.headers:
            
            origin = request.headers.get('Origin')
            config = current_app.config.get('DEVSIM_CONFIG')
            if config:
                cors_origins = config.security.cors_origins
            else:
                cors_origins = os.getenv('CORS_ORIGINS', '').split(',')
                cors_origins = [o.strip() for o in cors_origins if o.strip()]
            
            # Check if origin is allowed
            if origin and origin in cors_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Vary'] = 'Origin'
            elif not cors_origins:  # Development mode
                response.headers['Access-Control-Allow-Origin'] = '*'


def require_https(f):
    """Decorator to require HTTPS for specific endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = current_app.config.get('DEVSIM_CONFIG')
        should_enforce = False
        
        if config:
            should_enforce = config.environment == 'production' and config.security.force_https
        else:
            should_enforce = (os.getenv('FLASK_ENV') == 'production' and 
                            os.getenv('FORCE_HTTPS', 'false').lower() == 'true')
        
        if should_enforce and not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            return make_response('', 301, {'Location': url})
        
        return f(*args, **kwargs)
    return decorated_function


def add_security_headers(response_data=None, status_code=200, headers=None):
    """Helper function to add security headers to manual responses"""
    
    response = make_response(response_data, status_code, headers or {})
    
    # Add basic security headers
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response