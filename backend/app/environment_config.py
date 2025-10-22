#!/usr/bin/env python3
"""
DevSim Configuration Management
===============================

This module provides environment-aware configuration for the DevSim application.
It ensures proper security settings based on the deployment environment and
validates critical configuration parameters.
"""

import os
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    debug_enabled: bool = False
    allow_sensitive_connections: bool = False
    force_https: bool = False
    hsts_max_age: int = 31536000
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ['*']  # Default for development


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class AppConfig:
    """Main application configuration"""
    environment: str
    secret_key: str
    encryption_key: str
    jwt_secret_key: str
    max_content_length: int
    upload_folder: str
    security: SecurityConfig
    database: DatabaseConfig
    
    # Authentication
    authentication_enabled: bool = False
    keycloak_enabled: bool = False
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    log_level: str = 'INFO'


class ConfigurationManager:
    """Manages application configuration based on environment"""
    
    REQUIRED_PRODUCTION_VARS = [
        'SECRET_KEY',
        'ENCRYPTION_KEY', 
        'JWT_SECRET_KEY'
    ]
    
    def __init__(self):
        self.environment = os.getenv('FLASK_ENV', 'development').lower()
        
    def load_config(self) -> AppConfig:
        """Load configuration based on current environment"""
        
        if self.environment == 'production':
            return self._load_production_config()
        elif self.environment == 'testing':
            return self._load_testing_config()
        else:
            return self._load_development_config()
    
    def _load_production_config(self) -> AppConfig:
        """Load production configuration with strict security"""
        
        # Validate required environment variables
        missing_vars = []
        for var in self.REQUIRED_PRODUCTION_VARS:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise RuntimeError(
                f"Missing required production environment variables: {', '.join(missing_vars)}"
            )
        
        # Validate security settings
        self._validate_production_security()
        
        # Security configuration (strict)
        security = SecurityConfig(
            debug_enabled=False,  # NEVER enable debug in production
            allow_sensitive_connections=False,  # NEVER allow in production
            force_https=os.getenv('FORCE_HTTPS', 'true').lower() == 'true',
            hsts_max_age=int(os.getenv('HSTS_MAX_AGE', 31536000)),
            cors_origins=self._parse_cors_origins()
        )
        
        # Database configuration
        database = DatabaseConfig(
            url=os.getenv('DATABASE_URL', 'postgresql://devsim_user:password@postgres:5432/devsim_prod'),
            pool_size=int(os.getenv('DB_POOL_SIZE', 10)),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', 20)),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', 30)),
            echo=False  # Never log SQL in production
        )
        
        return AppConfig(
            environment='production',
            secret_key=os.getenv('SECRET_KEY'),
            encryption_key=os.getenv('ENCRYPTION_KEY'),
            jwt_secret_key=os.getenv('JWT_SECRET_KEY'),
            max_content_length=int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)),
            upload_folder=os.getenv('UPLOAD_FOLDER', '/app/uploads'),
            security=security,
            database=database,
            authentication_enabled=os.getenv('AUTHENTICATION_ENABLED', 'true').lower() == 'true',
            keycloak_enabled=os.getenv('KEYCLOAK_ENABLED', 'true').lower() == 'true',
            sentry_dsn=os.getenv('SENTRY_DSN'),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
    
    def _load_development_config(self) -> AppConfig:
        """Load development configuration with relaxed security"""
        
        # Security configuration (relaxed for development)
        security = SecurityConfig(
            debug_enabled=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
            allow_sensitive_connections=os.getenv('ALLOW_SENSITIVE_CONNECTIONS', 'true').lower() == 'true',
            force_https=False,
            cors_origins=['*']  # Allow all origins in development
        )
        
        # Database configuration
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        os.makedirs(data_dir, exist_ok=True)
        default_db_url = f"sqlite:///{os.path.join(data_dir, 'devsim.db')}"
        
        database = DatabaseConfig(
            url=os.getenv('DATABASE_URL', default_db_url),
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
        )
        
        return AppConfig(
            environment='development',
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            encryption_key=os.getenv('ENCRYPTION_KEY', 'dev-encryption-key-change-in-production'),
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production'),
            max_content_length=int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)),
            upload_folder=os.getenv('UPLOAD_FOLDER') or os.path.join(os.path.dirname(__file__), '..', 'uploads'),
            security=security,
            database=database,
            authentication_enabled=os.getenv('AUTHENTICATION_ENABLED', 'false').lower() == 'true',
            keycloak_enabled=os.getenv('KEYCLOAK_ENABLED', 'false').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'DEBUG')
        )
    
    def _load_testing_config(self) -> AppConfig:
        """Load testing configuration"""
        
        # Security configuration (secure but testable)
        security = SecurityConfig(
            debug_enabled=False,  # No debug in testing
            allow_sensitive_connections=False,
            force_https=False,
            cors_origins=['http://localhost', 'http://127.0.0.1']
        )
        
        # In-memory database for testing
        database = DatabaseConfig(
            url=os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:'),
            echo=False
        )
        
        return AppConfig(
            environment='testing',
            secret_key='test-secret-key',
            encryption_key='test-encryption-key',
            jwt_secret_key='test-jwt-secret',
            max_content_length=1024 * 1024,  # 1MB for testing
            upload_folder='/tmp/test_uploads',
            security=security,
            database=database,
            authentication_enabled=False,  # Disable auth in tests
            keycloak_enabled=False,
            log_level='WARNING'  # Reduce log noise in tests
        )
    
    def _validate_production_security(self):
        """Validate production security settings"""
        
        # Check debug mode
        flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()
        if flask_debug in ('true', '1', 'yes'):
            raise RuntimeError(
                "FLASK_DEBUG must be 'false' in production environment"
            )
        
        # Check sensitive connections
        allow_sensitive = os.getenv('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower()
        if allow_sensitive in ('true', '1', 'yes'):
            raise RuntimeError(
                "ALLOW_SENSITIVE_CONNECTIONS must be 'false' in production environment"
            )
        
        # Validate CORS origins
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if not cors_origins or cors_origins == '*':
            raise RuntimeError(
                "CORS_ORIGINS must be set to specific domains in production (not '*')"
            )
    
    def _parse_cors_origins(self) -> list:
        """Parse CORS origins from environment variable"""
        cors_origins = os.getenv('CORS_ORIGINS', '')
        
        if not cors_origins:
            if self.environment == 'production':
                raise RuntimeError("CORS_ORIGINS must be set in production")
            return ['*']  # Default for non-production
        
        # Split by comma and clean up
        origins = [origin.strip() for origin in cors_origins.split(',')]
        return [origin for origin in origins if origin]
    
    def validate_config(self, config: AppConfig) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'environment': config.environment
        }
        
        # Validate secret key
        if not config.secret_key or len(config.secret_key) < 32:
            results['errors'].append("SECRET_KEY must be at least 32 characters long")
            results['valid'] = False
        
        # Validate encryption key
        if not config.encryption_key:
            results['errors'].append("ENCRYPTION_KEY is required")
            results['valid'] = False
        
        # Production-specific validations
        if config.environment == 'production':
            if config.security.debug_enabled:
                results['errors'].append("Debug mode must be disabled in production")
                results['valid'] = False
            
            if config.security.allow_sensitive_connections:
                results['errors'].append("Sensitive connections must be disabled in production")
                results['valid'] = False
            
            if '*' in config.security.cors_origins:
                results['errors'].append("CORS origins must be specific domains in production")
                results['valid'] = False
        
        # Development warnings
        if config.environment == 'development':
            if config.security.debug_enabled:
                results['warnings'].append("Debug mode is enabled - disable in production")
            
            if config.security.allow_sensitive_connections:
                results['warnings'].append("Sensitive connections allowed - disable in production")
        
        return results


def get_config() -> AppConfig:
    """Get application configuration for current environment"""
    manager = ConfigurationManager()
    config = manager.load_config()
    
    # Validate configuration
    validation = manager.validate_config(config)
    
    if not validation['valid']:
        print("❌ Configuration validation failed:")
        for error in validation['errors']:
            print(f"   • {error}")
        sys.exit(1)
    
    # Show warnings
    if validation['warnings']:
        print("⚠️  Configuration warnings:")
        for warning in validation['warnings']:
            print(f"   • {warning}")
    
    return config


def print_config_summary(config: AppConfig):
    """Print configuration summary for debugging"""
    print(f"📋 Configuration Summary ({config.environment.upper()})")
    print("=" * 50)
    print(f"Environment: {config.environment}")
    print(f"Debug Mode: {config.security.debug_enabled}")
    print(f"Sensitive Connections: {config.security.allow_sensitive_connections}")
    print(f"Force HTTPS: {config.security.force_https}")
    print(f"CORS Origins: {config.security.cors_origins}")
    print(f"Authentication: {config.authentication_enabled}")
    print(f"Keycloak: {config.keycloak_enabled}")
    print(f"Database: {config.database.url}")
    print(f"Log Level: {config.log_level}")
    print("=" * 50)