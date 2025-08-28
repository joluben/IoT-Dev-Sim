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
