from flask import Blueprint, request, jsonify
import os
import logging
from ..models import Device, Connection
from ..transmission import TransmissionManager
from ..scheduler import get_scheduler
from ..transmission_state import get_state_manager
from ..validators import validate_transmission_request, validate_transmission_config_update

transmissions_bp = Blueprint('transmissions_bp', __name__)

@transmissions_bp.route('/api/transmissions/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to verify routes are working"""
    return jsonify({
        'status': 'ok',
        'message': 'Transmissions blueprint is working',
        'endpoints': [
            'GET /api/transmissions/test',
            'GET /api/devices/<id>/transmission-config',
            'PUT /api/devices/<id>/transmission-config',
            'POST /api/devices/<id>/transmit',
            'GET /api/devices/<id>/debug'
        ]
    })

@transmissions_bp.route('/api/devices/<int:device_id>/transmission-config', methods=['GET', 'PUT'])
def handle_transmission_config(device_id):
    try:
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
    except Exception as e:
        logging.error(f"Error getting device {device_id}: {e}")
        return jsonify({'error': f'Error retrieving device: {str(e)}'}), 500

    if request.method == 'GET':
        return jsonify({
            'device_type': device.device_type,
            'transmission_frequency': device.transmission_frequency,
            'transmission_enabled': device.transmission_enabled,
            'selected_connection_id': getattr(device, 'selected_connection_id', None),
            'include_device_id_in_payload': getattr(device, 'include_device_id_in_payload', False),
            'auto_reset_counter': getattr(device, 'auto_reset_counter', False)
        })

    if request.method == 'PUT':
        try:
            # Validate request has JSON data
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            # Validar configuración
            try:
                is_valid, error_msg = validate_transmission_config_update(
                    device_type=data.get('device_type'),
                    frequency=data.get('transmission_frequency'),
                    enabled=data.get('transmission_enabled')
                )
                
                if not is_valid:
                    return jsonify({'error': error_msg}), 400
            except Exception as validation_error:
                logging.error(f"Validation error for device {device_id}: {validation_error}")
                return jsonify({'error': f'Validation failed: {str(validation_error)}'}), 400
            
            # Validate connection_id if provided
            connection_id = data.get('connection_id')
            if connection_id is not None:
                try:
                    connection_id = int(connection_id)
                    # Verify connection exists
                    from ..models import Connection
                    connection = Connection.get_by_id(connection_id)
                    if not connection:
                        return jsonify({'error': f'Connection with ID {connection_id} not found'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': 'connection_id must be a valid integer'}), 400
            
            device.update_transmission_config(
                device_type=data.get('device_type'),
                frequency=data.get('transmission_frequency'),
                enabled=data.get('transmission_enabled'),
                connection_id=connection_id,
                include_device_id_in_payload=data.get('include_device_id_in_payload'),
                auto_reset_counter=data.get('auto_reset_counter', False)
            )
            # NO reprogramar automáticamente al guardar configuración.
            # La programación se controla explícitamente vía /pause, /resume y /stop.
            return jsonify(device.to_dict())
            
        except Exception as e:
            import logging
            logging.error(f"Error updating transmission config for device {device_id}: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@transmissions_bp.route('/api/devices/<int:device_id>/transmit-now/<int:connection_id>', methods=['POST'])
def transmit_now(device_id, connection_id):
    """Ejecuta transmisión manual solo si está permitido"""
    state_manager = get_state_manager()
    
    if not state_manager.can_execute_manual(device_id):
        return jsonify({
            'error': 'Cannot execute manual transmission while another manual transmission is in progress',
            'current_state': state_manager.get_device_state(device_id)
        }), 400
    
    try:
        result = state_manager.execute_manual_transmission(device_id, connection_id)
        if result['success']:
            # Devolver información útil para actualizar UI
            refreshed = Device.get_by_id(device_id)
            return jsonify({
                'message': result['message'],
                'current_row_index': refreshed.current_row_index,
                'last_transmission': refreshed.last_transmission,
                'success': True
            }), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@transmissions_bp.route('/api/devices/<int:device_id>/transmit', methods=['POST'])
def transmit_legacy(device_id):
    """Legacy endpoint for backward compatibility"""
    try:
        # Validate request has JSON data
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        connection_id = data.get('connection_id')
        if not connection_id:
            return jsonify({'error': 'connection_id is required'}), 400
        
        # Validate connection_id is a valid integer
        try:
            connection_id = int(connection_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'connection_id must be a valid integer'}), 400

        return transmit_now(device_id, connection_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in transmit_legacy endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@transmissions_bp.route('/api/devices/<int:device_id>/transmission-history', methods=['GET'])
def get_history(device_id):
    # Leer parámetro limit (opcional), por defecto 20
    try:
        limit = int(request.args.get('limit', 20))
    except (TypeError, ValueError):
        limit = 20

    raw_history = TransmissionManager.get_transmission_history(device_id, limit=limit)

    # Normalizar claves para compatibilidad con UI
    normalized = []
    for item in raw_history:
        # Copia superficial del dict
        entry = dict(item)
        # Asegurar campo 'timestamp' esperado por el frontend
        entry['timestamp'] = entry.get('transmission_time')
        # Compatibilidad adicional: 'sent_at' y 'created_at'
        entry.setdefault('sent_at', entry['timestamp'])
        entry.setdefault('created_at', entry['timestamp'])
        normalized.append(entry)

    return jsonify(normalized)

@transmissions_bp.route('/api/devices/<int:device_id>/reset-sensor', methods=['POST'])
def reset_sensor(device_id):
    device = Device.get_by_id(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    if device.device_type != 'Sensor':
        return jsonify({'error': 'Device is not a Sensor'}), 400

    device.reset_sensor_position()
    return jsonify({'message': 'Sensor position reset successfully'}), 200

@transmissions_bp.route('/api/scheduled-jobs', methods=['GET'])
def get_scheduled_jobs():
    scheduler = get_scheduler()
    jobs = scheduler.get_scheduled_jobs()
    return jsonify(jobs)


@transmissions_bp.route('/api/devices/<int:device_id>/transmission-state', methods=['GET'])
def get_transmission_state(device_id):
    """Retorna estado actual y acciones disponibles para el dispositivo"""
    state_manager = get_state_manager()
    current_state = state_manager.get_device_state(device_id)
    available_actions = state_manager.get_available_actions(device_id)
    
    return jsonify({
        'device_id': device_id,
        'current_state': current_state,
        'available_actions': available_actions,
        'last_transmission': state_manager.get_last_transmission_time(device_id),
        'next_scheduled': state_manager.get_next_scheduled_transmission(device_id)
    })

@transmissions_bp.route('/api/devices/<int:device_id>/start-transmission/<int:connection_id>', methods=['POST'])
def start_transmission(device_id, connection_id):
    """Iniciar transmisión automática"""
    try:
        # Helper to write debug info to data/transmissions_debug.log
        def _debug(msg):
            try:
                debug_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'transmissions_debug.log')
                with open(debug_path, 'a', encoding='utf-8') as f:
                    f.write(f"[start_transmission] {msg}\n")
            except Exception:
                pass

        _debug(f"called with device_id={device_id}, connection_id={connection_id}")
        # Validar que el dispositivo existe
        device = Device.get_by_id(device_id)
        if not device:
            _debug("device not found")
            return jsonify({'error': 'Device not found'}), 404
            
        # Validar que la conexión existe y está activa
        connection = Connection.get_by_id(connection_id)
        if not connection:
            _debug("connection not found")
            return jsonify({'error': 'Connection not found'}), 404
            
        if not getattr(connection, 'is_active', False):
            _debug("connection inactive")
            return jsonify({'error': 'Connection is not active'}), 400
            
        # Validar frecuencia de transmisión
        if not device.transmission_frequency or device.transmission_frequency <= 0:
            _debug(f"invalid frequency: {getattr(device, 'transmission_frequency', None)}")
            return jsonify({'error': 'Invalid transmission frequency. Please configure a valid frequency first.'}), 400
            
        state_manager = get_state_manager()
        if not state_manager:
            _debug("state manager not available")
            return jsonify({'error': 'Transmission state manager not available'}), 500
        
        _debug("calling state_manager.start_automatic_transmission")
        if state_manager.start_automatic_transmission(device_id, connection_id):
            device.update_transmission_config(enabled=True)
            _debug("automatic transmission started successfully")
            return jsonify({
                'message': 'Automatic transmission started',
                'current_state': state_manager.get_device_state(device_id),
                'transmission_enabled': True,
                'next_scheduled': state_manager.get_next_scheduled_transmission(device_id)
            })
        else:
            _debug("state_manager.start_automatic_transmission returned False")
            return jsonify({'error': 'Failed to start automatic transmission. Check logs for details.'}), 500
    except Exception as e:
        logging.error(f"Error in start_transmission endpoint: {e}")
        try:
            debug_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'transmissions_debug.log')
            with open(debug_path, 'a', encoding='utf-8') as f:
                f.write(f"[start_transmission][exception] {e}\n")
        except Exception:
            pass
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@transmissions_bp.route('/api/devices/<int:device_id>/pause-transmission', methods=['POST'])
def pause_transmission(device_id):
    """Pausar transmisión automática"""
    state_manager = get_state_manager()
    
    if state_manager.pause_transmission(device_id):
        device = Device.get_by_id(device_id)
        device.update_transmission_config(enabled=False)
        
        return jsonify({
            'message': 'Transmission paused',
            'current_state': state_manager.get_device_state(device_id),
            'current_row_index': device.current_row_index
        })
    else:
        return jsonify({'error': 'Cannot pause transmission'}), 400

@transmissions_bp.route('/api/devices/<int:device_id>/resume-transmission', methods=['POST'])
def resume_transmission(device_id):
    """Reanudar transmisión automática"""
    state_manager = get_state_manager()
    
    if state_manager.resume_transmission(device_id):
        device = Device.get_by_id(device_id)
        device.update_transmission_config(enabled=True)
        
        return jsonify({
            'message': 'Transmission resumed',
            'current_state': state_manager.get_device_state(device_id),
            'current_row_index': device.current_row_index
        })
    else:
        return jsonify({'error': 'Cannot resume transmission'}), 400

@transmissions_bp.route('/api/devices/<int:device_id>/stop-transmission', methods=['POST'])
def stop_transmission(device_id):
    """Detener transmisión automática"""
    state_manager = get_state_manager()
    
    if state_manager.stop_transmission(device_id):
        device = Device.get_by_id(device_id)
        device.update_transmission_config(enabled=False)
        if device.device_type == 'Sensor':
            device.reset_sensor_position()
        
        return jsonify({
            'message': 'Transmission stopped',
            'current_state': state_manager.get_device_state(device_id),
            'current_row_index': device.current_row_index
        })
    else:
        return jsonify({'error': 'Cannot stop transmission'}), 400

@transmissions_bp.route('/api/transmissions/updates', methods=['GET'])
def get_transmissions_updates():
    """Endpoint placeholder para actualizaciones en tiempo real.
    La UI hace polling a este endpoint cuando no hay WebSocket disponible.
    De momento devolvemos una lista vacía para evitar 404 y errores en consola.
    Futuro: devolver eventos acumulados desde TransmissionStateManager o una cola.
    """
    return jsonify([]), 200

# Legacy endpoints for backward compatibility
@transmissions_bp.route('/api/devices/<int:device_id>/pause', methods=['POST'])
def pause_legacy(device_id):
    return pause_transmission(device_id)

@transmissions_bp.route('/api/devices/<int:device_id>/resume', methods=['POST'])
def resume_legacy(device_id):
    return resume_transmission(device_id)

@transmissions_bp.route('/api/devices/<int:device_id>/stop', methods=['POST'])
def stop_legacy(device_id):
    return stop_transmission(device_id)

@transmissions_bp.route('/api/devices/<int:device_id>/debug', methods=['GET'])
def debug_device(device_id):
    """Debug endpoint to diagnose device and connection issues"""
    try:
        # Check device
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Device not found', 'device_id': device_id}), 404
        
        # Check connection if selected
        connection = None
        connection_status = None
        if device.selected_connection_id:
            try:
                connection = Connection.get_by_id(device.selected_connection_id)
                if connection:
                    connection_status = {
                        'id': connection.id,
                        'name': connection.name,
                        'type': connection.type,
                        'is_active': connection.is_active,
                        'host': connection.host,
                        'port': connection.port
                    }
                else:
                    connection_status = {'error': f'Connection {device.selected_connection_id} not found'}
            except Exception as e:
                connection_status = {'error': f'Error loading connection: {str(e)}'}
        
        # Check CSV data
        csv_status = {
            'has_data': bool(device.csv_data),
            'parsed_ok': False,
            'row_count': 0
        }
        
        if device.csv_data:
            try:
                csv_content = device.get_csv_data_parsed()
                if csv_content and 'data' in csv_content:
                    csv_status['parsed_ok'] = True
                    csv_status['row_count'] = len(csv_content['data'])
            except Exception as e:
                csv_status['parse_error'] = str(e)
        
        return jsonify({
            'device_id': device_id,
            'device': {
                'id': device.id,
                'name': device.name,
                'reference': device.reference,
                'device_type': device.device_type,
                'transmission_frequency': device.transmission_frequency,
                'transmission_enabled': device.transmission_enabled,
                'current_row_index': device.current_row_index,
                'selected_connection_id': device.selected_connection_id,
                'include_device_id_in_payload': device.include_device_id_in_payload,
                'auto_reset_counter': getattr(device, 'auto_reset_counter', False)
            },
            'connection': connection_status,
            'csv_data': csv_status,
            'timestamp': os.times()
        })
        
    except Exception as e:
        logging.error(f"Error in debug endpoint for device {device_id}: {e}")
        return jsonify({
            'error': f'Debug failed: {str(e)}',
            'device_id': device_id
        }), 500
