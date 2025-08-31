from flask import Blueprint, request, jsonify
from ..models import Device

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
    """Obtener todos los dispositivos"""
    try:
        devices = Device.get_all()
        return jsonify([device.to_dict() for device in devices])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
