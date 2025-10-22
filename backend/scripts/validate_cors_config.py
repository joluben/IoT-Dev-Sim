#!/usr/bin/env python3
"""
CORS Configuration Validator
============================

This script validates the CORS configuration for DevSim to ensure
production security requirements are met.
"""

import os
import sys
import re
from typing import List, Dict, Any


def validate_cors_origins(cors_origins: str, environment: str) -> Dict[str, Any]:
    """Validate CORS origins configuration"""
    
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'origins': []
    }
    
    if not cors_origins:
        result['errors'].append("CORS_ORIGINS is not set")
        result['valid'] = False
        return result
    
    # Parse origins
    origins = [origin.strip() for origin in cors_origins.split(',')]
    origins = [origin for origin in origins if origin]  # Remove empty strings
    result['origins'] = origins
    
    # Environment-specific validation
    if environment == 'production':
        # Production must not have wildcards
        if '*' in origins:
            result['errors'].append("Production CORS cannot use wildcard '*'")
            result['valid'] = False
        
        # All origins must be HTTPS in production
        for origin in origins:
            if not origin.startswith('https://'):
                result['errors'].append(f"Production origin must use HTTPS: {origin}")
                result['valid'] = False
        
        # Validate domain format
        domain_pattern = re.compile(r'^https://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for origin in origins:
            if not domain_pattern.match(origin):
                result['warnings'].append(f"Origin format may be invalid: {origin}")
        
        # Check for common security issues
        for origin in origins:
            if 'localhost' in origin or '127.0.0.1' in origin:
                result['errors'].append(f"Production cannot use localhost/127.0.0.1: {origin}")
                result['valid'] = False
    
    elif environment == 'development':
        # Development warnings
        if '*' in origins:
            result['warnings'].append("Wildcard CORS in development - ensure this is disabled in production")
        
        # Check for mixed HTTP/HTTPS
        http_origins = [o for o in origins if o.startswith('http://')]
        https_origins = [o for o in origins if o.startswith('https://')]
        
        if http_origins and https_origins:
            result['warnings'].append("Mixed HTTP/HTTPS origins detected")
    
    return result


def validate_nginx_cors_config(nginx_config_path: str) -> Dict[str, Any]:
    """Validate nginx CORS configuration"""
    
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'has_wildcard': False,
        'has_restrictive_policy': False
    }
    
    if not os.path.exists(nginx_config_path):
        result['errors'].append(f"Nginx config file not found: {nginx_config_path}")
        result['valid'] = False
        return result
    
    try:
        with open(nginx_config_path, 'r') as f:
            content = f.read()
        
        # Check for wildcard CORS
        if 'Access-Control-Allow-Origin *' in content:
            result['has_wildcard'] = True
            result['errors'].append("Nginx config contains wildcard CORS policy")
            result['valid'] = False
        
        # Check for restrictive CORS policy
        if '$cors_origin' in content or 'map $http_origin' in content:
            result['has_restrictive_policy'] = True
        
        # Check for security headers
        security_headers = [
            'Strict-Transport-Security',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection'
        ]
        
        missing_headers = []
        for header in security_headers:
            if header not in content:
                missing_headers.append(header)
        
        if missing_headers:
            result['warnings'].append(f"Missing security headers: {', '.join(missing_headers)}")
    
    except Exception as e:
        result['errors'].append(f"Error reading nginx config: {e}")
        result['valid'] = False
    
    return result


def main():
    """Main validation function"""
    
    print("🔍 Validating CORS Configuration")
    print("=" * 50)
    
    # Get environment
    environment = os.getenv('FLASK_ENV', 'development').lower()
    print(f"Environment: {environment}")
    
    # Validate CORS origins
    cors_origins = os.getenv('CORS_ORIGINS', '')
    cors_result = validate_cors_origins(cors_origins, environment)
    
    print(f"\n📋 CORS Origins Validation:")
    print(f"Origins: {cors_result['origins']}")
    
    if cors_result['errors']:
        print("❌ Errors:")
        for error in cors_result['errors']:
            print(f"   • {error}")
    
    if cors_result['warnings']:
        print("⚠️  Warnings:")
        for warning in cors_result['warnings']:
            print(f"   • {warning}")
    
    if not cors_result['errors']:
        print("✅ CORS origins validation passed")
    
    # Validate nginx configuration
    nginx_configs = [
        ('Development', 'frontend/nginx.conf'),
        ('Production', 'frontend/nginx.prod.conf')
    ]
    
    nginx_valid = True
    for config_name, config_path in nginx_configs:
        print(f"\n🌐 {config_name} Nginx Configuration:")
        
        nginx_result = validate_nginx_cors_config(config_path)
        
        if nginx_result['errors']:
            print("❌ Errors:")
            for error in nginx_result['errors']:
                print(f"   • {error}")
            nginx_valid = False
        
        if nginx_result['warnings']:
            print("⚠️  Warnings:")
            for warning in nginx_result['warnings']:
                print(f"   • {warning}")
        
        if nginx_result['has_wildcard']:
            print("🚨 Wildcard CORS detected")
        
        if nginx_result['has_restrictive_policy']:
            print("🔒 Restrictive CORS policy detected")
        
        if not nginx_result['errors']:
            print(f"✅ {config_name} nginx validation passed")
    
    # Overall result
    print("\n" + "=" * 50)
    overall_valid = cors_result['valid'] and nginx_valid
    
    if overall_valid:
        print("✅ All CORS validations passed")
        return 0
    else:
        print("❌ CORS validation failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())