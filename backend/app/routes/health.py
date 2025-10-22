"""
Health check endpoints for the Device Simulator.

This module provides health check and system status endpoints for monitoring
and validation purposes. Includes system resource monitoring for production.
"""

from flask import Blueprint, jsonify
from ..secrets_mgmt.secret_manager import get_secret_manager
from ..startup_validation import StartupValidator
import logging
import time
import os

# Try to import psutil for system monitoring (production dependency)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

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


@health_bp.route('/api/health/system', methods=['GET'])
def system_health_check():
    """System resource health check for production monitoring."""
    try:
        start_time = time.time()
        
        system_info = {
            'timestamp': time.time(),
            'uptime': None,
            'cpu': {},
            'memory': {},
            'disk': {},
            'process': {},
            'load_balancer_ready': True
        }
        
        if PSUTIL_AVAILABLE:
            # CPU information
            system_info['cpu'] = {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            system_info['memory'] = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # Disk information
            disk = psutil.disk_usage('/')
            system_info['disk'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
            
            # Process information
            process = psutil.Process()
            system_info['process'] = {
                'pid': process.pid,
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            }
            
            # System uptime
            system_info['uptime'] = time.time() - psutil.boot_time()
            
            # Health thresholds
            cpu_healthy = system_info['cpu']['percent'] < 80
            memory_healthy = system_info['memory']['percent'] < 85
            disk_healthy = system_info['disk']['percent'] < 90
            
            # Determine overall health
            if cpu_healthy and memory_healthy and disk_healthy:
                overall_status = 'healthy'
            elif system_info['cpu']['percent'] > 95 or system_info['memory']['percent'] > 95:
                overall_status = 'critical'
            else:
                overall_status = 'warning'
                
        else:
            # Fallback when psutil is not available
            overall_status = 'healthy'
            system_info['note'] = 'System monitoring not available (psutil not installed)'
        
        # Response time
        system_info['response_time'] = time.time() - start_time
        
        # Load balancer readiness check
        system_info['load_balancer_ready'] = overall_status in ['healthy', 'warning']
        
        status_code = 200
        if overall_status == 'critical':
            status_code = 503
        elif overall_status == 'warning':
            status_code = 200  # Still serve traffic but with warning
            
        return jsonify({
            'status': overall_status,
            'system': system_info
        }), status_code
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'system': {'error': 'System monitoring failed'}
        }), 500


@health_bp.route('/api/health/readiness', methods=['GET'])
def readiness_check():
    """Kubernetes/Docker readiness probe endpoint."""
    try:
        # Quick checks for readiness
        checks = {
            'database': False,
            'secrets': False,
            'basic_functionality': False
        }
        
        # Check database connectivity (basic)
        try:
            from ..database.session_manager import get_session_manager
            session_manager = get_session_manager()
            # Simple query to test database
            with session_manager.get_session() as session:
                session.execute("SELECT 1")
            checks['database'] = True
        except Exception as e:
            logger.warning(f"Database readiness check failed: {e}")
        
        # Check secrets availability
        try:
            secret_manager = get_secret_manager()
            health = secret_manager.get_health_status()
            checks['secrets'] = health.get('secret_provider', {}).get('available', False)
        except Exception as e:
            logger.warning(f"Secrets readiness check failed: {e}")
        
        # Basic functionality check
        checks['basic_functionality'] = True  # If we got this far, basic functionality works
        
        # Determine readiness
        ready = all(checks.values())
        
        return jsonify({
            'ready': ready,
            'checks': checks,
            'timestamp': time.time()
        }), 200 if ready else 503
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'ready': False,
            'error': str(e),
            'timestamp': time.time()
        }), 503


@health_bp.route('/api/health/liveness', methods=['GET'])
def liveness_check():
    """Kubernetes/Docker liveness probe endpoint."""
    try:
        # Very basic liveness check - if we can respond, we're alive
        return jsonify({
            'alive': True,
            'timestamp': time.time(),
            'pid': os.getpid()
        }), 200
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return jsonify({
            'alive': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500
