#!/usr/bin/env python3
"""
DevSim Production Environment Validation Script
===============================================

This script validates that the environment is properly configured for
production deployment. It checks security settings, required variables,
and potential misconfigurations.

Usage:
    python validate_production_env.py [--fix-warnings]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any


class ProductionValidator:
    """Validates production environment configuration"""
    
    REQUIRED_PRODUCTION_VARS = [
        'SECRET_KEY',
        'ENCRYPTION_KEY',
        'JWT_SECRET_KEY',
        'CORS_ORIGINS'
    ]
    
    FORBIDDEN_PRODUCTION_VALUES = {
        'FLASK_DEBUG': ['true', '1', 'yes'],
        'ALLOW_SENSITIVE_CONNECTIONS': ['true', '1', 'yes'],
        'FLASK_ENV': ['development', 'dev']
    }
    
    RECOMMENDED_PRODUCTION_VARS = [
        'DATABASE_URL',
        'REDIS_URL',
        'SENTRY_DSN',
        'LOG_LEVEL',
        'BACKUP_ENABLED'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.recommendations = []
    
    def validate_environment_variables(self):
        """Validate required environment variables"""
        
        # Check required variables
        for var in self.REQUIRED_PRODUCTION_VARS:
            value = os.getenv(var)
            if not value:
                self.errors.append(f"Missing required variable: {var}")
            elif len(value.strip()) < 16:  # Minimum security length
                self.errors.append(f"Variable {var} is too short (minimum 16 characters)")
        
        # Check forbidden values
        for var, forbidden_values in self.FORBIDDEN_PRODUCTION_VALUES.items():
            value = os.getenv(var, '').lower()
            if value in forbidden_values:
                self.errors.append(f"Variable {var}={value} is not allowed in production")
        
        # Check recommended variables
        for var in self.RECOMMENDED_PRODUCTION_VARS:
            if not os.getenv(var):
                self.recommendations.append(f"Consider setting {var} for production")
    
    def validate_flask_configuration(self):
        """Validate Flask-specific configuration"""
        
        flask_env = os.getenv('FLASK_ENV', 'development').lower()
        if flask_env != 'production':
            self.errors.append(f"FLASK_ENV must be 'production', got '{flask_env}'")
        
        # Check debug mode
        flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()
        if flask_debug in ('true', '1', 'yes'):
            self.errors.append("FLASK_DEBUG must be 'false' in production")
        
        # Check secret key strength
        secret_key = os.getenv('SECRET_KEY', '')
        if secret_key:
            if len(secret_key) < 32:
                self.errors.append("SECRET_KEY must be at least 32 characters long")
            if secret_key in ['dev-secret-key', 'change-me', 'secret']:
                self.errors.append("SECRET_KEY appears to be a default/weak value")
    
    def validate_security_configuration(self):
        """Validate security-related configuration"""
        
        # CORS origins
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if not cors_origins:
            self.errors.append("CORS_ORIGINS must be set in production")
        elif cors_origins == '*':
            self.errors.append("CORS_ORIGINS cannot be '*' in production")
        elif 'localhost' in cors_origins.lower():
            self.warnings.append("CORS_ORIGINS contains localhost - ensure this is intentional")
        
        # Sensitive connections
        allow_sensitive = os.getenv('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower()
        if allow_sensitive in ('true', '1', 'yes'):
            self.errors.append("ALLOW_SENSITIVE_CONNECTIONS must be 'false' in production")
        
        # HTTPS enforcement
        force_https = os.getenv('FORCE_HTTPS', 'false').lower()
        if force_https not in ('true', '1', 'yes'):
            self.warnings.append("FORCE_HTTPS should be 'true' in production")
    
    def validate_database_configuration(self):
        """Validate database configuration"""
        
        database_url = os.getenv('DATABASE_URL', '')
        
        if not database_url:
            self.warnings.append("DATABASE_URL not set - will use default SQLite")
        elif database_url.startswith('sqlite://'):
            self.warnings.append("Using SQLite in production - consider PostgreSQL for better performance")
        elif 'localhost' in database_url:
            self.warnings.append("Database URL contains localhost - ensure this is correct for production")
        
        # Check database credentials
        if 'password' in database_url.lower() and ('password' in database_url or 'pass123' in database_url):
            self.errors.append("Database URL contains weak/default password")
    
    def validate_file_structure(self):
        """Validate file structure and permissions"""
        
        # Check for compromised files
        if Path('.env').exists():
            self.errors.append("Compromised .env file still exists - should be removed")
        
        # Check secrets directory
        secrets_dir = Path('secrets')
        if not secrets_dir.exists():
            self.errors.append("Secrets directory does not exist")
        else:
            required_secrets = [
                'secret_key.txt',
                'encryption_key.txt',
                'jwt_secret_key.txt'
            ]
            
            for secret_file in required_secrets:
                secret_path = secrets_dir / secret_file
                if not secret_path.exists():
                    self.errors.append(f"Missing secret file: {secret_file}")
                elif secret_path.stat().st_size == 0:
                    self.errors.append(f"Secret file is empty: {secret_file}")
        
        # Check production template
        if not Path('.env.production').exists():
            self.warnings.append("Production environment template (.env.production) not found")
    
    def validate_docker_configuration(self):
        """Validate Docker configuration for production"""
        
        # Check for production docker-compose
        if not Path('docker-compose.prod.yml').exists():
            self.recommendations.append("Create docker-compose.prod.yml for production deployment")
        
        # Check Dockerfile
        dockerfile_prod = Path('backend/Dockerfile.prod')
        if not dockerfile_prod.exists():
            self.recommendations.append("Create backend/Dockerfile.prod for production builds")
    
    def check_development_artifacts(self):
        """Check for development artifacts that shouldn't be in production"""
        
        development_files = [
            '.env.development',
            'debug.log',
            'test.db',
            'dev.sqlite'
        ]
        
        for dev_file in development_files:
            if Path(dev_file).exists():
                self.warnings.append(f"Development file found: {dev_file}")
        
        # Check for debug prints in code
        python_files = list(Path('backend').rglob('*.py'))
        debug_patterns = ['print(', 'pdb.', 'breakpoint(', 'import pdb']
        
        files_with_debug = []
        for py_file in python_files:
            try:
                content = py_file.read_text()
                for pattern in debug_patterns:
                    if pattern in content:
                        files_with_debug.append(str(py_file))
                        break
            except:
                continue
        
        if files_with_debug:
            self.warnings.append(f"Files with debug code: {', '.join(files_with_debug[:3])}{'...' if len(files_with_debug) > 3 else ''}")
    
    def run_validation(self) -> Dict[str, Any]:
        """Run all validation checks"""
        
        print("🔍 DevSim Production Environment Validation")
        print("=" * 50)
        print()
        
        # Run all validation checks
        self.validate_environment_variables()
        self.validate_flask_configuration()
        self.validate_security_configuration()
        self.validate_database_configuration()
        self.validate_file_structure()
        self.validate_docker_configuration()
        self.check_development_artifacts()
        
        # Display results
        if self.errors:
            print("❌ ERRORS (Must be fixed before production):")
            for error in self.errors:
                print(f"   • {error}")
            print()
        
        if self.warnings:
            print("⚠️  WARNINGS (Should be addressed):")
            for warning in self.warnings:
                print(f"   • {warning}")
            print()
        
        if self.recommendations:
            print("💡 RECOMMENDATIONS (Consider implementing):")
            for rec in self.recommendations:
                print(f"   • {rec}")
            print()
        
        # Summary
        total_issues = len(self.errors) + len(self.warnings)
        
        if self.errors:
            print(f"❌ VALIDATION FAILED: {len(self.errors)} errors must be fixed")
            return {
                'valid': False,
                'errors': self.errors,
                'warnings': self.warnings,
                'recommendations': self.recommendations
            }
        elif self.warnings:
            print(f"⚠️  VALIDATION PASSED WITH WARNINGS: {len(self.warnings)} warnings")
            return {
                'valid': True,
                'errors': self.errors,
                'warnings': self.warnings,
                'recommendations': self.recommendations
            }
        else:
            print("✅ VALIDATION PASSED: Environment ready for production")
            return {
                'valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': self.recommendations
            }
    
    def generate_fix_script(self) -> str:
        """Generate a script to fix common issues"""
        
        fixes = []
        
        # Fix environment variables
        if any('FLASK_ENV' in error for error in self.errors):
            fixes.append("export FLASK_ENV=production")
        
        if any('FLASK_DEBUG' in error for error in self.errors):
            fixes.append("export FLASK_DEBUG=false")
        
        if any('ALLOW_SENSITIVE_CONNECTIONS' in error for error in self.errors):
            fixes.append("export ALLOW_SENSITIVE_CONNECTIONS=false")
        
        # Generate missing secrets
        if any('SECRET_KEY' in error for error in self.errors):
            fixes.append("# Generate new SECRET_KEY")
            fixes.append("python backend/scripts/rotate_credentials.py")
        
        if fixes:
            script = "#!/bin/bash\n"
            script += "# Auto-generated fix script for DevSim production environment\n\n"
            script += "\n".join(fixes)
            return script
        
        return ""


def main():
    parser = argparse.ArgumentParser(description="Validate DevSim production environment")
    parser.add_argument("--fix-script", action="store_true",
                       help="Generate a script to fix common issues")
    
    args = parser.parse_args()
    
    validator = ProductionValidator()
    results = validator.run_validation()
    
    # Generate fix script if requested
    if args.fix_script:
        fix_script = validator.generate_fix_script()
        if fix_script:
            with open('fix_production_env.sh', 'w') as f:
                f.write(fix_script)
            print(f"📝 Fix script generated: fix_production_env.sh")
        else:
            print("📝 No automatic fixes available")
    
    # Exit with appropriate code
    sys.exit(0 if results['valid'] else 1)


if __name__ == "__main__":
    main()