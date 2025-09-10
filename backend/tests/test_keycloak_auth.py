"""
Unit tests for Keycloak authentication system
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import jwt
import json
import sys
import os
from flask import Flask, g
from keycloak.exceptions import KeycloakError

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import modules to test
from app.config.keycloak_config import KeycloakConfig
from app.utils.auth_utils import (
    TokenValidator, 
    AuthenticationError,
    extract_token_from_request,
    get_user_info_from_token,
    has_role,
    has_any_role
)
from app.middleware.auth_middleware import AuthMiddleware
from app.routes.auth_routes import auth_bp

class TestKeycloakConfig(unittest.TestCase):
    """Test Keycloak configuration management"""
    
    def setUp(self):
        self.original_env = {}
        
    def tearDown(self):
        # Restore original environment
        import os
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    @patch.dict('os.environ', {
        'KEYCLOAK_ENABLED': 'true',
        'KEYCLOAK_SERVER_URL': 'http://test-keycloak:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_CLIENT_ID': 'test-client',
        'KEYCLOAK_CLIENT_SECRET': 'test-secret'
    })
    def test_config_enabled(self):
        """Test configuration when Keycloak is enabled"""
        config = KeycloakConfig()
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.server_url, 'http://test-keycloak:8080')
        self.assertEqual(config.realm, 'test-realm')
        self.assertEqual(config.client_id, 'test-client')
        self.assertEqual(config.client_secret, 'test-secret')
    
    @patch.dict('os.environ', {'KEYCLOAK_ENABLED': 'false'})
    def test_config_disabled(self):
        """Test configuration when Keycloak is disabled"""
        config = KeycloakConfig()
        
        self.assertFalse(config.enabled)
    
    @patch.dict('os.environ', {
        'KEYCLOAK_ENABLED': 'true',
        'KEYCLOAK_SERVER_URL': 'http://test-keycloak:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_CLIENT_ID': 'test-client'
        # Missing KEYCLOAK_CLIENT_SECRET
    })
    def test_config_validation_missing_secret(self):
        """Test configuration validation with missing client secret"""
        with self.assertRaises(ValueError) as context:
            KeycloakConfig()
        
        self.assertIn('client_secret', str(context.exception))
    
    @patch('backend.app.config.keycloak_config.KeycloakOpenID')
    @patch.dict('os.environ', {
        'KEYCLOAK_ENABLED': 'true',
        'KEYCLOAK_SERVER_URL': 'http://test-keycloak:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_CLIENT_ID': 'test-client',
        'KEYCLOAK_CLIENT_SECRET': 'test-secret'
    })
    def test_get_openid_client(self, mock_keycloak_openid):
        """Test OpenID client creation"""
        config = KeycloakConfig()
        client = config.get_openid_client()
        
        mock_keycloak_openid.assert_called_once_with(
            server_url='http://test-keycloak:8080',
            client_id='test-client',
            realm_name='test-realm',
            client_secret_key='test-secret'
        )
        self.assertIsNotNone(client)


class TestTokenValidator(unittest.TestCase):
    """Test JWT token validation"""
    
    def setUp(self):
        self.validator = TokenValidator()
        self.mock_keycloak_openid = Mock()
        self.validator.keycloak_openid = self.mock_keycloak_openid
    
    def test_validate_token_success(self):
        """Test successful token validation"""
        # Mock public key
        self.mock_keycloak_openid.public_key.return_value = "test_public_key"
        
        # Mock JWT decode
        expected_payload = {
            'sub': 'user123',
            'preferred_username': 'testuser',
            'email': 'test@example.com',
            'realm_access': {'roles': ['user']},
            'aud': 'test-client'
        }
        
        with patch('jwt.decode', return_value=expected_payload):
            result = self.validator.validate_token('valid_token')
            
            self.assertEqual(result, expected_payload)
    
    def test_validate_token_expired(self):
        """Test token validation with expired token"""
        self.mock_keycloak_openid.public_key.return_value = "test_public_key"
        
        with patch('jwt.decode', side_effect=jwt.ExpiredSignatureError()):
            with self.assertRaises(AuthenticationError) as context:
                self.validator.validate_token('expired_token')
            
            self.assertIn('expired', str(context.exception))
    
    def test_validate_token_invalid(self):
        """Test token validation with invalid token"""
        self.mock_keycloak_openid.public_key.return_value = "test_public_key"
        
        with patch('jwt.decode', side_effect=jwt.InvalidTokenError()):
            with self.assertRaises(AuthenticationError) as context:
                self.validator.validate_token('invalid_token')
            
            self.assertIn('Invalid token', str(context.exception))
    
    def test_validate_token_no_keycloak(self):
        """Test token validation when Keycloak is not configured"""
        validator = TokenValidator()
        validator.keycloak_openid = None
        
        with self.assertRaises(AuthenticationError) as context:
            validator.validate_token('any_token')
        
        self.assertIn('not configured', str(context.exception))


class TestAuthUtils(unittest.TestCase):
    """Test authentication utility functions"""
    
    def test_extract_token_from_request_valid(self):
        """Test extracting valid Bearer token from request"""
        with patch('flask.request') as mock_request:
            mock_request.headers.get.return_value = 'Bearer test_token_123'
            
            token = extract_token_from_request()
            self.assertEqual(token, 'test_token_123')
    
    def test_extract_token_from_request_no_header(self):
        """Test extracting token when no Authorization header"""
        with patch('flask.request') as mock_request:
            mock_request.headers.get.return_value = None
            
            token = extract_token_from_request()
            self.assertIsNone(token)
    
    def test_extract_token_from_request_invalid_format(self):
        """Test extracting token with invalid format"""
        with patch('flask.request') as mock_request:
            mock_request.headers.get.return_value = 'Invalid format'
            
            token = extract_token_from_request()
            self.assertIsNone(token)
    
    def test_get_user_info_from_token(self):
        """Test extracting user info from token data"""
        token_data = {
            'sub': 'user123',
            'preferred_username': 'testuser',
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'realm_access': {'roles': ['user', 'admin']},
            'resource_access': {
                'test-client': {'roles': ['client_user']}
            }
        }
        
        with patch('backend.app.utils.auth_utils.keycloak_config') as mock_config:
            mock_config.client_id = 'test-client'
            
            user_info = get_user_info_from_token(token_data)
            
            expected = {
                'user_id': 'user123',
                'username': 'testuser',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'roles': ['user', 'admin'],
                'client_roles': ['client_user']
            }
            
            self.assertEqual(user_info, expected)
    
    def test_has_role_true(self):
        """Test role checking when user has role"""
        user_roles = ['user', 'admin', 'viewer']
        self.assertTrue(has_role(user_roles, 'admin'))
    
    def test_has_role_false(self):
        """Test role checking when user doesn't have role"""
        user_roles = ['user', 'viewer']
        self.assertFalse(has_role(user_roles, 'admin'))
    
    def test_has_any_role_true(self):
        """Test checking if user has any of multiple roles"""
        user_roles = ['user', 'viewer']
        required_roles = ['admin', 'user', 'superuser']
        self.assertTrue(has_any_role(user_roles, required_roles))
    
    def test_has_any_role_false(self):
        """Test checking if user has any role when they don't"""
        user_roles = ['viewer']
        required_roles = ['admin', 'superuser']
        self.assertFalse(has_any_role(user_roles, required_roles))


class TestAuthMiddleware(unittest.TestCase):
    """Test authentication middleware"""
    
    def setUp(self):
        self.app = Flask(__name__)
        self.middleware = AuthMiddleware()
        
    def test_should_skip_auth_health_check(self):
        """Test that health check endpoints skip authentication"""
        with self.app.test_request_context('/health'):
            self.assertTrue(self.middleware._should_skip_auth())
    
    def test_should_skip_auth_static_files(self):
        """Test that static files skip authentication"""
        with self.app.test_request_context('/static/style.css'):
            self.assertTrue(self.middleware._should_skip_auth())
    
    def test_should_skip_auth_auth_endpoints(self):
        """Test that auth endpoints skip authentication"""
        with self.app.test_request_context('/api/auth/login'):
            self.assertTrue(self.middleware._should_skip_auth())
    
    def test_should_skip_auth_options_request(self):
        """Test that OPTIONS requests skip authentication"""
        with self.app.test_request_context('/api/devices', method='OPTIONS'):
            self.assertTrue(self.middleware._should_skip_auth())
    
    def test_should_not_skip_auth_api_endpoint(self):
        """Test that regular API endpoints don't skip authentication"""
        with self.app.test_request_context('/api/devices'):
            self.assertFalse(self.middleware._should_skip_auth())


class TestAuthRoutes(unittest.TestCase):
    """Test authentication routes"""
    
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Import and register auth blueprint
        from backend.app.routes.auth_routes import auth_bp
        self.app.register_blueprint(auth_bp)
    
    @patch('backend.app.routes.auth_routes.keycloak_config')
    def test_get_auth_config_disabled(self, mock_config):
        """Test getting auth config when Keycloak is disabled"""
        mock_config.enabled = False
        mock_config.get_config_dict.return_value = {'enabled': False}
        
        response = self.client.get('/api/auth/config')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['enabled'])
    
    @patch('backend.app.routes.auth_routes.keycloak_config')
    def test_login_keycloak_disabled(self, mock_config):
        """Test login when Keycloak is disabled"""
        mock_config.enabled = False
        
        response = self.client.post('/api/auth/login')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('not enabled', data['error'])


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestKeycloakConfig,
        TestTokenValidator,
        TestAuthUtils,
        TestAuthMiddleware,
        TestAuthRoutes
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with error code if tests failed
    import sys
    sys.exit(0 if result.wasSuccessful() else 1)
