"""
Secret provider implementations for the Device Simulator.

This module contains concrete implementations of secret providers including
environment-based and file-based providers.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
from pathlib import Path
from .interfaces import SecretProvider

logger = logging.getLogger(__name__)


class EnvironmentSecretProvider(SecretProvider):
    """Environment variable-based secret provider."""
    
    def __init__(self, prefix: str = "DEVSIM_"):
        """
        Initialize the environment secret provider.
        
        Args:
            prefix: Prefix for environment variables
        """
        self.prefix = prefix
        
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from environment variables."""
        env_key = f"{self.prefix}{key.upper()}"
        return os.environ.get(env_key)
    
    def set_secret(self, key: str, value: str) -> bool:
        """Set a secret in environment variables (runtime only)."""
        try:
            env_key = f"{self.prefix}{key.upper()}"
            os.environ[env_key] = value
            return True
        except Exception as e:
            logger.error(f"Failed to set environment secret {key}: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from environment variables."""
        try:
            env_key = f"{self.prefix}{key.upper()}"
            if env_key in os.environ:
                del os.environ[env_key]
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete environment secret {key}: {e}")
            return False
    
    def list_secrets(self) -> List[str]:
        """List all secrets with the configured prefix."""
        secrets = []
        for env_key in os.environ:
            if env_key.startswith(self.prefix):
                secret_key = env_key[len(self.prefix):].lower()
                secrets.append(secret_key)
        return secrets
    
    def is_available(self) -> bool:
        """Environment provider is always available."""
        return True


class FileSecretProvider(SecretProvider):
    """File-based secret provider with secure storage."""
    
    def __init__(self, secrets_dir: str = None):
        """
        Initialize the file secret provider.
        
        Args:
            secrets_dir: Directory to store secret files
        """
        if secrets_dir is None:
            secrets_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'secrets')
        
        self.secrets_dir = Path(secrets_dir)
        self._ensure_secrets_directory()
    
    def _ensure_secrets_directory(self):
        """Ensure the secrets directory exists with proper permissions."""
        try:
            self.secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Set permissions on existing directory
            os.chmod(self.secrets_dir, 0o700)
        except Exception as e:
            logger.error(f"Failed to create secrets directory: {e}")
            raise RuntimeError("Cannot initialize file secret provider")
    
    def _get_secret_file_path(self, key: str) -> Path:
        """Get the file path for a secret key."""
        # Sanitize key for filename
        safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-')).lower()
        return self.secrets_dir / f"{safe_key}.secret"
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from file storage."""
        try:
            secret_file = self._get_secret_file_path(key)
            if secret_file.exists():
                with open(secret_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('value')
            return None
        except Exception as e:
            logger.error(f"Failed to read secret {key}: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret in file storage."""
        try:
            secret_file = self._get_secret_file_path(key)
            from datetime import datetime
            data = {
                'key': key,
                'value': value,
                'created_at': (
                    datetime.utcfromtimestamp(os.path.getmtime(secret_file)).isoformat() + 'Z'
                    if secret_file.exists() else datetime.utcnow().isoformat() + 'Z'
                ),
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            with open(secret_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Set secure permissions
            os.chmod(secret_file, 0o600)
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {key}: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from file storage."""
        try:
            secret_file = self._get_secret_file_path(key)
            if secret_file.exists():
                secret_file.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False
    
    def list_secrets(self) -> List[str]:
        """List all secrets in file storage."""
        try:
            secrets = []
            if self.secrets_dir.exists():
                for secret_file in self.secrets_dir.glob("*.secret"):
                    try:
                        with open(secret_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'key' in data:
                                secrets.append(data['key'])
                    except Exception:
                        # Skip corrupted files
                        continue
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if file provider is available."""
        try:
            return self.secrets_dir.exists() and os.access(self.secrets_dir, os.R_OK | os.W_OK)
        except Exception:
            return False


class CompositeSecretProvider(SecretProvider):
    """Composite provider that tries multiple providers in order."""
    
    def __init__(self, providers: List[SecretProvider]):
        """
        Initialize the composite provider.
        
        Args:
            providers: List of providers in priority order
        """
        self.providers = providers
    
    def get_secret(self, key: str) -> Optional[str]:
        """Try to get secret from providers in order."""
        for provider in self.providers:
            if provider.is_available():
                try:
                    value = provider.get_secret(key)
                    if value is not None:
                        return value
                except Exception as e:
                    logger.warning(f"Provider {type(provider).__name__} failed for key {key}: {e}")
                    continue
        return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Set secret using the first available provider."""
        for provider in self.providers:
            if provider.is_available():
                try:
                    return provider.set_secret(key, value)
                except Exception as e:
                    logger.warning(f"Provider {type(provider).__name__} failed to set {key}: {e}")
                    continue
        return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete secret from all providers."""
        success = False
        for provider in self.providers:
            if provider.is_available():
                try:
                    if provider.delete_secret(key):
                        success = True
                except Exception as e:
                    logger.warning(f"Provider {type(provider).__name__} failed to delete {key}: {e}")
        return success
    
    def list_secrets(self) -> List[str]:
        """List secrets from all providers."""
        all_secrets = set()
        for provider in self.providers:
            if provider.is_available():
                try:
                    secrets = provider.list_secrets()
                    all_secrets.update(secrets)
                except Exception as e:
                    logger.warning(f"Provider {type(provider).__name__} failed to list secrets: {e}")
        return list(all_secrets)
    
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return any(provider.is_available() for provider in self.providers)


class DockerSecretsProvider(SecretProvider):
    """Docker secrets provider for containerized environments."""
    
    def __init__(self, secrets_path: str = "/run/secrets"):
        """
        Initialize the Docker secrets provider.
        
        Args:
            secrets_path: Path to Docker secrets directory
        """
        self.secrets_path = Path(secrets_path)
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from Docker secrets."""
        try:
            secret_file = self.secrets_path / key.lower()
            if secret_file.exists():
                with open(secret_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            logger.error(f"Failed to read Docker secret {key}: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Docker secrets are read-only."""
        logger.warning("Docker secrets are read-only, cannot set secret")
        return False
    
    def delete_secret(self, key: str) -> bool:
        """Docker secrets are read-only."""
        logger.warning("Docker secrets are read-only, cannot delete secret")
        return False
    
    def list_secrets(self) -> List[str]:
        """List all Docker secrets."""
        try:
            if self.secrets_path.exists():
                return [f.name for f in self.secrets_path.iterdir() if f.is_file()]
            return []
        except Exception as e:
            logger.error(f"Failed to list Docker secrets: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if Docker secrets are available."""
        return self.secrets_path.exists() and self.secrets_path.is_dir()
