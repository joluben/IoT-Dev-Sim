"""
Rutas API para gestión de proyectos.
Implementa endpoints CRUD y operaciones masivas para proyectos.
"""
from flask import Blueprint, request, jsonify
import logging
from ..models import Project, Device, Connection
from ..project_operations import ProjectOperationManager

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__)

# ============================================================================
# CRUD de Proyectos
# ============================================================================

@projects_bp.route('/api/projects', methods=['GET'])
def get_projects():
    """Listar todos los proyectos"""
    try:
        projects = Project.get_all()
        return jsonify([project.to_dict() for project in projects])
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects', methods=['POST'])
def create_project():
    """Crear nuevo proyecto"""
    try:
        data = request.get_json()
        
        # Validaciones
        if not data or not data.get('name'):
            return jsonify({'error': 'Nombre del proyecto requerido'}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Nombre del proyecto no puede estar vacío'}), 400
        
        if Project.name_exists(name):
            return jsonify({'error': 'Ya existe un proyecto con ese nombre'}), 400
        
        description = data.get('description', '').strip()
        
        project = Project.create(name, description if description else None)
        return jsonify(project.to_dict()), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Obtener proyecto específico"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        return jsonify(project.to_dict_detailed())
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Actualizar proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Validar y actualizar nombre si se proporciona
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Nombre del proyecto no puede estar vacío'}), 400
            
            if Project.name_exists(name, exclude_id=project_id):
                return jsonify({'error': 'Ya existe un proyecto con ese nombre'}), 400
        
        # Actualizar campos
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'description' in data:
            update_data['description'] = data['description'].strip() if data['description'] else None
        if 'is_active' in data:
            update_data['is_active'] = bool(data['is_active'])
        
        if update_data:
            project.update(**update_data)
        
        return jsonify(project.to_dict())
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Eliminar proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        # Parar transmisiones activas antes de eliminar
        if project.transmission_status in ['ACTIVE', 'PAUSED']:
            try:
                operation_manager = ProjectOperationManager()
                operation_manager.stop_project_transmission(project_id)
            except Exception as e:
                logger.warning(f"Error stopping transmissions before deleting project {project_id}: {e}")
        
        project.delete()
        return jsonify({'message': 'Proyecto eliminado correctamente'})
        
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ============================================================================
# Gestión de Dispositivos en Proyectos
# ============================================================================

@projects_bp.route('/api/projects/<int:project_id>/devices', methods=['GET'])
def get_project_devices(project_id):
    """Obtener dispositivos del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        devices = project.get_devices()
        return jsonify([device.to_dict() for device in devices])
        
    except Exception as e:
        logger.error(f"Error getting devices for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/devices', methods=['POST'])
def add_devices_to_project(project_id):
    """Agregar dispositivos al proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        data = request.get_json()
        if not data or 'device_ids' not in data:
            return jsonify({'error': 'device_ids requerido'}), 400
        
        device_ids = data['device_ids']
        if not isinstance(device_ids, list):
            return jsonify({'error': 'device_ids debe ser una lista'}), 400
        
        results = []
        for device_id in device_ids:
            try:
                device_id = int(device_id)
                device = Device.get_by_id(device_id)
                if not device:
                    results.append({
                        'device_id': device_id,
                        'status': 'FAILED',
                        'message': 'Dispositivo no encontrado'
                    })
                    continue
                
                if project.add_device(device_id):
                    results.append({
                        'device_id': device_id,
                        'device_name': device.name,
                        'status': 'SUCCESS',
                        'message': 'Dispositivo agregado al proyecto'
                    })
                else:
                    results.append({
                        'device_id': device_id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'Dispositivo ya pertenece al proyecto'
                    })
            except (ValueError, TypeError):
                results.append({
                    'device_id': device_id,
                    'status': 'FAILED',
                    'message': 'ID de dispositivo inválido'
                })
        
        return jsonify({'results': results})
        
    except Exception as e:
        logger.error(f"Error adding devices to project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/devices/<int:device_id>', methods=['DELETE'])
def remove_device_from_project(project_id, device_id):
    """Remover dispositivo del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        if project.remove_device(device_id):
            return jsonify({'message': 'Dispositivo removido del proyecto'})
        else:
            return jsonify({'error': 'Dispositivo no pertenece al proyecto'}), 400
            
    except Exception as e:
        logger.error(f"Error removing device {device_id} from project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/devices/unassigned', methods=['GET'])
def get_unassigned_devices():
    """Dispositivos sin proyecto asignado"""
    try:
        devices = Device.get_unassigned()
        return jsonify([device.to_dict() for device in devices])
    except Exception as e:
        logger.error(f"Error getting unassigned devices: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ============================================================================
# Control Masivo de Transmisiones
# ============================================================================

@projects_bp.route('/api/projects/<int:project_id>/start-transmission', methods=['POST'])
def start_project_transmission(project_id):
    """Iniciar transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        data = request.get_json() or {}
        connection_id = data.get('connection_id')  # Opcional: usar conexión específica
        
        # Validar conexión si se especifica
        if connection_id:
            connection = Connection.get_by_id(connection_id)
            if not connection:
                return jsonify({'error': 'Conexión no encontrada'}), 404
            if not connection.is_active:
                return jsonify({'error': 'Conexión no está activa'}), 400
        
        operation_manager = ProjectOperationManager()
        result = operation_manager.start_project_transmission(project_id, connection_id)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting transmission for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/pause-transmission', methods=['POST'])
def pause_project_transmission(project_id):
    """Pausar transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        operation_manager = ProjectOperationManager()
        result = operation_manager.pause_project_transmission(project_id)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error pausing transmission for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/resume-transmission', methods=['POST'])
def resume_project_transmission(project_id):
    """Reanudar transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        operation_manager = ProjectOperationManager()
        result = operation_manager.resume_project_transmission(project_id)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error resuming transmission for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/stop-transmission', methods=['POST'])
def stop_project_transmission(project_id):
    """Parar transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        operation_manager = ProjectOperationManager()
        result = operation_manager.stop_project_transmission(project_id)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error stopping transmission for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ============================================================================
# Historial y Estadísticas
# ============================================================================

@projects_bp.route('/api/projects/<int:project_id>/transmission-history', methods=['GET'])
def get_project_transmission_history(project_id):
    """Historial de transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validar parámetros
        if limit < 1 or limit > 1000:
            limit = 100
        if offset < 0:
            offset = 0
        
        operation_manager = ProjectOperationManager()
        history = operation_manager.get_project_transmission_history(project_id, limit, offset)
        
        return jsonify({
            'project_id': project_id,
            'project_name': project.name,
            'transmissions': history,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting transmission history for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/transmission-stats', methods=['GET'])
def get_project_transmission_stats(project_id):
    """Estadísticas de transmisiones del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        operation_manager = ProjectOperationManager()
        stats = operation_manager.get_project_transmission_stats(project_id)
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting transmission stats for project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@projects_bp.route('/api/projects/<int:project_id>/validate', methods=['GET'])
def validate_project_requirements(project_id):
    """Validar requerimientos de transmisión del proyecto"""
    try:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        issues = project.validate_transmission_requirements()
        
        return jsonify({
            'project_id': project_id,
            'project_name': project.name,
            'is_valid': len(issues) == 0,
            'issues': issues,
            'devices_count': project.get_devices_count()
        })
        
    except Exception as e:
        logger.error(f"Error validating project {project_id}: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500
