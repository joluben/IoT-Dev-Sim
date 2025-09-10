"""
Security package for Device Simulator.

This package provides secret management, encryption, and security validation
functionality for the Device Simulator application.
"""

from .secret_manager import get_secret_manager, SecretManager, DevSimEnvironmentValidator

def encrypt_credential(data):
    """Encrypt credential data using the global secret manager."""
    secret_manager = get_secret_manager()
    return secret_manager.encrypt_credential(data)

def decrypt_credential(encrypted_payload):
    """Decrypt credential data using the global secret manager."""
    secret_manager = get_secret_manager()
    return secret_manager.decrypt_credential(encrypted_payload)

__all__ = ['get_secret_manager', 'SecretManager', 'DevSimEnvironmentValidator', 'encrypt_credential', 'decrypt_credential']
