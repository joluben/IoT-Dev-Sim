#!/usr/bin/env python3
"""
DevSim Production Startup Script
================================

This script helps start the DevSim backend in production mode with proper
validation and configuration checks.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path


def check_environment():
    """Check if the environment is properly configured for production"""
    print("🔍 Checking production environment...")
    
    errors = []
    warnings = []
    
    # Check required environment variables
    required_vars = [
        'FLASK_ENV',
        'SECRET_KEY',
        'ENCRYPTION_KEY',
        'JWT_SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Check Flask environment
    flask_env = os.getenv('FLASK_ENV', '').lower()
    if flask_env != 'production':
        errors.append(f"FLASK_ENV must be 'production', got: {flask_env}")
    
    # Check debug mode
    flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()
    if flask_debug in ('true', '1', 'yes'):
        errors.append("FLASK_DEBUG must be 'false' in production")
    
    # Check sensitive connections
    allow_sensitive = os.getenv('ALLOW_SENSITIVE_CONNECTIONS', 'false').lower()
    if allow_sensitive in ('true', '1', 'yes'):
        errors.append("ALLOW_SENSITIVE_CONNECTIONS must be 'false' in production")
    
    # Check directories
    required_dirs = [
        '/app/logs',
        '/app/data',
        '/app/uploads'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                warnings.append(f"Created missing directory: {dir_path}")
            except Exception as e:
                errors.append(f"Cannot create directory {dir_path}: {e}")
    
    # Check configuration files
    config_files = [
        'gunicorn_config.py',
        'logging_config.py'
    ]
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            errors.append(f"Missing configuration file: {config_file}")
    
    # Report results
    if errors:
        print("❌ Environment check failed:")
        for error in errors:
            print(f"   • {error}")
        return False
    
    if warnings:
        print("⚠️  Environment warnings:")
        for warning in warnings:
            print(f"   • {warning}")
    
    print("✅ Environment check passed")
    return True


def start_gunicorn():
    """Start Gunicorn with production configuration"""
    print("🚀 Starting DevSim backend with Gunicorn...")
    
    # Gunicorn command
    cmd = [
        'gunicorn',
        '--config', 'gunicorn_config.py',
        'run:app'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Start Gunicorn
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                print("⚠️  Graceful shutdown timeout, forcing termination...")
                process.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Monitor process output
        print("📊 Gunicorn output:")
        print("-" * 50)
        
        for line in process.stdout:
            print(line.rstrip())
            
            # Check for startup completion
            if "DevSim Backend ready to serve requests" in line:
                print("-" * 50)
                print("✅ DevSim backend started successfully!")
                print("🌐 Server is ready to accept requests")
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            print("✅ Gunicorn exited successfully")
        else:
            print(f"❌ Gunicorn exited with code: {return_code}")
        
        return return_code
        
    except FileNotFoundError:
        print("❌ Gunicorn not found. Install with: pip install gunicorn")
        return 1
    except Exception as e:
        print(f"❌ Failed to start Gunicorn: {e}")
        return 1


def main():
    """Main entry point"""
    print("=" * 60)
    print("DevSim Backend Production Startup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('run.py'):
        print("❌ Error: run.py not found. Please run from the backend directory.")
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Start Gunicorn
    return_code = start_gunicorn()
    sys.exit(return_code)


if __name__ == "__main__":
    main()