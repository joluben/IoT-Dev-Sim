from flask import Blueprint, request, jsonify
import os
from ..models import Connection, ConnectionTest
from ..connection_clients import ConnectionClientFactory
from ..pagination import PaginationHelper
from ..database import get_db_session
from ..sqlalchemy_models import ConnectionORM as SQLConnection
from ..optimized_queries import OptimizedQueries
import json

connections_bp = Blueprint('connections', __name__)

@connections_bp.route('/api/connections', methods=['GET'])
def get_connections():
    """Obtiene conexiones con paginación optimizada"""
    try:
        # Extract pagination parameters
        page, per_page = PaginationHelper.get_pagination_params(
            request.args, 
            default_per_page=20, 
            max_per_page=100
        )
        
        # Extract filter parameters
        search = request.args.get('search', '').strip()
        connection_type = request.args.get('type', '').strip()
        is_active = request.args.get('active')
        active_bool = None
        if is_active is not None:
            active_bool = is_active.lower() in ('true', '1', 'yes')
        
        # Use optimized query
        try:
            result = OptimizedQueries.get_connections_summary(
                page=page,
                per_page=per_page,
                search=search if search else None,
                connection_type=connection_type if connection_type else None,
                active=active_bool
            )
            
            # Format response for pagination compatibility
            return jsonify({
                'items': result['items'],
                'pagination': {
                    'page': result['page'],
                    'per_page': result['per_page'],
                    'total': result['total'],
                    'pages': result['pages']
                }
            })
            
        except Exception as optimized_error:
            # Fallback to legacy approach if optimized query fails
            connections = Connection.get_all()
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                connections = [c for c in connections if (
                    search_lower in c.name.lower() or
                    search_lower in c.type.lower() or
                    search_lower in c.host.lower()
                )]
            
            # Apply type filter
            if connection_type:
                connections = [c for c in connections if c.type == connection_type]
            
            # Apply active filter
            if active_bool is not None:
                connections = [c for c in connections if c.is_active == active_bool]
            
            # Manual pagination for legacy approach
            total = len(connections)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_connections = connections[start_idx:end_idx]
            
            return jsonify(PaginationHelper.create_pagination_response(
                items=[conn.to_dict() for conn in paginated_connections],
                total=total,
                page=page,
                per_page=per_page
            ))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections', methods=['POST'])
def create_connection():
    """Crea una nueva conexión"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['name', 'type', 'host', 'auth_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # Validar tipo de conexión
        if data['type'] not in ['MQTT', 'HTTPS']:
            return jsonify({'error': 'Tipo de conexión debe ser MQTT o HTTPS'}), 400
        
        # Validar tipo de autenticación
        if data['auth_type'] not in ['NONE', 'USER_PASS', 'TOKEN', 'API_KEY']:
            return jsonify({'error': 'Tipo de autenticación no válido'}), 400
        
        connection = Connection.create(
            name=data['name'],
            description=data.get('description', ''),
            type=data['type'],
            host=data['host'],
            port=data.get('port'),
            endpoint=data.get('endpoint', ''),
            auth_type=data['auth_type'],
            auth_config=data.get('auth_config'),
            connection_config=data.get('connection_config')
        )
        
        return jsonify(connection.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections/<int:connection_id>', methods=['GET'])
def get_connection(connection_id):
    """Obtiene una conexión específica"""
    try:
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        # Safe default: do NOT expose sensitive data.
        # Allow only if both env flag and query param are set (intencional for dev-only use).
        allow_sensitive = os.environ.get('ALLOW_SENSITIVE_CONNECTIONS', '').lower() in ('1', 'true', 'yes')
        include_sensitive_param = request.args.get('include_sensitive', 'false').lower() in ('1', 'true', 'yes')
        include_sensitive = allow_sensitive and include_sensitive_param
        
        return jsonify(connection.to_dict(include_sensitive=include_sensitive))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections/<int:connection_id>', methods=['PUT'])
def update_connection(connection_id):
    """Actualiza una conexión"""
    try:
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        data = request.get_json()
        
        # Validar tipo de conexión si se proporciona
        if 'type' in data and data['type'] not in ['MQTT', 'HTTPS']:
            return jsonify({'error': 'Tipo de conexión debe ser MQTT o HTTPS'}), 400
        
        # Validar tipo de autenticación si se proporciona
        if 'auth_type' in data and data['auth_type'] not in ['NONE', 'USER_PASS', 'TOKEN', 'API_KEY']:
            return jsonify({'error': 'Tipo de autenticación no válido'}), 400
        
        connection.update(**data)
        
        # Obtener conexión actualizada
        updated_connection = Connection.get_by_id(connection_id)
        return jsonify(updated_connection.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections/<int:connection_id>', methods=['DELETE'])
def delete_connection(connection_id):
    """Elimina una conexión"""
    try:
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        connection.delete()
        return jsonify({'message': 'Conexión eliminada correctamente'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections/<int:connection_id>/test', methods=['POST'])
def test_connection(connection_id):
    """Prueba una conexión"""
    try:
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        # Crear cliente y probar conexión
        client = ConnectionClientFactory.create_client(connection)
        result = client.test_connection()
        
        # Guardar resultado en historial
        test_result = 'SUCCESS' if result['success'] else 'FAILED'
        error_message = None if result['success'] else result['message']
        
        ConnectionTest.create(
            connection_id=connection_id,
            test_result=test_result,
            response_time=result['response_time'],
            error_message=error_message
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'response_time': 0,
            'message': f'Error interno: {str(e)}'
        }), 500

@connections_bp.route('/api/connections/<int:connection_id>/history', methods=['GET'])
def get_connection_history(connection_id):
    """Obtiene el historial de pruebas de una conexión"""
    try:
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        limit = request.args.get('limit', 10, type=int)
        tests = ConnectionTest.get_by_connection(connection_id, limit)
        
        return jsonify([test.to_dict() for test in tests])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@connections_bp.route('/api/connections/types', methods=['GET'])
def get_connection_types():
    """Obtiene los tipos de conexión disponibles"""
    return jsonify({
        'types': [
            {
                'value': 'MQTT',
                'label': 'MQTT (Mosquitto)',
                'description': 'Protocolo de mensajería ligero para IoT',
                'default_port': 1883,
                'fields': ['client_id', 'keep_alive', 'qos', 'retain', 'ssl']
            },
            {
                'value': 'HTTPS',
                'label': 'HTTPS REST API',
                'description': 'Servicios web RESTful sobre HTTP/HTTPS',
                'default_port': 443,
                'fields': ['method', 'timeout', 'verify_ssl', 'headers']
            }
        ]
    })

@connections_bp.route('/api/connections/auth-types', methods=['GET'])
def get_auth_types():
    """Obtiene los tipos de autenticación disponibles"""
    return jsonify({
        'auth_types': [
            {
                'value': 'NONE',
                'label': 'Sin Autenticación',
                'description': 'Para servicios públicos sin autenticación',
                'fields': []
            },
            {
                'value': 'USER_PASS',
                'label': 'Usuario y Contraseña',
                'description': 'Autenticación básica con credenciales',
                'fields': ['username', 'password']
            },
            {
                'value': 'TOKEN',
                'label': 'Token Bearer',
                'description': 'Autenticación por token JWT/OAuth',
                'fields': ['token', 'token_type']
            },
            {
                'value': 'API_KEY',
                'label': 'API Key',
                'description': 'Clave de API en header o query parameter',
                'fields': ['key', 'location', 'parameter_name']
            }
        ]
    })

@connections_bp.route('/api/devices/<int:device_id>/send/<int:connection_id>', methods=['POST'])
def send_device_data(device_id, connection_id):
    """Envía datos de dispositivo a través de una conexión"""
    try:
        from ..models import Device
        
        # Verificar que existan el dispositivo y la conexión
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        connection = Connection.get_by_id(connection_id)
        if not connection:
            return jsonify({'error': 'Conexión no encontrada'}), 404
        
        if not connection.is_active:
            return jsonify({'error': 'Conexión no está activa'}), 400
        
        # Obtener datos CSV del dispositivo
        csv_data = device.get_csv_data_parsed()
        if not csv_data:
            return jsonify({'error': 'El dispositivo no tiene datos CSV'}), 400
        
        # Preparar datos para envío
        payload = {
            'device_id': device.id,
            'device_reference': device.reference,
            'device_name': device.name,
            'timestamp': json.dumps(csv_data, default=str),
            'data': csv_data
        }
        
        # Crear cliente y enviar datos
        client = ConnectionClientFactory.create_client(connection)
        
        if connection.type == 'MQTT':
            topic = connection.endpoint or f"devices/{device.reference}"
            client.connect()
            client.publish(topic, payload)
            client.disconnect()
            message = f'Datos enviados via MQTT al topic: {topic}'
            
        elif connection.type == 'HTTPS':
            response = client.send_request(payload)
            message = f'Datos enviados via HTTPS (Status: {response.status_code})'
        
        return jsonify({
            'success': True,
            'message': message,
            'payload_size': len(json.dumps(payload))
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error enviando datos: {str(e)}'
        }), 500
