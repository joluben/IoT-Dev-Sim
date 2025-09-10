"""
Authentication Routes for Keycloak Integration
Handles OAuth2 flow, token management, and user authentication
"""
import logging
from flask import Blueprint, request, jsonify, redirect, session, url_for
from urllib.parse import urlencode
import secrets
import requests
from keycloak.exceptions import KeycloakError

from ..config.keycloak_config import keycloak_config
from ..utils.auth_utils import (
    token_validator,
    get_user_info_from_token,
    AuthenticationError,
    extract_token_from_request
)

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/config', methods=['GET'])
def get_auth_config():
    """Get authentication configuration for frontend"""
    config = keycloak_config.get_config_dict()
    
    # Add OAuth2 URLs if Keycloak is enabled
    if keycloak_config.enabled and keycloak_config.get_openid_client():
        try:
            # Generate state parameter for CSRF protection
            import secrets
            state = secrets.token_urlsafe(32)
            session['oauth_state'] = state
            
            # Generate auth URL with state parameter
            auth_url = keycloak_config.get_auth_url(
                redirect_uri=request.host_url.rstrip('/') + '/api/auth/callback',
                state=state
            )
            
            config.update({
                'auth_url': auth_url,
                'logout_url': f"{keycloak_config.server_url}/realms/{keycloak_config.realm}/protocol/openid-connect/logout",
                'callback_url': request.host_url.rstrip('/') + '/api/auth/callback',
                'state': state
            })
        except Exception as e:
            logger.error(f"Failed to generate auth URLs: {e}")
    
    return jsonify(config)


@auth_bp.route('/api/auth/login', methods=['POST'])
def initiate_login():
    """Initiate OAuth2 login flow"""
    if not keycloak_config.enabled:
        return jsonify({'error': 'Keycloak authentication not enabled'}), 400
    
    try:
        keycloak_openid = keycloak_config.get_openid_client()
        if not keycloak_openid:
            return jsonify({'error': 'Keycloak not configured'}), 500
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Get redirect URI from request or use default
        redirect_uri = request.json.get('redirect_uri', request.host_url.rstrip('/') + '/api/auth/callback')
        
        # Generate authorization URL
        auth_url = keycloak_openid.auth_url(
            redirect_uri=redirect_uri,
            scope="openid email profile",
            state=state
        )
        
        return jsonify({
            'auth_url': auth_url,
            'state': state
        })
        
    except KeycloakError as e:
        logger.error(f"Keycloak error during login initiation: {e}")
        return jsonify({'error': 'Authentication service error'}), 503
    except Exception as e:
        logger.error(f"Unexpected error during login initiation: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/api/auth/session', methods=['GET'])
def get_session_tokens():
    """Get tokens from session for frontend"""
    if not keycloak_config.enabled:
        return jsonify({'error': 'Keycloak authentication not enabled'}), 400
    
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'No active session'}), 401
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': session.get('refresh_token'),
        'expires_in': session.get('expires_in'),
        'user': session.get('user_info')
    })


@auth_bp.route('/api/auth/callback', methods=['GET', 'POST'])
def auth_callback():
    """Handle OAuth2 callback from Keycloak"""
    if not keycloak_config.enabled:
        return redirect('/?error=keycloak_disabled')
    
    try:
        # Get authorization code from request
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"OAuth2 error: {error}")
            return redirect(f'/?error={error}')
        
        if not code:
            return redirect('/?error=no_code')
        
        # Verify state parameter (CSRF protection)
        if state != session.get('oauth_state'):
            logger.warning("OAuth2 state mismatch")
            return redirect('/?error=invalid_state')
        
        # Exchange code for tokens
        keycloak_openid = keycloak_config.get_openid_client()
        redirect_uri = request.host_url.rstrip('/') + '/api/auth/callback'
        
        token_response = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=redirect_uri
        )
        
        # Validate and decode access token
        access_token = token_response['access_token']
        token_data = token_validator.validate_token(access_token)
        user_info = get_user_info_from_token(token_data)
        
        # Store tokens in session for the frontend to retrieve
        session['access_token'] = access_token
        session['refresh_token'] = token_response.get('refresh_token')
        session['user_info'] = user_info
        session['expires_in'] = token_response.get('expires_in')
        
        # Clear OAuth state from session
        session.pop('oauth_state', None)
        
        # Redirect to main app with success parameter
        return redirect('/?auth=success')
        
    except KeycloakError as e:
        logger.error(f"Keycloak error during callback: {e}")
        return redirect('/?error=keycloak_error')
    except AuthenticationError as e:
        logger.warning(f"Authentication error during callback: {e}")
        return redirect('/?error=auth_error')
    except Exception as e:
        logger.error(f"Unexpected error during callback: {e}")
        return redirect('/?error=server_error')


@auth_bp.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    if not keycloak_config.enabled:
        return jsonify({'error': 'Keycloak authentication not enabled'}), 400
    
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400
        
        keycloak_openid = keycloak_config.get_openid_client()
        
        # Refresh the token
        token_response = keycloak_openid.refresh_token(refresh_token)
        
        # Validate new access token
        access_token = token_response['access_token']
        token_data = token_validator.validate_token(access_token)
        user_info = get_user_info_from_token(token_data)
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': token_response.get('refresh_token'),
            'expires_in': token_response.get('expires_in'),
            'user': user_info
        })
        
    except KeycloakError as e:
        logger.error(f"Token refresh failed: {e}")
        return jsonify({'error': 'Token refresh failed'}), 401
    except AuthenticationError as e:
        logger.warning(f"Token validation failed during refresh: {e}")
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user and invalidate tokens"""
    if not keycloak_config.enabled:
        return jsonify({'message': 'Logout successful'}), 200
    
    try:
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')
        
        if refresh_token:
            keycloak_openid = keycloak_config.get_openid_client()
            
            # Logout from Keycloak (invalidate refresh token)
            keycloak_openid.logout(refresh_token)
            logger.info("User logged out successfully")
        
        # Clear session
        session.clear()
        
        return jsonify({'message': 'Logout successful'})
        
    except KeycloakError as e:
        logger.warning(f"Keycloak logout error: {e}")
        # Even if Keycloak logout fails, clear local session
        session.clear()
        return jsonify({'message': 'Logout completed with warnings'})
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        session.clear()
        return jsonify({'message': 'Logout completed'})


@auth_bp.route('/api/auth/user', methods=['GET'])
def get_current_user():
    """Get current user information from token"""
    if not keycloak_config.enabled:
        return jsonify({'error': 'Keycloak authentication not enabled'}), 400
    
    try:
        token = extract_token_from_request()
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Validate token and get user info
        token_data = token_validator.validate_token(token)
        user_info = get_user_info_from_token(token_data)
        
        return jsonify({'user': user_info})
        
    except AuthenticationError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/api/auth/validate', methods=['POST'])
def validate_token():
    """Validate access token"""
    if not keycloak_config.enabled:
        return jsonify({'valid': True}), 200
    
    try:
        token = extract_token_from_request()
        if not token:
            return jsonify({'valid': False, 'error': 'No token provided'}), 200
        
        # Validate token
        token_data = token_validator.validate_token(token)
        user_info = get_user_info_from_token(token_data)
        
        return jsonify({
            'valid': True,
            'user': user_info,
            'expires_at': token_data.get('exp')
        })
        
    except AuthenticationError as e:
        return jsonify({'valid': False, 'error': str(e)}), 200
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return jsonify({'valid': False, 'error': 'Validation service error'}), 500
