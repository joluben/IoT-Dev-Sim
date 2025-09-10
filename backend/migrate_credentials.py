#!/usr/bin/env python3
"""
Credential Migration Script for Device Simulator Security Upgrade

This script migrates existing encrypted credentials from the legacy EncryptionManager
to the new SecretManager system with key rotation support.

Usage:
    python migrate_credentials.py [--dry-run] [--force]
    
Options:
    --dry-run    Show what would be migrated without making changes
    --force      Force migration even if new format is detected
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import execute_query, execute_insert, init_db
from app.security import get_secret_manager, encrypt_credential, decrypt_credential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CredentialMigrator:
    """Handles migration of credentials from legacy to new encryption system"""
    
    def __init__(self, dry_run=False, force=False):
        self.dry_run = dry_run
        self.force = force
        self.secret_manager = get_secret_manager()
        self.legacy_cipher = None
        self._init_legacy_cipher()
        
        # Migration statistics
        self.stats = {
            'connections_processed': 0,
            'connections_migrated': 0,
            'connections_skipped': 0,
            'connections_failed': 0,
            'credentials_migrated': 0,
            'errors': []
        }
    
    def _init_legacy_cipher(self):
        """Initialize legacy encryption cipher for backward compatibility"""
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Try to load legacy key
            key_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'encryption.key')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    legacy_key = f.read()
                self.legacy_cipher = Fernet(legacy_key)
                logger.info("Legacy encryption key loaded successfully")
            else:
                logger.warning("No legacy encryption key found - will skip legacy credential migration")
                
        except Exception as e:
            logger.error(f"Failed to initialize legacy cipher: {e}")
            self.legacy_cipher = None
    
    def migrate_all_credentials(self):
        """Migrate all credentials in the system"""
        logger.info("Starting credential migration process...")
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        # Initialize database
        init_db()
        
        # Migrate connection credentials
        self._migrate_connection_credentials()
        
        # Print migration summary
        self._print_migration_summary()
        
        return self.stats
    
    def _migrate_connection_credentials(self):
        """Migrate connection authentication credentials"""
        logger.info("Migrating connection credentials...")
        
        try:
            # Get all connections with auth_config
            connections = execute_query('''
                SELECT id, name, auth_config 
                FROM connections 
                WHERE auth_config IS NOT NULL AND auth_config != ''
            ''')
            
            if not connections:
                logger.info("No connections with credentials found")
                return
            
            logger.info(f"Found {len(connections)} connections with credentials")
            
            for conn in connections:
                self._migrate_single_connection(conn)
                
        except Exception as e:
            error_msg = f"Failed to migrate connection credentials: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
    
    def _migrate_single_connection(self, connection):
        """Migrate credentials for a single connection"""
        conn_id = connection['id']
        conn_name = connection['name']
        
        try:
            self.stats['connections_processed'] += 1
            
            # Parse auth_config
            auth_config = json.loads(connection['auth_config'])
            if not isinstance(auth_config, dict):
                logger.warning(f"Connection {conn_id} ({conn_name}): Invalid auth_config format")
                self.stats['connections_skipped'] += 1
                return
            
            # Check if already migrated (unless force is specified)
            if not self.force and self._is_already_migrated(auth_config):
                logger.info(f"Connection {conn_id} ({conn_name}): Already migrated, skipping")
                self.stats['connections_skipped'] += 1
                return
            
            # Migrate sensitive fields
            migrated_config = {}
            needs_migration = False
            sensitive_fields = ['password', 'token', 'key', 'secret', 'api_key', 'client_secret']
            
            for field, value in auth_config.items():
                if field in sensitive_fields and value:
                    migrated_value = self._migrate_credential_field(field, value, conn_id, conn_name)
                    if migrated_value != value:
                        needs_migration = True
                        self.stats['credentials_migrated'] += 1
                    migrated_config[field] = migrated_value
                else:
                    migrated_config[field] = value
            
            # Update database if migration is needed
            if needs_migration:
                if not self.dry_run:
                    execute_insert('''
                        UPDATE connections 
                        SET auth_config = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', [json.dumps(migrated_config), conn_id])
                
                logger.info(f"Connection {conn_id} ({conn_name}): Migrated successfully")
                self.stats['connections_migrated'] += 1
            else:
                logger.info(f"Connection {conn_id} ({conn_name}): No migration needed")
                self.stats['connections_skipped'] += 1
                
        except Exception as e:
            error_msg = f"Connection {conn_id} ({conn_name}): Migration failed - {e}"
            logger.error(error_msg)
            self.stats['connections_failed'] += 1
            self.stats['errors'].append(error_msg)
    
    def _is_already_migrated(self, auth_config):
        """Check if auth_config is already using new encryption format"""
        sensitive_fields = ['password', 'token', 'key', 'secret', 'api_key', 'client_secret']
        
        for field in sensitive_fields:
            if field in auth_config and auth_config[field]:
                value = auth_config[field]
                # Check if it's already in new format (dict with 'data' and 'version')
                if isinstance(value, dict) and 'data' in value and 'version' in value:
                    return True
        
        return False
    
    def _migrate_credential_field(self, field_name, field_value, conn_id, conn_name):
        """Migrate a single credential field"""
        try:
            # If already in new format, return as-is (unless force is specified)
            if isinstance(field_value, dict) and 'data' in field_value and 'version' in field_value:
                if not self.force:
                    return field_value
                # If force is specified, try to decrypt and re-encrypt with current key
                try:
                    decrypted = decrypt_credential(field_value)
                    return encrypt_credential(decrypted)
                except Exception:
                    logger.warning(f"Connection {conn_id}: Could not re-encrypt {field_name}, keeping original")
                    return field_value
            
            # Try to decrypt using legacy cipher
            if self.legacy_cipher and isinstance(field_value, str):
                try:
                    import base64
                    decrypted_bytes = self.legacy_cipher.decrypt(base64.b64decode(field_value.encode()))
                    decrypted_value = decrypted_bytes.decode('utf-8')
                    
                    # Re-encrypt using new system
                    new_encrypted = encrypt_credential(decrypted_value)
                    logger.debug(f"Connection {conn_id}: Migrated {field_name} from legacy format")
                    return new_encrypted
                    
                except Exception as e:
                    logger.warning(f"Connection {conn_id}: Could not decrypt legacy {field_name}: {e}")
            
            # If we can't decrypt, assume it's plain text and encrypt it
            if isinstance(field_value, str) and field_value.strip():
                logger.warning(f"Connection {conn_id}: Encrypting plain text {field_name}")
                return encrypt_credential(field_value)
            
            # Return original value if we can't process it
            return field_value
            
        except Exception as e:
            logger.error(f"Connection {conn_id}: Failed to migrate {field_name}: {e}")
            return field_value
    
    def _print_migration_summary(self):
        """Print migration summary"""
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Connections processed: {self.stats['connections_processed']}")
        logger.info(f"Connections migrated: {self.stats['connections_migrated']}")
        logger.info(f"Connections skipped: {self.stats['connections_skipped']}")
        logger.info(f"Connections failed: {self.stats['connections_failed']}")
        logger.info(f"Individual credentials migrated: {self.stats['credentials_migrated']}")
        
        if self.stats['errors']:
            logger.info(f"Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.error(f"  - {error}")
        
        if self.dry_run:
            logger.info("DRY RUN COMPLETED - No actual changes were made")
        else:
            logger.info("MIGRATION COMPLETED")
        
        logger.info("=" * 60)

def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate Device Simulator credentials to new encryption system'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force migration even if new format is detected'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create migrator and run migration
    migrator = CredentialMigrator(dry_run=args.dry_run, force=args.force)
    
    try:
        stats = migrator.migrate_all_credentials()
        
        # Exit with error code if there were failures
        if stats['connections_failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Migration failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
