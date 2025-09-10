"""
Startup validation module for the Device Simulator.

This module validates environment variables and system requirements
before the application starts to ensure proper configuration.
"""

import os
import sys
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import from the new secrets_mgmt package
try:
    from .secrets_mgmt.secret_manager import DevSimEnvironmentValidator, get_secret_manager
except ImportError:
    # Fallback for direct execution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    secrets_path = os.path.join(current_dir, 'secrets_mgmt')
    if secrets_path not in sys.path:
        sys.path.insert(0, secrets_path)
    from secret_manager import DevSimEnvironmentValidator, get_secret_manager

logger = logging.getLogger(__name__)


class StartupValidator:
    """Validates system configuration at application startup."""
    
    def __init__(self):
        self.env_validator = DevSimEnvironmentValidator()
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> Dict[str, Any]:
        """
        Perform comprehensive startup validation.
        
        Returns:
            Dictionary containing validation results
        """
        logger.info("Starting application configuration validation...")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'environment': {},
            'secret_manager': {},
            'recommendations': []
        }
        
        # Validate environment variables
        env_results = self._validate_environment()
        results['environment'] = env_results
        
        if not env_results['valid']:
            results['valid'] = False
            results['errors'].extend(env_results.get('errors', []))
        
        results['warnings'].extend(env_results.get('warnings', []))
        
        # Validate secret management system
        if results['valid']:  # Only if environment is valid
            secret_results = self._validate_secret_manager()
            results['secret_manager'] = secret_results
            
            if not secret_results['valid']:
                results['valid'] = False
                results['errors'].extend(secret_results.get('errors', []))
            
            results['warnings'].extend(secret_results.get('warnings', []))
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _validate_environment(self) -> Dict[str, Any]:
        """Validate environment variables."""
        logger.info("Validating environment variables...")
        
        env_validation = self.env_validator.validate_required_variables()
        
        results = {
            'valid': env_validation['valid'],
            'errors': [],
            'warnings': env_validation.get('warnings', [])
        }
        
        # Format missing variables as errors
        if env_validation['missing']:
            for var in env_validation['missing']:
                config = self.env_validator.REQUIRED_VARIABLES.get(var, {})
                description = config.get('description', 'Required environment variable')
                results['errors'].append(
                    f"Missing required environment variable: {var} - {description}"
                )
        
        # Format invalid variables as errors
        if env_validation['invalid']:
            for var, error in env_validation['invalid'].items():
                results['errors'].append(
                    f"Invalid environment variable: {var} - {error}"
                )
        
        # Add security warnings
        if os.environ.get('FLASK_ENV') == 'development':
            results['warnings'].append(
                "Running in development mode - ensure this is not a production deployment"
            )
        
        if os.environ.get('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower() == 'true':
            results['warnings'].append(
                "Sensitive connections are allowed - disable in production for security"
            )
        
        if not os.environ.get('ENCRYPTION_KEY'):
            results['warnings'].append(
                "No encryption key configured - sensitive data will not be encrypted"
            )
        
        return results
    
    def _validate_secret_manager(self) -> Dict[str, Any]:
        """Validate secret management system."""
        logger.info("Validating secret management system...")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Initialize secret manager
            secret_manager = get_secret_manager()
            
            # Get health status
            health_status = secret_manager.get_health_status()
            
            # Check secret provider
            if not health_status.get('secret_provider', {}).get('available', False):
                results['valid'] = False
                results['errors'].append("Secret provider is not available")
            
            # Check encryption provider
            if not health_status.get('encryption_provider', {}).get('available', False):
                results['warnings'].append("Encryption provider is not available - credentials will not be encrypted")
            
            # Check secret operations
            secret_ops = health_status.get('secret_operations')
            if secret_ops and secret_ops != 'healthy':
                results['valid'] = False
                results['errors'].append(f"Secret operations failed: {secret_ops}")
            
            # Check encryption operations
            encryption_ops = health_status.get('encryption_operations')
            if encryption_ops and 'error' in str(encryption_ops):
                results['warnings'].append(f"Encryption operations issue: {encryption_ops}")
            
            # Check key rotation status
            encryption_keys = health_status.get('encryption_keys', {})
            if encryption_keys.get('rotation_needed'):
                results['warnings'].append("Encryption key rotation is recommended")
            
        except Exception as e:
            logger.error(f"Failed to validate secret manager: {e}")
            results['valid'] = False
            results['errors'].append(f"Secret manager initialization failed: {e}")
        
        return results
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate configuration recommendations based on validation results."""
        recommendations = []
        
        # Environment recommendations
        if not os.environ.get('ENCRYPTION_KEY'):
            recommendations.append(
                "Generate an encryption key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        if os.environ.get('FLASK_ENV') == 'development':
            recommendations.append(
                "For production deployment, set FLASK_ENV=production"
            )
        
        if not os.environ.get('JWT_SECRET_KEY') and os.environ.get('AUTHENTICATION_ENABLED', 'false').lower() == 'true':
            recommendations.append(
                "Generate a JWT secret key: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        
        # Security recommendations
        if os.environ.get('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower() == 'true':
            recommendations.append(
                "Disable sensitive connections in production: ALLOW_SENSITIVE_CONNECTIONS=false"
            )
        
        # Secret management recommendations
        secret_results = validation_results.get('secret_manager', {})
        if secret_results.get('warnings'):
            for warning in secret_results['warnings']:
                if 'key rotation' in warning.lower():
                    recommendations.append(
                        "Rotate encryption keys using the secret manager API or CLI tool"
                    )
        
        return recommendations
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print a formatted validation report."""
        print("\n" + "="*80)
        print("DEVICE SIMULATOR - STARTUP VALIDATION REPORT")
        print("="*80)
        
        if results['valid']:
            print("✅ Configuration validation PASSED")
        else:
            print("❌ Configuration validation FAILED")
        
        # Print errors
        if results['errors']:
            print(f"\n🚨 ERRORS ({len(results['errors'])}):")
            for i, error in enumerate(results['errors'], 1):
                print(f"   {i}. {error}")
        
        # Print warnings
        if results['warnings']:
            print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
            for i, warning in enumerate(results['warnings'], 1):
                print(f"   {i}. {warning}")
        
        # Print recommendations
        if results['recommendations']:
            print(f"\n💡 RECOMMENDATIONS ({len(results['recommendations'])}):")
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Print component status
        print(f"\n📊 COMPONENT STATUS:")
        env_status = "✅ VALID" if results['environment']['valid'] else "❌ INVALID"
        print(f"   Environment Variables: {env_status}")
        
        secret_status = "✅ HEALTHY" if results['secret_manager'].get('valid', True) else "❌ UNHEALTHY"
        print(f"   Secret Manager: {secret_status}")
        
        print("="*80 + "\n")


def validate_startup_configuration(exit_on_failure: bool = True) -> bool:
    """
    Validate startup configuration and optionally exit on failure.
    
    Args:
        exit_on_failure: Whether to exit the application if validation fails
        
    Returns:
        True if validation passed, False otherwise
    """
    validator = StartupValidator()
    results = validator.validate_all()
    
    # Always print the report
    validator.print_validation_report(results)
    
    if not results['valid']:
        logger.error("Startup validation failed - application cannot start safely")
        
        if exit_on_failure:
            print("❌ Application startup aborted due to configuration errors.")
            print("Please fix the errors above and restart the application.")
            sys.exit(1)
        
        return False
    
    if results['warnings']:
        logger.warning(f"Startup validation completed with {len(results['warnings'])} warnings")
    else:
        logger.info("Startup validation completed successfully")
    
    return True


def generate_secure_keys():
    """Generate secure keys for the application."""
    try:
        from cryptography.fernet import Fernet
        import secrets
        
        print("\n🔐 SECURE KEY GENERATION")
        print("="*50)
        
        # Generate Flask secret key
        flask_secret = secrets.token_urlsafe(32)
        print(f"Flask Secret Key (SECRET_KEY):")
        print(f"SECRET_KEY={flask_secret}")
        
        # Generate JWT secret key
        jwt_secret = secrets.token_urlsafe(32)
        print(f"\nJWT Secret Key (JWT_SECRET_KEY):")
        print(f"JWT_SECRET_KEY={jwt_secret}")
        
        # Generate encryption key
        encryption_key = Fernet.generate_key().decode()
        print(f"\nEncryption Key (ENCRYPTION_KEY):")
        print(f"ENCRYPTION_KEY={encryption_key}")
        
        print("\n⚠️  IMPORTANT SECURITY NOTES:")
        print("1. Store these keys securely and never commit them to version control")
        print("2. Use different keys for different environments (dev, staging, prod)")
        print("3. Rotate keys regularly according to your security policy")
        print("4. Consider using a dedicated secret management service for production")
        
        return {
            'SECRET_KEY': flask_secret,
            'JWT_SECRET_KEY': jwt_secret,
            'ENCRYPTION_KEY': encryption_key
        }
        
    except ImportError as e:
        print(f"❌ Failed to generate keys: {e}")
        print("Please install required dependencies: pip install cryptography")
        return None


if __name__ == '__main__':
    """CLI interface for validation and key generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Device Simulator Startup Validation')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--generate-keys', action='store_true', help='Generate secure keys')
    parser.add_argument('--no-exit', action='store_true', help='Don\'t exit on validation failure')
    
    args = parser.parse_args()
    
    if args.generate_keys:
        generate_secure_keys()
    elif args.validate:
        validate_startup_configuration(exit_on_failure=not args.no_exit)
    else:
        print("Use --validate to check configuration or --generate-keys to create secure keys")
        parser.print_help()
