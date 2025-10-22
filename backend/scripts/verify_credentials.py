#!/usr/bin/env python3
"""
DevSim Credential Verification Script
=====================================

This script verifies that credential rotation was successful and that
all new credentials are properly formatted and secure.

Usage:
    python verify_credentials.py [--secrets-dir secrets]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import base64


class CredentialVerifier:
    """Verifies rotated credentials are secure and properly formatted"""
    
    def __init__(self, secrets_dir="secrets"):
        self.secrets_dir = Path(secrets_dir)
        self.required_files = [
            'secret_key.txt',
            'encryption_key.txt', 
            'jwt_secret_key.txt',
            'db_password.txt',
            'keycloak_client_secret.txt',
            'keycloak_admin_password.txt'
        ]
        
    def verify_file_exists(self, filename):
        """Verify a credential file exists"""
        file_path = self.secrets_dir / filename
        if not file_path.exists():
            return False, f"File {filename} does not exist"
        
        if file_path.stat().st_size == 0:
            return False, f"File {filename} is empty"
            
        return True, "OK"
    
    def verify_secret_key(self):
        """Verify Flask SECRET_KEY"""
        file_path = self.secrets_dir / 'secret_key.txt'
        if not file_path.exists():
            return False, "secret_key.txt not found"
            
        secret_key = file_path.read_text().strip()
        
        # Check minimum length
        if len(secret_key) < 32:
            return False, f"SECRET_KEY too short: {len(secret_key)} chars (minimum 32)"
        
        # Check it's URL-safe base64
        try:
            import secrets
            # Should be URL-safe characters
            if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in secret_key):
                return False, "SECRET_KEY contains invalid characters"
        except:
            return False, "SECRET_KEY validation failed"
            
        return True, f"OK ({len(secret_key)} chars)"
    
    def verify_encryption_key(self):
        """Verify Fernet encryption key"""
        file_path = self.secrets_dir / 'encryption_key.txt'
        if not file_path.exists():
            return False, "encryption_key.txt not found"
            
        encryption_key = file_path.read_text().strip()
        
        # Fernet keys are 44 characters (32 bytes base64 encoded)
        if len(encryption_key) != 44:
            return False, f"ENCRYPTION_KEY wrong length: {len(encryption_key)} chars (expected 44)"
        
        # Verify it's valid base64
        try:
            decoded = base64.urlsafe_b64decode(encryption_key + '==')  # Add padding
            if len(decoded) != 32:
                return False, f"ENCRYPTION_KEY decodes to wrong length: {len(decoded)} bytes (expected 32)"
        except Exception as e:
            return False, f"ENCRYPTION_KEY invalid base64: {e}"
        
        # Test with Fernet
        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(encryption_key.encode())
            # Test encryption/decryption
            test_data = b"test_encryption"
            encrypted = fernet.encrypt(test_data)
            decrypted = fernet.decrypt(encrypted)
            if decrypted != test_data:
                return False, "ENCRYPTION_KEY failed encryption test"
        except Exception as e:
            return False, f"ENCRYPTION_KEY Fernet test failed: {e}"
            
        return True, "OK (Fernet compatible)"
    
    def verify_jwt_secret(self):
        """Verify JWT secret key"""
        file_path = self.secrets_dir / 'jwt_secret_key.txt'
        if not file_path.exists():
            return False, "jwt_secret_key.txt not found"
            
        jwt_secret = file_path.read_text().strip()
        
        # Check minimum length
        if len(jwt_secret) < 32:
            return False, f"JWT_SECRET_KEY too short: {len(jwt_secret)} chars (minimum 32)"
            
        return True, f"OK ({len(jwt_secret)} chars)"
    
    def verify_db_password(self):
        """Verify database password"""
        file_path = self.secrets_dir / 'db_password.txt'
        if not file_path.exists():
            return False, "db_password.txt not found"
            
        db_password = file_path.read_text().strip()
        
        # Check minimum length
        if len(db_password) < 16:
            return False, f"DB_PASSWORD too short: {len(db_password)} chars (minimum 16)"
        
        # Check complexity (should have uppercase, lowercase, digits)
        has_upper = any(c.isupper() for c in db_password)
        has_lower = any(c.islower() for c in db_password)
        has_digit = any(c.isdigit() for c in db_password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "DB_PASSWORD lacks complexity (needs upper, lower, digit)"
            
        return True, f"OK ({len(db_password)} chars, complex)"
    
    def verify_keycloak_client_secret(self):
        """Verify Keycloak client secret"""
        file_path = self.secrets_dir / 'keycloak_client_secret.txt'
        if not file_path.exists():
            return False, "keycloak_client_secret.txt not found"
            
        client_secret = file_path.read_text().strip()
        
        # Should be UUID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, client_secret):
            return False, "KEYCLOAK_CLIENT_SECRET not in UUID format"
            
        return True, "OK (UUID format)"
    
    def verify_keycloak_admin_password(self):
        """Verify Keycloak admin password"""
        file_path = self.secrets_dir / 'keycloak_admin_password.txt'
        if not file_path.exists():
            return False, "keycloak_admin_password.txt not found"
            
        admin_password = file_path.read_text().strip()
        
        # Check minimum length
        if len(admin_password) < 12:
            return False, f"KEYCLOAK_ADMIN_PASSWORD too short: {len(admin_password)} chars (minimum 12)"
        
        # Check complexity
        has_upper = any(c.isupper() for c in admin_password)
        has_lower = any(c.islower() for c in admin_password)
        has_digit = any(c.isdigit() for c in admin_password)
        has_symbol = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in admin_password)
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_symbol])
        if complexity_score < 3:
            return False, f"KEYCLOAK_ADMIN_PASSWORD lacks complexity (score: {complexity_score}/4)"
            
        return True, f"OK ({len(admin_password)} chars, complexity: {complexity_score}/4)"
    
    def verify_rotation_metadata(self):
        """Verify rotation metadata"""
        metadata_path = self.secrets_dir / 'rotation_metadata.json'
        if not metadata_path.exists():
            return False, "rotation_metadata.json not found"
        
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            required_fields = ['rotation_date', 'rotation_reason', 'credentials_rotated', 'version']
            for field in required_fields:
                if field not in metadata:
                    return False, f"Missing field in metadata: {field}"
            
            # Check rotation date is recent (within last hour)
            rotation_date = datetime.fromisoformat(metadata['rotation_date'])
            age_minutes = (datetime.now() - rotation_date).total_seconds() / 60
            
            if age_minutes > 60:
                return False, f"Rotation too old: {age_minutes:.1f} minutes ago"
            
            # Check version incremented
            if metadata['version'] != 2:
                return False, f"Version not incremented: {metadata['version']} (expected 2)"
                
            return True, f"OK (rotated {age_minutes:.1f} minutes ago, version {metadata['version']})"
            
        except Exception as e:
            return False, f"Metadata validation failed: {e}"
    
    def verify_old_env_removed(self):
        """Verify old .env file was removed"""
        env_path = Path('.env')
        if env_path.exists():
            return False, ".env file still exists (should be removed)"
        
        # Check for backup
        backup_files = list(Path('.').glob('.env.compromised.backup.*'))
        if not backup_files:
            return False, "No .env backup found (should exist)"
            
        return True, f"OK (.env removed, backup: {backup_files[0].name})"
    
    def verify_production_template(self):
        """Verify production environment template was created"""
        template_path = Path('.env.production')
        if not template_path.exists():
            return False, ".env.production template not found"
        
        content = template_path.read_text()
        
        # Check it doesn't contain actual secrets
        if 'i1bI_4CgAV_R6Swkuci8LMHTXNB73HlSV8Z4tmwjda0=' in content:
            return False, ".env.production contains old compromised secrets"
        
        if 'PSx6XhCVVHwVxYGXBhRbJLOdPRuxNx6j' in content:
            return False, ".env.production contains old Keycloak secret"
            
        return True, "OK (template created, no secrets)"
    
    def run_verification(self):
        """Run all verification checks"""
        print("🔍 DevSim Credential Verification")
        print("=================================")
        print()
        
        checks = [
            ("File existence", self.verify_file_existence),
            ("Flask SECRET_KEY", self.verify_secret_key),
            ("Fernet ENCRYPTION_KEY", self.verify_encryption_key),
            ("JWT Secret", self.verify_jwt_secret),
            ("Database Password", self.verify_db_password),
            ("Keycloak Client Secret", self.verify_keycloak_client_secret),
            ("Keycloak Admin Password", self.verify_keycloak_admin_password),
            ("Rotation Metadata", self.verify_rotation_metadata),
            ("Old .env Removed", self.verify_old_env_removed),
            ("Production Template", self.verify_production_template)
        ]
        
        results = []
        for check_name, check_func in checks:
            try:
                success, message = check_func()
                status = "✅" if success else "❌"
                print(f"{status} {check_name}: {message}")
                results.append((check_name, success, message))
            except Exception as e:
                print(f"❌ {check_name}: ERROR - {e}")
                results.append((check_name, False, f"ERROR - {e}"))
        
        print()
        
        # Summary
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        if passed == total:
            print(f"🎉 All checks passed! ({passed}/{total})")
            print("✅ Credential rotation verification successful")
            return True
        else:
            print(f"⚠️  {total - passed} checks failed ({passed}/{total} passed)")
            print("❌ Credential rotation verification failed")
            return False
    
    def verify_file_existence(self):
        """Verify all required files exist"""
        missing_files = []
        for filename in self.required_files:
            success, message = self.verify_file_exists(filename)
            if not success:
                missing_files.append(filename)
        
        if missing_files:
            return False, f"Missing files: {', '.join(missing_files)}"
        
        return True, f"All {len(self.required_files)} files present"


def main():
    parser = argparse.ArgumentParser(description="Verify DevSim credential rotation")
    parser.add_argument("--secrets-dir", default="secrets",
                       help="Directory containing rotated credentials (default: secrets)")
    
    args = parser.parse_args()
    
    verifier = CredentialVerifier(args.secrets_dir)
    success = verifier.run_verification()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()