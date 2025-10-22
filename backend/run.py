#!/usr/bin/env python3
"""
DevSim Application Entry Point
==============================

This module serves as the entry point for the DevSim application.
It handles environment-based configuration and ensures debug mode
is properly controlled based on the deployment environment.

For production deployment, use a WSGI server like Gunicorn instead
of running this script directly.

Usage:
    Development: python run.py
    Production: gunicorn --config gunicorn_config.py run:app
"""

import os
import sys
from app.app import create_app

# Ensure logging is configured early for both dev and prod
try:
    from logging_config import setup_logging, log_startup_info
    setup_logging()
    log_startup_info()
except Exception:
    # Fallback silently; run.py already has safe prints for failures
    pass

# Expose WSGI application for Gunicorn (module:variable -> run:app)
app = create_app()


# Create Flask application instance for WSGI servers (Gunicorn)
def create_wsgi_app():
    """Create Flask application for WSGI deployment"""
    try:
        # Setup logging for production
        flask_env = os.getenv('FLASK_ENV', 'development').lower()
        if flask_env == 'production':
            try:
                from logging_config import setup_logging, log_startup_info
                setup_logging()
                log_startup_info()
            except ImportError:
                # Fallback if logging_config is not available
                import logging
                logging.basicConfig(level=logging.INFO)
                logging.getLogger().info("Using basic logging (logging_config not available)")
        
        # Create and return Flask app
        app = create_app()
        return app
        
    except Exception as e:
        print(f"❌ Failed to create WSGI application: {e}")
        raise


# Global app instance for Gunicorn
app = create_wsgi_app()


def main():
    """Main application entry point with environment-aware configuration"""
    
    # Get environment configuration
    flask_env = os.getenv('FLASK_ENV', 'development').lower()
    flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()
    
    # Determine debug mode based on environment
    if flask_env == 'production':
        # NEVER enable debug in production
        debug_mode = False
        
        # Validate production environment
        if flask_debug in ('true', '1', 'yes'):
            print("❌ ERROR: FLASK_DEBUG cannot be enabled in production environment")
            print("   Set FLASK_DEBUG=false for production deployment")
            sys.exit(1)
            
        # Check for sensitive connections
        allow_sensitive = os.getenv('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower()
        if allow_sensitive in ('true', '1', 'yes'):
            print("❌ ERROR: ALLOW_SENSITIVE_CONNECTIONS must be false in production")
            print("   Set ALLOW_SENSITIVE_CONNECTIONS=false for production deployment")
            sys.exit(1)
            
        print("🔒 Production mode: Debug disabled, security enforced")
        
    elif flask_env == 'testing':
        # Testing environment - debug off for consistent testing
        debug_mode = False
        print("🧪 Testing mode: Debug disabled for consistent testing")
        
    else:
        # Development environment - respect FLASK_DEBUG setting
        debug_mode = flask_debug in ('true', '1', 'yes')
        
        if debug_mode:
            print("🔧 Development mode: Debug enabled")
            print("⚠️  WARNING: Never use debug mode in production!")
        else:
            print("🔧 Development mode: Debug disabled")
    
    try:
        # Use the globally created Flask application instance
        
        # Production deployment warning
        if flask_env == 'production':
            print("⚠️  PRODUCTION DEPLOYMENT NOTICE:")
            print("   This development server is not suitable for production.")
            print("   Use a WSGI server like Gunicorn for production deployment:")
            print("   gunicorn --config gunicorn_config.py run:app")
            print("")
        
        # Start development server
        app.run(
            debug=debug_mode,
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', 5000)),
            use_reloader=debug_mode,  # Only reload in debug mode
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
