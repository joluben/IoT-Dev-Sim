"""
Security interfaces for the Device Simulator secret management system.

This module defines the core interfaces for secret management, encryption,
and key rotation functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from datetime import datetime


class SecretProvider(ABC):
    """Abstract base class for secret providers."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret by key.
        
        Args:
            key: The secret identifier
            
        Returns:
            The secret value or None if not found
        """
        pass
    
    @abstractmethod
    def set_secret(self, key: str, value: str) -> bool:
        """
        Store a secret.
        
        Args:
            key: The secret identifier
            value: The secret value
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.
        
        Args:
            key: The secret identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_secrets(self) -> List[str]:
        """
        List all available secret keys.
        
        Returns:
            List of secret identifiers
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and functional.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass


class EncryptionProvider(ABC):
    """Abstract base class for encryption providers."""
    
    @abstractmethod
    def encrypt(self, data: str, key_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Encrypt data with the specified or current key version.
        
        Args:
            data: The data to encrypt
            key_version: Optional specific key version to use
            
        Returns:
            Dictionary containing encrypted data and metadata
        """
        pass
    
    @abstractmethod
    def decrypt(self, encrypted_payload: Dict[str, Any]) -> str:
        """
        Decrypt data using the appropriate key version.
        
        Args:
            encrypted_payload: Dictionary containing encrypted data and metadata
            
        Returns:
            Decrypted data
        """
        pass
    
    @abstractmethod
    def rotate_keys(self, force: bool = False) -> str:
        """
        Rotate encryption keys.
        
        Args:
            force: Force rotation even if not needed
            
        Returns:
            New key version identifier
        """
        pass
    
    @abstractmethod
    def get_key_status(self) -> Dict[str, Any]:
        """
        Get current key status and rotation information.
        
        Returns:
            Dictionary containing key status information
        """
        pass


class SecretManagerInterface(ABC):
    """Abstract base class for secret managers."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret by key.
        
        Args:
            key: The secret identifier
            
        Returns:
            The secret value or None if not found
        """
        pass
    
    @abstractmethod
    def set_secret(self, key: str, value: str, encrypt: bool = True) -> bool:
        """
        Store a secret with optional encryption.
        
        Args:
            key: The secret identifier
            value: The secret value
            encrypt: Whether to encrypt the value
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.
        
        Args:
            key: The secret identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def encrypt_credential(self, data: str) -> Dict[str, Any]:
        """
        Encrypt credential data.
        
        Args:
            data: The credential data to encrypt
            
        Returns:
            Dictionary containing encrypted data and metadata
        """
        pass
    
    @abstractmethod
    def decrypt_credential(self, encrypted_payload: Dict[str, Any]) -> str:
        """
        Decrypt credential data.
        
        Args:
            encrypted_payload: Dictionary containing encrypted data and metadata
            
        Returns:
            Decrypted credential data
        """
        pass
    
    @abstractmethod
    def rotate_keys(self, force: bool = False) -> str:
        """
        Rotate encryption keys.
        
        Args:
            force: Force rotation even if not needed
            
        Returns:
            New key version identifier
        """
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the secret management system.
        
        Returns:
            Dictionary containing health status information
        """
        pass


class EnvironmentValidator(ABC):
    """Abstract base class for environment variable validation."""
    
    @abstractmethod
    def validate_required_variables(self) -> Dict[str, Any]:
        """
        Validate that all required environment variables are present and valid.
        
        Returns:
            Dictionary containing validation results
        """
        pass
    
    @abstractmethod
    def get_missing_variables(self) -> List[str]:
        """
        Get list of missing required environment variables.
        
        Returns:
            List of missing variable names
        """
        pass
    
    @abstractmethod
    def get_invalid_variables(self) -> Dict[str, str]:
        """
        Get dictionary of invalid environment variables and their issues.
        
        Returns:
            Dictionary mapping variable names to error descriptions
        """
        pass
