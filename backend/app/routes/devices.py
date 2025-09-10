from flask import Blueprint, request, jsonify
from ..models import Device
from ..pagination import PaginationHelper
from ..database import get_db_session
from ..sqlalchemy_models import DeviceORM as SQLDevice
from ..optimized_queries import OptimizedQueries

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/devices', methods=['POST'])
def create_device():
    """Crear un nuevo dispositivo"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        device = Device.create(
            name=data['name'],
            description=data.get('description', '')
        )
        
        return jsonify(device.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/devices', methods=['GET'])
def get_devices():
    """Obtener dispositivos con paginación optimizada"""
    try:
        # Extract pagination parameters
        page, per_page = PaginationHelper.get_pagination_params(
            request.args, 
            default_per_page=20, 
            max_per_page=100
        )
        
        # Extract filter parameters
        search = request.args.get('search', '').strip()
        device_type = request.args.get('type', '').strip()
        
        # Use optimized query
        try:
            result = OptimizedQueries.get_devices_summary(
                page=page,
                per_page=per_page,
                search=search if search else None,
                device_type=device_type if device_type else None
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
            devices = Device.get_all()
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                devices = [d for d in devices if (
                    search_lower in d.name.lower() or
                    search_lower in d.reference.lower() or
                    search_lower in (d.description or '').lower()
                )]
            
            # Apply type filter
            if device_type:
                devices = [d for d in devices if d.device_type == device_type]
            
            # Manual pagination for legacy approach
            total = len(devices)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_devices = devices[start_idx:end_idx]
            
            return jsonify(PaginationHelper.create_pagination_response(
                items=[device.to_dict() for device in paginated_devices],
                total=total,
                page=page,
                per_page=per_page
            ))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/devices/unassigned', methods=['GET'])
def get_unassigned_devices():
    """Obtener dispositivos no asignados a proyectos (optimizado)"""
    try:
        # Use optimized query for better performance
        devices = OptimizedQueries.get_unassigned_devices_summary()
        return jsonify(devices)
    except Exception as e:
        # Fallback to legacy approach
        try:
            devices = Device.get_unassigned()
            return jsonify([device.to_dict() for device in devices])
        except Exception as fallback_error:
            return jsonify({'error': str(fallback_error)}), 500

@devices_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Obtener un dispositivo específico"""
    try:
        device = Device.get_by_id(device_id)
        
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        return jsonify(device.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/devices/<int:device_id>/duplicate', methods=['POST'])
def duplicate_device(device_id):
    """Duplicar un dispositivo n veces"""
    try:
        data = request.get_json()
        
        if not data or 'count' not in data:
            return jsonify({'error': 'El campo count es requerido'}), 400
        
        count = data['count']
        
        # Validar que count sea un número entero válido
        if not isinstance(count, int) or count < 1 or count > 50:
            return jsonify({'error': 'El número de duplicados debe estar entre 1 y 50'}), 400
        
        # Obtener dispositivo original para incluir en respuesta
        original_device = Device.get_by_id(device_id)
        if not original_device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        # Duplicar dispositivo
        duplicated_devices = Device.duplicate(device_id, count)
        
        # Preparar respuesta
        response = {
            'original_device_id': device_id,
            'original_device_name': original_device.name,
            'duplicates_created': len(duplicated_devices),
            'duplicated_devices': [device.to_dict() for device in duplicated_devices]
        }
        
        return jsonify(response), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Eliminar un dispositivo de forma permanente"""
    try:
        # Verificar que el dispositivo existe
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        # TODO: Detener transmisiones activas y schedulers relacionados
        # TODO: Desvincular de proyectos y conexiones
        
        # Eliminar dispositivo
        success = Device.delete(device_id)
        
        if success:
            return jsonify({'deleted': True, 'device_id': device_id}), 200
        else:
            return jsonify({'error': 'No se pudo eliminar el dispositivo'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
