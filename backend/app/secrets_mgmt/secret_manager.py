"""
Enhanced SecretManager implementation for the Device Simulator.

This module provides a comprehensive secret management system with encryption,
key rotation, and multiple provider support.
"""

import os
import logging
from typing import Dict, Optional, List, Any
from .interfaces import SecretManagerInterface, EnvironmentValidator
from .providers import (
    EnvironmentSecretProvider, 
    FileSecretProvider, 
    CompositeSecretProvider,
    DockerSecretsProvider
)
from .encryption import FernetEncryptionProvider

logger = logging.getLogger(__name__)


class SecretManager(SecretManagerInterface):
    """Enhanced secret manager with multiple providers and encryption support."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the secret manager.
        
        Args:
            config: Configuration dictionary for providers and encryption
        """
        self.config = config or {}
        self._secret_provider = None
        self._encryption_provider = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize secret and encryption providers."""
        try:
            # Initialize encryption provider
            encryption_config = self.config.get('encryption', {})
            key_storage_path = encryption_config.get('key_storage_path')
            self._encryption_provider = FernetEncryptionProvider(key_storage_path)
            
            # Initialize secret providers in priority order
            providers = []
            
            # Docker secrets (highest priority in containerized environments)
            if self.config.get('use_docker_secrets', False):
                docker_provider = DockerSecretsProvider()
                if docker_provider.is_available():
                    providers.append(docker_provider)
                    logger.info("Docker secrets provider initialized")
            
            # Environment variables (high priority)
            env_prefix = self.config.get('env_prefix', 'DEVSIM_')
            env_provider = EnvironmentSecretProvider(env_prefix)
            providers.append(env_provider)
            logger.info("Environment secrets provider initialized")
            
            # File-based storage (fallback)
            file_config = self.config.get('file_storage', {})
            secrets_dir = file_config.get('secrets_dir')
            file_provider = FileSecretProvider(secrets_dir)
            if file_provider.is_available():
                providers.append(file_provider)
                logger.info("File secrets provider initialized")
            
            # Use composite provider to try multiple sources
            self._secret_provider = CompositeSecretProvider(providers)
            
            logger.info(f"SecretManager initialized with {len(providers)} providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize SecretManager: {e}")
            raise RuntimeError("Critical security error: Unable to initialize secret management system")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key."""
        try:
            return self._secret_provider.get_secret(key)
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key}: {e}")
            return None
    
    def set_secret(self, key: str, value: str, encrypt: bool = True) -> bool:
        """Store a secret with optional encryption."""
        try:
            if encrypt and self._encryption_provider:
                # Encrypt the value before storing
                encrypted_payload = self._encryption_provider.encrypt(value)
                # Store as JSON string
                import json
                value_to_store = json.dumps(encrypted_payload)
            else:
                value_to_store = value
            
            return self._secret_provider.set_secret(key, value_to_store)
            
        except Exception as e:
            logger.error(f"Failed to store secret {key}: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        try:
            return self._secret_provider.delete_secret(key)
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False
    
    def encrypt_credential(self, data: str) -> Dict[str, Any]:
        """Encrypt credential data."""
        try:
            if not self._encryption_provider:
                raise RuntimeError("Encryption provider not available")
            
            return self._encryption_provider.encrypt(data)
            
        except Exception as e:
            logger.error("Failed to encrypt credential (sensitive data not logged)")
            raise RuntimeError("Failed to encrypt credential data")
    
    def decrypt_credential(self, encrypted_payload: Dict[str, Any]) -> str:
        """Decrypt credential data."""
        try:
            if not self._encryption_provider:
                raise RuntimeError("Encryption provider not available")
            
            return self._encryption_provider.decrypt(encrypted_payload)
            
        except Exception as e:
            logger.error("Failed to decrypt credential (sensitive data not logged)")
            raise RuntimeError("Failed to decrypt credential data")
    
    def rotate_keys(self, force: bool = False) -> str:
        """Rotate encryption keys."""
        try:
            if not self._encryption_provider:
                raise RuntimeError("Encryption provider not available")
            
            return self._encryption_provider.rotate_keys(force)
            
        except Exception as e:
            logger.error(f"Failed to rotate keys: {e}")
            raise RuntimeError("Failed to rotate encryption keys")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the secret management system."""
        try:
            status = {
                'secret_provider': {
                    'available': self._secret_provider.is_available() if self._secret_provider else False,
                    'type': type(self._secret_provider).__name__ if self._secret_provider else None
                },
                'encryption_provider': {
                    'available': self._encryption_provider is not None,
                    'type': type(self._encryption_provider).__name__ if self._encryption_provider else None
                }
            }
            
            # Add encryption key status if available
            if self._encryption_provider:
                try:
                    key_status = self._encryption_provider.get_key_status()
                    status['encryption_keys'] = key_status
                except Exception as e:
                    status['encryption_keys'] = {'error': str(e)}
            
            # Test basic functionality
            test_key = '_health_check_test'
            test_value = 'test_value_12345'
            
            try:
                # Test secret storage and retrieval
                if self.set_secret(test_key, test_value, encrypt=False):
                    retrieved = self.get_secret(test_key)
                    if retrieved == test_value:
                        status['secret_operations'] = 'healthy'
                        self.delete_secret(test_key)  # Cleanup
                    else:
                        status['secret_operations'] = 'failed_retrieval'
                else:
                    status['secret_operations'] = 'failed_storage'
            except Exception as e:
                status['secret_operations'] = f'error: {e}'
            
            # Test encryption if available
            if self._encryption_provider:
                try:
                    encrypted = self.encrypt_credential(test_value)
                    decrypted = self.decrypt_credential(encrypted)
                    if decrypted == test_value:
                        status['encryption_operations'] = 'healthy'
                    else:
                        status['encryption_operations'] = 'failed_decryption'
                except Exception as e:
                    status['encryption_operations'] = f'error: {e}'
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {'error': 'Unable to retrieve health status'}


class DevSimEnvironmentValidator(EnvironmentValidator):
    """Environment variable validator for Device Simulator."""
    
    REQUIRED_VARIABLES = {
        'SECRET_KEY': {
            'description': 'Flask secret key for session management',
            'validator': lambda x: len(x) >= 32,
            'error': 'Must be at least 32 characters long'
        },
        'DATABASE_URL': {
            'description': 'Database connection URL',
            'validator': lambda x: x.startswith(('sqlite:///', 'postgresql://', 'mysql://')),
            'error': 'Must be a valid database URL'
        }
    }
    
    OPTIONAL_VARIABLES = {
        'ENCRYPTION_KEY': {
            'description': 'Base64 encoded Fernet encryption key',
            'validator': lambda x: len(x) == 44 and x.replace('=', '').replace('-', '').replace('_', '').isalnum(),
            'error': 'Must be a valid base64 Fernet key (44 characters)'
        },
        'JWT_SECRET_KEY': {
            'description': 'JWT token signing key',
            'validator': lambda x: len(x) >= 32,
            'error': 'Must be at least 32 characters long'
        },
        'AUTHENTICATION_ENABLED': {
            'description': 'Enable/disable authentication system',
            'validator': lambda x: x.lower() in ('true', 'false', '1', '0'),
            'error': 'Must be true/false or 1/0'
        },
        'FLASK_ENV': {
            'description': 'Flask environment mode',
            'validator': lambda x: x in ('development', 'production', 'testing'),
            'error': 'Must be development, production, or testing'
        }
    }
    
    def validate_required_variables(self) -> Dict[str, Any]:
        """Validate that all required environment variables are present and valid."""
        results = {
            'valid': True,
            'missing': [],
            'invalid': {},
            'warnings': []
        }
        
        # Check required variables
        for var_name, config in self.REQUIRED_VARIABLES.items():
            value = os.environ.get(var_name)
            
            if not value:
                results['missing'].append(var_name)
                results['valid'] = False
            elif not config['validator'](value):
                results['invalid'][var_name] = config['error']
                results['valid'] = False
        
        # Check optional variables if present
        for var_name, config in self.OPTIONAL_VARIABLES.items():
            value = os.environ.get(var_name)
            
            if value and not config['validator'](value):
                results['invalid'][var_name] = config['error']
                results['valid'] = False
        
        # Security warnings
        if os.environ.get('FLASK_ENV') == 'development':
            results['warnings'].append('Running in development mode - not suitable for production')
        
        if not os.environ.get('ENCRYPTION_KEY'):
            results['warnings'].append('No encryption key configured - credentials will not be encrypted')
        
        return results
    
    def get_missing_variables(self) -> List[str]:
        """Get list of missing required environment variables."""
        missing = []
        for var_name in self.REQUIRED_VARIABLES:
            if not os.environ.get(var_name):
                missing.append(var_name)
        return missing
    
    def get_invalid_variables(self) -> Dict[str, str]:
        """Get dictionary of invalid environment variables and their issues."""
        invalid = {}
        
        # Check all variables (required and optional)
        all_variables = {**self.REQUIRED_VARIABLES, **self.OPTIONAL_VARIABLES}
        
        for var_name, config in all_variables.items():
            value = os.environ.get(var_name)
            if value and not config['validator'](value):
                invalid[var_name] = config['error']
        
        return invalid


# Global instance for easy access
_secret_manager_instance = None

def get_secret_manager() -> SecretManager:
    """Get the global SecretManager instance."""
    global _secret_manager_instance
    if _secret_manager_instance is None:
        config = {
            'use_docker_secrets': os.environ.get('USE_DOCKER_SECRETS', 'false').lower() == 'true',
            'env_prefix': os.environ.get('SECRET_ENV_PREFIX', 'DEVSIM_'),
            'encryption': {
                'key_storage_path': os.environ.get('ENCRYPTION_KEY_STORAGE_PATH')
            },
            'file_storage': {
                'secrets_dir': os.environ.get('SECRETS_STORAGE_DIR')
            }
        }
        _secret_manager_instance = SecretManager(config)
    return _secret_manager_instance
