"""
Encryption provider implementations for the Device Simulator.

This module contains concrete implementations of encryption providers with
key rotation support.
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from .interfaces import EncryptionProvider
from ..database import execute_query, execute_insert

logger = logging.getLogger(__name__)


class FernetEncryptionProvider(EncryptionProvider):
    """Fernet-based encryption provider with key rotation support."""
    
    def __init__(self, key_storage_path: str = None):
        """
        Initialize the Fernet encryption provider.
        
        Args:
            key_storage_path: Directory to store encryption keys
        """
        if key_storage_path is None:
            key_storage_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'keys')
        
        self.key_storage_path = Path(key_storage_path)
        self._keys_cache = {}
        self._current_key_version = None
        self._ensure_key_storage_directory()
        self._initialize_keys()
    
    def _ensure_key_storage_directory(self):
        """Ensure the key storage directory exists with proper permissions."""
        try:
            self.key_storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self.key_storage_path, 0o700)
        except Exception as e:
            logger.error(f"Failed to create key storage directory: {e}")
            raise RuntimeError("Cannot initialize encryption provider")
    
    def _initialize_keys(self):
        """Initialize encryption keys from environment or storage."""
        try:
            # Try to load from environment first (production)
            env_key = os.environ.get('ENCRYPTION_KEY')
            env_key_version = os.environ.get('ENCRYPTION_KEY_VERSION', '1')
            
            if env_key:
                logger.info("Loading encryption key from environment variable")
                self._load_key_from_environment(env_key, env_key_version)
            else:
                logger.info("Loading encryption keys from secure storage")
                self._load_keys_from_storage()
            
            # Ensure we have at least one key
            if not self._keys_cache:
                logger.warning("No encryption keys found, generating new master key")
                self._generate_new_master_key()
                
        except Exception as e:
            logger.error(f"Failed to initialize encryption keys: {e}")
            raise RuntimeError("Critical security error: Unable to initialize encryption system")
    
    def _load_key_from_environment(self, key_data: str, version: str):
        """Load encryption key from environment variable."""
        try:
            # Validate key format (should be base64 Fernet key)
            key_bytes = base64.urlsafe_b64decode(key_data.encode())
            if len(key_bytes) != 32:
                raise ValueError("Invalid key length")
            
            # Store in cache
            self._keys_cache[version] = key_data.encode()
            self._current_key_version = version
            
            # Store metadata in database
            self._store_key_metadata(version, 'environment', datetime.utcnow())
            
        except Exception as e:
            logger.error("Failed to load key from environment")
            raise ValueError(f"Invalid encryption key in environment: {e}")
    
    def _load_keys_from_storage(self):
        """Load all encryption keys from secure storage."""
        try:
            # Load key metadata from database
            key_metadata = self._get_key_metadata()
            
            for metadata in key_metadata:
                version = metadata['version']
                if metadata['source'] == 'file':
                    key_file = self.key_storage_path / f"key_v{version}.key"
                    if key_file.exists():
                        with open(key_file, 'rb') as f:
                            self._keys_cache[version] = f.read()
                        
                        # Set current version to the latest active key
                        if metadata['is_active'] and (
                            not self._current_key_version or 
                            int(version) > int(self._current_key_version)
                        ):
                            self._current_key_version = version
            
        except Exception as e:
            logger.error(f"Failed to load keys from storage: {e}")
    
    def _generate_new_master_key(self) -> str:
        """Generate a new master encryption key."""
        try:
            # Generate new Fernet key
            key = Fernet.generate_key()
            version = str(int(self._current_key_version or 0) + 1)
            
            # Store key securely
            key_file = self.key_storage_path / f"key_v{version}.key"
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set secure permissions (owner read/write only)
            os.chmod(key_file, 0o600)
            
            # Cache the key
            self._keys_cache[version] = key
            self._current_key_version = version
            
            # Store metadata
            self._store_key_metadata(version, 'file', datetime.utcnow(), is_active=True)
            
            logger.info(f"Generated new master encryption key version {version}")
            return version
            
        except Exception as e:
            logger.error(f"Failed to generate new master key: {e}")
            raise RuntimeError("Failed to generate encryption key")
    
    def _store_key_metadata(self, version: str, source: str, created_at: datetime, is_active: bool = True):
        """Store key metadata in database."""
        try:
            # Create encryption_keys table if it doesn't exist
            execute_insert('''
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    version TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    rotated_at TIMESTAMP NULL,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # Insert or update key metadata
            execute_insert('''
                INSERT OR REPLACE INTO encryption_keys 
                (version, source, created_at, is_active, usage_count)
                VALUES (?, ?, ?, ?, 0)
            ''', [version, source, created_at, is_active])
            
        except Exception as e:
            logger.error(f"Failed to store key metadata: {e}")
    
    def _get_key_metadata(self) -> List[Dict]:
        """Get all key metadata from database."""
        try:
            rows = execute_query('''
                SELECT version, source, created_at, is_active, rotated_at, usage_count
                FROM encryption_keys 
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in rows] if rows else []
        except Exception:
            return []
    
    def encrypt(self, data: str, key_version: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt sensitive data with specified or current key version."""
        if not data:
            return None
        
        try:
            # Use specified version or current version
            version = key_version or self._current_key_version
            if version not in self._keys_cache:
                raise ValueError(f"Encryption key version {version} not available")
            
            # Create cipher and encrypt
            cipher = Fernet(self._keys_cache[version])
            encrypted_bytes = cipher.encrypt(data.encode('utf-8'))
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            # Update usage count
            self._increment_key_usage(version)
            
            # Return encrypted data with metadata
            return {
                'data': encrypted_b64,
                'version': version,
                'algorithm': 'fernet',
                'encrypted_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Encryption failed (sensitive data not logged)")
            raise RuntimeError("Failed to encrypt sensitive data")
    
    def decrypt(self, encrypted_payload: Dict[str, Any]) -> str:
        """Decrypt sensitive data using the appropriate key version."""
        if not encrypted_payload or 'data' not in encrypted_payload:
            return None
        
        try:
            version = encrypted_payload.get('version', '1')
            encrypted_data = encrypted_payload['data']
            
            # Get the appropriate key
            if version not in self._keys_cache:
                logger.error(f"Decryption key version {version} not available")
                raise ValueError(f"Key version {version} not available")
            
            # Decrypt data
            cipher = Fernet(self._keys_cache[version])
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            
            return decrypted_bytes.decode('utf-8')
            
        except InvalidToken:
            logger.error("Invalid token during decryption")
            raise ValueError("Invalid or corrupted encrypted data")
        except Exception as e:
            logger.error("Decryption failed (sensitive data not logged)")
            raise RuntimeError("Failed to decrypt sensitive data")
    
    def rotate_keys(self, force: bool = False) -> str:
        """Rotate encryption keys - generate new key and mark old ones for migration."""
        try:
            # Check if rotation is needed
            if not force and not self._should_rotate_key():
                logger.info("Key rotation not needed at this time")
                return self._current_key_version
            
            # Generate new key
            new_version = self._generate_new_master_key()
            
            # Mark old keys as rotated but keep them for backward compatibility
            if self._current_key_version and self._current_key_version != new_version:
                execute_insert('''
                    UPDATE encryption_keys 
                    SET is_active = FALSE, rotated_at = ? 
                    WHERE version = ?
                ''', [datetime.utcnow(), self._current_key_version])
            
            logger.info(f"Key rotation completed. New version: {new_version}")
            return new_version
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise RuntimeError("Failed to rotate encryption keys")
    
    def _should_rotate_key(self) -> bool:
        """Determine if key rotation is needed based on age and usage."""
        try:
            if not self._current_key_version:
                return True
            
            metadata = execute_query('''
                SELECT created_at, usage_count FROM encryption_keys 
                WHERE version = ? AND is_active = TRUE
            ''', [self._current_key_version])
            
            if not metadata:
                return True
            
            created_at = datetime.fromisoformat(metadata[0]['created_at'])
            usage_count = metadata[0]['usage_count']
            
            # Rotate if key is older than 90 days or has been used more than 10000 times
            age_threshold = datetime.utcnow() - timedelta(days=90)
            usage_threshold = 10000
            
            return created_at < age_threshold or usage_count > usage_threshold
            
        except Exception:
            return True  # Err on the side of caution
    
    def _increment_key_usage(self, version: str):
        """Increment usage count for a key version."""
        try:
            execute_insert('''
                UPDATE encryption_keys 
                SET usage_count = usage_count + 1 
                WHERE version = ?
            ''', [version])
        except Exception:
            pass  # Non-critical operation
    
    def get_key_status(self) -> Dict[str, Any]:
        """Get current key status and rotation information."""
        try:
            metadata = self._get_key_metadata()
            current_key = next((k for k in metadata if k['version'] == self._current_key_version), None)
            
            return {
                'current_version': self._current_key_version,
                'total_keys': len(metadata),
                'active_keys': len([k for k in metadata if k['is_active']]),
                'current_key_age_days': (
                    (datetime.utcnow() - datetime.fromisoformat(current_key['created_at'])).days
                    if current_key else None
                ),
                'rotation_needed': self._should_rotate_key(),
                'keys': [
                    {
                        'version': k['version'],
                        'source': k['source'],
                        'created_at': k['created_at'],
                        'is_active': k['is_active'],
                        'usage_count': k['usage_count']
                    }
                    for k in metadata
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get key status: {e}")
            return {'error': 'Unable to retrieve key status'}
