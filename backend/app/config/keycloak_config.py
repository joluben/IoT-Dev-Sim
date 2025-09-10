"""
Keycloak Configuration Module
Handles Keycloak server configuration and client setup
"""
import os
from typing import Optional, Dict, Any
from keycloak import KeycloakOpenID, KeycloakAdmin
import logging

logger = logging.getLogger(__name__)


class KeycloakConfig:
    """Configuration class for Keycloak integration"""
    
    def __init__(self):
        self.enabled = self._get_bool_env('KEYCLOAK_ENABLED', False)
        self.server_url = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
        self.realm = os.getenv('KEYCLOAK_REALM', 'devsim')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'devsim-app')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
        self.admin_username = os.getenv('KEYCLOAK_ADMIN_USERNAME', 'admin')
        self.admin_password = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')
        
        # Validate configuration if Keycloak is enabled
        if self.enabled:
            self._validate_config()
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Convert environment variable to boolean"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _validate_config(self) -> None:
        """Validate required configuration parameters"""
        required_fields = {
            'server_url': self.server_url,
            'realm': self.realm,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            raise ValueError(f"Missing required Keycloak configuration: {', '.join(missing_fields)}")
        
        logger.info(f"Keycloak configuration validated for realm: {self.realm}")
    
    def get_openid_client(self) -> Optional[KeycloakOpenID]:
        """Create and return Keycloak OpenID client"""
        if not self.enabled:
            return None
        
        try:
            client = KeycloakOpenID(
                server_url=self.server_url,
                client_id=self.client_id,
                realm_name=self.realm,
                client_secret_key=self.client_secret
            )
            logger.info(f"Keycloak OpenID client created for realm: {self.realm}")
            return client
        except Exception as e:
            logger.error(f"Failed to create Keycloak OpenID client: {e}")
            raise
    
    def get_admin_client(self) -> Optional[KeycloakAdmin]:
        """Create and return Keycloak Admin client"""
        if not self.enabled:
            return None
        
        try:
            admin_client = KeycloakAdmin(
                server_url=self.server_url,
                username=self.admin_username,
                password=self.admin_password,
                realm_name=self.realm,
                verify=True
            )
            logger.info(f"Keycloak Admin client created for realm: {self.realm}")
            return admin_client
        except Exception as e:
            logger.error(f"Failed to create Keycloak Admin client: {e}")
            raise
    
    def get_auth_url(self, redirect_uri: str = None, state: str = None) -> Optional[str]:
        """Generate authentication URL for login redirect"""
        if not self.enabled:
            return None
        
        if not redirect_uri:
            redirect_uri = "http://localhost:5000/api/auth/callback"
        
        try:
            # Use Keycloak OpenID client to generate proper auth URL with state
            keycloak_openid = self.get_openid_client()
            if keycloak_openid:
                auth_url = keycloak_openid.auth_url(
                    redirect_uri=redirect_uri,
                    scope="openid email profile",
                    state=state
                )
                return auth_url
            else:
                # Fallback: Build Keycloak auth URL manually
                auth_url = (
                    f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/auth"
                    f"?client_id={self.client_id}"
                    f"&redirect_uri={redirect_uri}"
                    f"&response_type=code"
                    f"&scope=openid profile email"
                )
                if state:
                    auth_url += f"&state={state}"
                return auth_url
        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            return None
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return {
            'enabled': self.enabled,
            'server_url': self.server_url,
            'realm': self.realm,
            'client_id': self.client_id,
            'has_client_secret': bool(self.client_secret)
        }


# Global configuration instance
keycloak_config = KeycloakConfig()
