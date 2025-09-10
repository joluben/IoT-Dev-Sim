from flask import Blueprint, request, jsonify
from ..security import get_secret_manager, rotate_encryption_keys
import logging

security_bp = Blueprint('security', __name__)
logger = logging.getLogger(__name__)

@security_bp.route('/api/security/keys/status', methods=['GET'])
def get_key_status():
    """Get current encryption key status and rotation information"""
    try:
        secret_manager = get_secret_manager()
        status = secret_manager.get_key_status()
        
        return jsonify({
            'success': True,
            'data': status
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get key status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve key status'
        }), 500

@security_bp.route('/api/security/keys/rotate', methods=['POST'])
def rotate_keys():
    """Rotate encryption keys"""
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
        
        secret_manager = get_secret_manager()
        new_version = secret_manager.rotate_keys(force=force)
        
        return jsonify({
            'success': True,
            'message': 'Key rotation completed successfully',
            'data': {
                'new_version': new_version,
                'force_rotation': force
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Key rotation failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to rotate encryption keys'
        }), 500

@security_bp.route('/api/security/credentials/migrate', methods=['POST'])
def migrate_credentials():
    """Migrate credentials from old key version to new version"""
    try:
        data = request.get_json()
        if not data or 'old_version' not in data or 'new_version' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: old_version, new_version'
            }), 400
        
        old_version = data['old_version']
        new_version = data['new_version']
        
        secret_manager = get_secret_manager()
        result = secret_manager.migrate_credentials(old_version, new_version)
        
        return jsonify({
            'success': True,
            'message': 'Credential migration completed',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Credential migration failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to migrate credentials'
        }), 500

@security_bp.route('/api/security/health', methods=['GET'])
def security_health_check():
    """Perform security health check"""
    try:
        secret_manager = get_secret_manager()
        status = secret_manager.get_key_status()
        
        # Perform health checks
        health_issues = []
        
        # Check if current key exists
        if not status.get('current_version'):
            health_issues.append('No current encryption key available')
        
        # Check key age
        key_age = status.get('current_key_age_days')
        if key_age and key_age > 90:
            health_issues.append(f'Current key is {key_age} days old (recommended rotation)')
        
        # Check if rotation is needed
        if status.get('rotation_needed'):
            health_issues.append('Key rotation is recommended')
        
        # Check for inactive keys that might need cleanup
        inactive_keys = [k for k in status.get('keys', []) if not k['is_active']]
        if len(inactive_keys) > 5:
            health_issues.append(f'Too many inactive keys ({len(inactive_keys)})')
        
        health_status = 'healthy' if not health_issues else 'warning'
        
        return jsonify({
            'success': True,
            'data': {
                'status': health_status,
                'issues': health_issues,
                'key_info': {
                    'current_version': status.get('current_version'),
                    'total_keys': status.get('total_keys'),
                    'active_keys': status.get('active_keys'),
                    'key_age_days': key_age
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to perform security health check'
        }), 500

@security_bp.route('/api/security/keys/generate', methods=['POST'])
def generate_new_key():
    """Generate a new encryption key (emergency use)"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Manual generation')
        
        secret_manager = get_secret_manager()
        new_version = secret_manager._generate_new_master_key()
        
        logger.warning(f"New encryption key generated manually. Reason: {reason}")
        
        return jsonify({
            'success': True,
            'message': 'New encryption key generated successfully',
            'data': {
                'new_version': new_version,
                'reason': reason
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to generate new key: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate new encryption key'
        }), 500

@security_bp.route('/api/security/test/encrypt', methods=['POST'])
def test_encryption():
    """Test encryption/decryption functionality (for testing only)"""
    try:
        data = request.get_json()
        if not data or 'test_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing test_data parameter'
            }), 400
        
        test_data = data['test_data']
        
        # Only allow in development/testing
        import os
        if os.environ.get('FLASK_ENV') != 'development':
            return jsonify({
                'success': False,
                'error': 'Test endpoint only available in development mode'
            }), 403
        
        secret_manager = get_secret_manager()
        
        # Encrypt test data
        encrypted_payload = secret_manager.encrypt(test_data)
        
        # Decrypt test data
        decrypted_data = secret_manager.decrypt(encrypted_payload)
        
        # Verify round-trip
        success = test_data == decrypted_data
        
        return jsonify({
            'success': success,
            'message': 'Encryption test completed',
            'data': {
                'original_length': len(test_data),
                'encrypted_version': encrypted_payload.get('version'),
                'round_trip_success': success
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Encryption test failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Encryption test failed'
        }), 500
