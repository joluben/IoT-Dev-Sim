"""
Health check endpoints for the Device Simulator.

This module provides health check and system status endpoints for monitoring
and validation purposes.
"""

from flask import Blueprint, jsonify
from ..secrets_mgmt.secret_manager import get_secret_manager
from ..startup_validation import StartupValidator
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'device-simulator',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@health_bp.route('/api/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with component status."""
    try:
        # Get secret manager status
        secret_manager = get_secret_manager()
        secret_health = secret_manager.get_health_status()
        
        # Perform startup validation
        validator = StartupValidator()
        validation_results = validator.validate_all()
        
        health_status = {
            'status': 'healthy' if validation_results['valid'] else 'degraded',
            'service': 'device-simulator',
            'version': '1.0.0',
            'components': {
                'secret_manager': secret_health,
                'environment': validation_results['environment'],
                'validation': {
                    'valid': validation_results['valid'],
                    'errors': validation_results['errors'],
                    'warnings': validation_results['warnings']
                }
            },
            'recommendations': validation_results['recommendations']
        }
        
        status_code = 200 if validation_results['valid'] else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@health_bp.route('/api/health/security', methods=['GET'])
def security_health_check():
    """Security-focused health check."""
    try:
        secret_manager = get_secret_manager()
        security_status = secret_manager.get_health_status()
        
        # Add additional security checks
        security_status['encryption_available'] = security_status.get('encryption_provider', {}).get('available', False)
        security_status['secrets_available'] = security_status.get('secret_provider', {}).get('available', False)
        
        # Check key rotation status
        encryption_keys = security_status.get('encryption_keys', {})
        security_status['key_rotation_needed'] = encryption_keys.get('rotation_needed', False)
        
        overall_status = 'healthy'
        if not security_status['secrets_available']:
            overall_status = 'unhealthy'
        elif not security_status['encryption_available'] or security_status['key_rotation_needed']:
            overall_status = 'degraded'
        
        return jsonify({
            'status': overall_status,
            'security': security_status
        }), 200 if overall_status == 'healthy' else 503
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
