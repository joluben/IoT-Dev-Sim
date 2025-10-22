#!/usr/bin/env python3
"""
DevSim Production Logging Configuration
=======================================

This module provides production-ready logging configuration for DevSim backend.
It includes structured JSON logging, proper log levels, and rotation policies.
"""

import os
import sys
import logging
import logging.config
from datetime import datetime


def get_log_level():
    """Get log level from environment variable"""
    level = os.getenv('LOG_LEVEL', 'INFO').upper()
    return getattr(logging, level, logging.INFO)


def get_logging_config():
    """Get comprehensive logging configuration for production"""
    
    # Create logs directory if it doesn't exist
    log_dir = '/app/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s (%(filename)s:%(lineno)d)',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
            },
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': sys.stdout
            },
            'file_detailed': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': f'{log_dir}/devsim.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_json': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': f'{log_dir}/devsim.json',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': f'{log_dir}/devsim_errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            'devsim': {
                'level': get_log_level(),
                'handlers': ['console', 'file_detailed', 'file_json', 'error_file'],
                'propagate': False
            },
            'gunicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file_detailed'],
                'propagate': False
            },
            'gunicorn.error': {
                'level': 'INFO',
                'handlers': ['console', 'error_file'],
                'propagate': False
            },
            'gunicorn.access': {
                'level': 'INFO',
                'handlers': ['file_detailed'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'WARNING',
                'handlers': ['console', 'file_detailed'],
                'propagate': False
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['file_detailed'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'WARNING',
                'handlers': ['file_detailed'],
                'propagate': False
            }
        },
        'root': {
            'level': get_log_level(),
            'handlers': ['console', 'file_detailed', 'error_file']
        }
    }
    
    return config


def setup_logging():
    """Setup logging configuration for the application"""
    try:
        config = get_logging_config()
        logging.config.dictConfig(config)
        
        # Get logger and log startup
        logger = logging.getLogger('devsim')
        logger.info("Logging configuration initialized successfully")
        logger.info(f"Log level: {logging.getLevelName(logger.level)}")
        logger.info(f"Log directory: /app/logs")
        
        return True
        
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger = logging.getLogger('devsim')
        logger.error(f"Failed to setup advanced logging configuration: {e}")
        logger.info("Using basic logging configuration as fallback")
        return False


def get_request_logger():
    """Get logger for request tracking"""
    return logging.getLogger('devsim.requests')


def get_security_logger():
    """Get logger for security events"""
    return logging.getLogger('devsim.security')


def get_performance_logger():
    """Get logger for performance monitoring"""
    return logging.getLogger('devsim.performance')


def log_startup_info():
    """Log important startup information"""
    logger = logging.getLogger('devsim')
    
    logger.info("="*50)
    logger.info("DevSim Backend Starting")
    logger.info("="*50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Debug mode: {os.getenv('FLASK_DEBUG', 'false')}")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*50)


if __name__ == "__main__":
    # Test logging configuration
    setup_logging()
    log_startup_info()
    
    logger = logging.getLogger('devsim')
    logger.debug("Debug message test")
    logger.info("Info message test")
    logger.warning("Warning message test")
    logger.error("Error message test")
    
    print("Logging configuration test completed. Check /app/logs/ for output files.")