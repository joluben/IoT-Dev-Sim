#!/usr/bin/env python3
"""
DevSim Credential Rotation Script
=================================

This script generates new secure credentials to replace compromised ones.
It creates cryptographically secure keys for:
- Flask SECRET_KEY
- Fernet ENCRYPTION_KEY
- JWT_SECRET_KEY
- Database passwords
- Keycloak client secrets

Usage:
    python rotate_credentials.py [--output-dir secrets] [--backup]

Security Note:
    This script should be run in a secure environment and the generated
    credentials should be stored securely (Docker secrets, vault, etc.)
"""

import os
import sys
import secrets
import argparse
import json
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet


class CredentialRotator:
    """Handles secure credential generation and rotation"""
    
    def __init__(self, output_dir="secrets", backup_existing=True):
        self.output_dir = Path(output_dir)
        self.backup_existing = backup_existing
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_secret_key(self, length=32):
        """Generate Flask SECRET_KEY"""
        return secrets.token_urlsafe(length)
    
    def generate_encryption_key(self):
        """Generate Fernet encryption key"""
        return Fernet.generate_key().decode()
    
    def generate_jwt_secret(self, length=32):
        """Generate JWT secret"""
        return secrets.token_urlsafe(length)
    
    def generate_password(self, length=24, include_symbols=True):
        """Generate secure password"""
        import string
        
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_symbols else ""
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits)
        ]
        
        if include_symbols:
            password.append(secrets.choice(symbols))
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - len(password)):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def generate_keycloak_client_secret(self):
        """Generate Keycloak client secret (UUID format)"""
        import uuid
        return str(uuid.uuid4())
    
    def backup_existing_credentials(self):
        """Backup existing credential files"""
        if not self.backup_existing:
            return
            
        backup_dir = self.output_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        
        # Backup existing files
        for file_path in self.output_dir.glob("*.txt"):
            if file_path.is_file():
                backup_path = backup_dir / file_path.name
                backup_path.write_text(file_path.read_text())
                print(f"✓ Backed up {file_path.name} to {backup_path}")
    
    def rotate_all_credentials(self):
        """Generate and save all new credentials"""
        print("🔄 Starting credential rotation...")
        
        # Backup existing credentials
        self.backup_existing_credentials()
        
        # Generate new credentials
        credentials = {
            'SECRET_KEY': self.generate_secret_key(),
            'ENCRYPTION_KEY': self.generate_encryption_key(),
            'JWT_SECRET_KEY': self.generate_jwt_secret(),
            'DB_PASSWORD': self.generate_password(32, include_symbols=False),  # DB-safe password
            'KEYCLOAK_CLIENT_SECRET': self.generate_keycloak_client_secret(),
            'KEYCLOAK_ADMIN_PASSWORD': self.generate_password(24)
        }
        
        # Save credentials to individual files (Docker secrets format)
        for key, value in credentials.items():
            file_path = self.output_dir / f"{key.lower()}.txt"
            file_path.write_text(value)
            # Set restrictive permissions (Unix-like systems)
            if hasattr(os, 'chmod'):
                os.chmod(file_path, 0o600)
            print(f"✓ Generated {key} -> {file_path}")
        
        # Create metadata file
        metadata = {
            'rotation_date': datetime.now().isoformat(),
            'rotation_reason': 'Security incident - compromised credentials in .env file',
            'credentials_rotated': list(credentials.keys()),
            'next_rotation_due': (datetime.now() + 
                                 __import__('datetime').timedelta(days=90)).isoformat(),
            'version': 2  # Increment from current version 1
        }
        
        metadata_path = self.output_dir / "rotation_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Created rotation metadata -> {metadata_path}")
        
        # Create production environment template
        self.create_production_env_template(credentials)
        
        return credentials
    
    def create_production_env_template(self, credentials):
        """Create production environment template without actual secrets"""
        template_content = f"""# =============================================================================
# DevSim Production Environment Configuration
# =============================================================================
# Generated on: {datetime.now().isoformat()}
# 
# SECURITY WARNING: This template contains NO actual secrets.
# Secrets are stored in Docker secrets files in the secrets/ directory.
# 
# For production deployment:
# 1. Use Docker secrets or external secret manager
# 2. Never commit actual secrets to version control
# 3. Rotate credentials every 90 days
# =============================================================================

# =============================================================================
# FLASK CONFIGURATION
# =============================================================================
FLASK_ENV=production
FLASK_DEBUG=false

# Secrets are loaded from Docker secrets files:
# - SECRET_KEY from /run/secrets/secret_key
# - ENCRYPTION_KEY from /run/secrets/encryption_key  
# - JWT_SECRET_KEY from /run/secrets/jwt_secret_key

ENCRYPTION_KEY_VERSION=2

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
ALLOW_SENSITIVE_CONNECTIONS=false
FORCE_HTTPS=true
HSTS_MAX_AGE=31536000

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# Production database (PostgreSQL recommended)
DATABASE_URL=postgresql://devsim_user:{{DB_PASSWORD}}@postgres:5432/devsim_prod
# DB password loaded from /run/secrets/db_password

# Connection pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# =============================================================================
# AUTHENTICATION CONFIGURATION
# =============================================================================
AUTHENTICATION_ENABLED=true

# Keycloak Configuration
KEYCLOAK_ENABLED=true
KEYCLOAK_SERVER_URL=https://keycloak.yourdomain.com
KEYCLOAK_REALM=devsim-prod
KEYCLOAK_CLIENT_ID=devsim-app
# KEYCLOAK_CLIENT_SECRET loaded from /run/secrets/keycloak_client_secret
KEYCLOAK_ADMIN_USERNAME=admin
# KEYCLOAK_ADMIN_PASSWORD loaded from /run/secrets/keycloak_admin_password

# =============================================================================
# CORS & SECURITY HEADERS
# =============================================================================
CORS_ORIGINS=https://devsim.yourdomain.com,https://www.devsim.yourdomain.com

# =============================================================================
# UPLOAD & LIMITS
# =============================================================================
MAX_CONTENT_LENGTH=10485760
UPLOAD_FOLDER=/app/uploads

# =============================================================================
# MONITORING & LOGGING
# =============================================================================
LOG_LEVEL=INFO
LOG_FILE=/app/logs/devsim.log
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS_URL=redis://redis:6379/0

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=devsim-backups

# =============================================================================
# DOCKER SECRETS CONFIGURATION
# =============================================================================
USE_DOCKER_SECRETS=true
"""
        
        template_path = Path(".env.production")
        template_path.write_text(template_content)
        print(f"✓ Created production environment template -> {template_path}")
    
    def remove_compromised_env_file(self):
        """Remove the compromised .env file from filesystem and git history"""
        env_file = Path(".env")
        
        if env_file.exists():
            # Create backup first
            backup_path = Path(f".env.compromised.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_path.write_text(env_file.read_text())
            print(f"✓ Backed up compromised .env to {backup_path}")
            
            # Remove from filesystem
            env_file.unlink()
            print("✓ Removed compromised .env file from filesystem")
        
        # Instructions for git history cleanup
        print("\n⚠️  IMPORTANT: Manual git history cleanup required!")
        print("Run these commands to remove .env from git history:")
        print("  git filter-branch --force --index-filter \\")
        print("    'git rm --cached --ignore-unmatch .env' \\")
        print("    --prune-empty --tag-name-filter cat -- --all")
        print("  git push origin --force --all")
        print("  git push origin --force --tags")
        print("\nAlternatively, use BFG Repo-Cleaner for better performance:")
        print("  java -jar bfg.jar --delete-files .env")
        print("  git reflog expire --expire=now --all && git gc --prune=now --aggressive")


def main():
    parser = argparse.ArgumentParser(description="Rotate DevSim credentials")
    parser.add_argument("--output-dir", default="secrets", 
                       help="Directory to store new credentials (default: secrets)")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip backing up existing credentials")
    parser.add_argument("--remove-env", action="store_true",
                       help="Remove compromised .env file")
    
    args = parser.parse_args()
    
    try:
        rotator = CredentialRotator(
            output_dir=args.output_dir,
            backup_existing=not args.no_backup
        )
        
        # Rotate credentials
        credentials = rotator.rotate_all_credentials()
        
        # Remove compromised .env file if requested
        if args.remove_env:
            rotator.remove_compromised_env_file()
        
        print("\n🎉 Credential rotation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update Docker Compose to use the new secrets")
        print("2. Update Keycloak with new client secret")
        print("3. Update database with new password")
        print("4. Test the application with new credentials")
        print("5. Remove compromised .env from git history")
        print("6. Schedule next rotation in 90 days")
        
        print(f"\n📊 Rotation Summary:")
        print(f"   • Credentials rotated: {len(credentials)}")
        print(f"   • Output directory: {args.output_dir}")
        print(f"   • Backup created: {not args.no_backup}")
        print(f"   • Production template: .env.production")
        
    except Exception as e:
        print(f"❌ Error during credential rotation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()