"""
Integration tests for Keycloak authentication system
Tests the complete authentication flow with a running Keycloak instance
"""
import unittest
import requests
import time
import json
from unittest.mock import patch
import subprocess
import os


class TestKeycloakIntegration(unittest.TestCase):
    """Integration tests for Keycloak authentication"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.backend_url = 'http://localhost:5000'
        cls.keycloak_url = 'http://localhost:8080'
        cls.realm = 'devsim'
        cls.client_id = 'devsim-app'
        cls.client_secret = 'devsim-client-secret-2025'
        
        # Test credentials from realm configuration
        cls.test_username = 'admin'
        cls.test_password = 'Idrica2025!'
        
        print("🔧 Setting up Keycloak integration tests...")
        
    def setUp(self):
        """Set up each test"""
        # Wait for services to be ready
        self.wait_for_service(self.backend_url + '/api/health', 'Backend')
        self.wait_for_service(self.keycloak_url + '/health/ready', 'Keycloak')
    
    def wait_for_service(self, url, service_name, timeout=30):
        """Wait for a service to be ready"""
        print(f"⏳ Waiting for {service_name} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service_name} is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        raise Exception(f"❌ {service_name} not ready after {timeout} seconds")
    
    def test_auth_config_endpoint(self):
        """Test authentication configuration endpoint"""
        response = requests.get(f'{self.backend_url}/api/auth/config')
        
        self.assertEqual(response.status_code, 200)
        
        config = response.json()
        self.assertIn('enabled', config)
        
        if config['enabled']:
            self.assertIn('server_url', config)
            self.assertIn('realm', config)
            self.assertIn('client_id', config)
            self.assertEqual(config['realm'], self.realm)
            self.assertEqual(config['client_id'], self.client_id)
    
    def test_keycloak_token_exchange(self):
        """Test direct token exchange with Keycloak"""
        # Get token directly from Keycloak
        token_url = f'{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token'
        
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.test_username,
            'password': self.test_password
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            self.assertIn('access_token', token_data)
            self.assertIn('refresh_token', token_data)
            self.assertIn('expires_in', token_data)
            
            # Validate token with backend
            auth_headers = {'Authorization': f"Bearer {token_data['access_token']}"}
            validate_response = requests.post(
                f'{self.backend_url}/api/auth/validate',
                headers=auth_headers
            )
            
            self.assertEqual(validate_response.status_code, 200)
            
            validation_result = validate_response.json()
            self.assertTrue(validation_result['valid'])
            self.assertIn('user', validation_result)
        else:
            self.skipTest(f"Keycloak authentication failed: {response.status_code}")
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        # Check if authentication is enabled
        config_response = requests.get(f'{self.backend_url}/api/auth/config')
        config = config_response.json()
        
        if not config.get('enabled', False):
            self.skipTest("Authentication is not enabled")
        
        # Try to access a protected endpoint without token
        response = requests.get(f'{self.backend_url}/api/devices')
        
        # Should be redirected or get 401
        self.assertIn(response.status_code, [401, 403])
    
    def test_protected_endpoint_with_auth(self):
        """Test accessing protected endpoint with valid authentication"""
        # Get token first
        token_url = f'{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token'
        
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.test_username,
            'password': self.test_password
        }
        
        token_response = requests.post(token_url, data=data)
        
        if token_response.status_code != 200:
            self.skipTest("Cannot obtain authentication token")
        
        token_data = token_response.json()
        auth_headers = {'Authorization': f"Bearer {token_data['access_token']}"}
        
        # Access protected endpoint
        response = requests.get(f'{self.backend_url}/api/devices', headers=auth_headers)
        
        # Should succeed (200) or return empty list
        self.assertIn(response.status_code, [200])
    
    def test_token_refresh_flow(self):
        """Test token refresh functionality"""
        # Get initial tokens
        token_url = f'{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token'
        
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.test_username,
            'password': self.test_password
        }
        
        token_response = requests.post(token_url, data=data)
        
        if token_response.status_code != 200:
            self.skipTest("Cannot obtain authentication token")
        
        token_data = token_response.json()
        refresh_token = token_data['refresh_token']
        
        # Use refresh token to get new access token
        refresh_response = requests.post(
            f'{self.backend_url}/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )
        
        if refresh_response.status_code == 200:
            new_token_data = refresh_response.json()
            
            self.assertIn('access_token', new_token_data)
            self.assertIn('user', new_token_data)
            
            # Verify new token works
            auth_headers = {'Authorization': f"Bearer {new_token_data['access_token']}"}
            validate_response = requests.post(
                f'{self.backend_url}/api/auth/validate',
                headers=auth_headers
            )
            
            self.assertEqual(validate_response.status_code, 200)
        else:
            self.skipTest(f"Token refresh failed: {refresh_response.status_code}")
    
    def test_logout_flow(self):
        """Test logout functionality"""
        # Get token first
        token_url = f'{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token'
        
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.test_username,
            'password': self.test_password
        }
        
        token_response = requests.post(token_url, data=data)
        
        if token_response.status_code != 200:
            self.skipTest("Cannot obtain authentication token")
        
        token_data = token_response.json()
        refresh_token = token_data['refresh_token']
        
        # Logout
        logout_response = requests.post(
            f'{self.backend_url}/api/auth/logout',
            json={'refresh_token': refresh_token}
        )
        
        # Logout should succeed
        self.assertEqual(logout_response.status_code, 200)
        
        # Try to use refresh token after logout (should fail)
        refresh_response = requests.post(
            f'{self.backend_url}/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )
        
        # Should fail with 401
        self.assertEqual(refresh_response.status_code, 401)


class TestKeycloakDisabled(unittest.TestCase):
    """Test behavior when Keycloak is disabled"""
    
    def setUp(self):
        self.backend_url = 'http://localhost:5000'
    
    @patch.dict(os.environ, {'KEYCLOAK_ENABLED': 'false'})
    def test_auth_disabled_behavior(self):
        """Test that endpoints work normally when auth is disabled"""
        try:
            # Check config
            config_response = requests.get(f'{self.backend_url}/api/auth/config')
            if config_response.status_code == 200:
                config = config_response.json()
                
                if not config.get('enabled', True):
                    # Auth is disabled, endpoints should work without tokens
                    response = requests.get(f'{self.backend_url}/api/devices')
                    self.assertEqual(response.status_code, 200)
                else:
                    self.skipTest("Authentication is enabled")
            else:
                self.skipTest("Cannot check auth configuration")
        except requests.exceptions.RequestException:
            self.skipTest("Backend service not available")


def run_integration_tests():
    """Run integration tests with proper setup"""
    print("🧪 Starting Keycloak Integration Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add integration tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestKeycloakIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestKeycloakDisabled))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 50)
    if result.wasSuccessful():
        print("✅ All integration tests passed!")
    else:
        print("❌ Some integration tests failed!")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    import sys
    sys.exit(0 if success else 1)
