"""
Sistema de gestión de operaciones masivas para proyectos.
Implementa la lógica de operaciones en lote definida en la Fase 8 del plan de implementación.
"""
import logging
from datetime import datetime
from .models import Project, Device, Connection
from .transmission import TransmissionManager
from .scheduler import get_scheduler
from .database import execute_query

logger = logging.getLogger(__name__)

class ProjectOperationManager:
    def __init__(self):
        self.transmission_manager = TransmissionManager()
        self.scheduler = get_scheduler()
    
    def start_project_transmission(self, project_id, connection_id=None):
        """Iniciar transmisión automática para todos los dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            raise ValueError("Proyecto no encontrado")
        
        # Verificar que el scheduler está disponible
        if not self.scheduler:
            logger.error("Scheduler not available - cannot start transmissions")
            raise RuntimeError("El sistema de transmisiones no está disponible. Verifica los logs del servidor.")
        
        devices = project.get_devices()
        if not devices:
            return {
                'total_devices': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'results': [],
                'message': 'No hay dispositivos en el proyecto'
            }
        
        results = []
        successful = 0
        failed = 0
        
        for device in devices:
            try:
                # Usar conexión específica o la primera disponible
                target_connection = connection_id or device.get_default_connection_id()
                
                if not target_connection:
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'No hay conexión configurada'
                    })
                    failed += 1
                    continue
                
                # Verificar que la conexión existe y está activa
                connection = Connection.get_by_id(target_connection)
                if not connection or not connection.is_active:
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'Conexión inactiva o no encontrada'
                    })
                    failed += 1
                    continue
                
                # Verificar que el dispositivo tiene datos CSV
                if not device.has_csv_data():
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'No hay datos CSV cargados'
                    })
                    failed += 1
                    continue
                
                # Actualizar configuración del dispositivo ANTES de programar
                # para que el scheduler encuentre transmission_enabled=True
                device.update_transmission_config(enabled=True, connection_id=target_connection)
                logger.info(f"Device {device.id} config updated: enabled=True, connection_id={target_connection}")
                
                # Iniciar transmisión para el dispositivo
                if self.scheduler:
                    logger.info(f"Scheduling transmission for device {device.id}, connection {target_connection}, freq {device.transmission_frequency}")
                    success = self.scheduler.schedule_transmission(
                        device.id, target_connection, device.transmission_frequency
                    )
                    logger.info(f"Schedule result for device {device.id}: {success}")
                    
                    if success:
                        # Actualizar configuración del dispositivo
                        # device.update_transmission_config(enabled=True, connection_id=target_connection)
                        
                        results.append({
                            'device_id': device.id,
                            'device_name': device.name,
                            'status': 'SUCCESS',
                            'message': 'Transmisión iniciada correctamente'
                        })
                        successful += 1
                    else:
                        results.append({
                            'device_id': device.id,
                            'device_name': device.name,
                            'status': 'FAILED',
                            'message': 'Error al programar transmisión'
                        })
                        failed += 1
                else:
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'Scheduler no disponible'
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error starting transmission for device {device.id}: {e}")
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'status': 'FAILED',
                    'message': str(e)
                })
                failed += 1
        
        # Actualizar estado del proyecto
        if successful > 0:
            project.update(transmission_status='ACTIVE')
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'operation': 'START_TRANSMISSION',
            'total_devices': len(devices),
            'successful_operations': successful,
            'failed_operations': failed,
            'results': results,
            'execution_time': datetime.utcnow().isoformat() + 'Z'
        }
    
    def pause_project_transmission(self, project_id):
        """Pausar transmisiones de todos los dispositivos del proyecto"""
        result = self._execute_bulk_operation(project_id, 'PAUSE')
        
        # Actualizar estado del proyecto si hay éxitos
        if result['successful_operations'] > 0:
            project = Project.get_by_id(project_id)
            if project:
                project.update(transmission_status='PAUSED')
        
        return result
    
    def resume_project_transmission(self, project_id):
        """Reanudar transmisiones de todos los dispositivos del proyecto"""
        result = self._execute_bulk_operation(project_id, 'RESUME')
        
        # Actualizar estado del proyecto si hay éxitos
        if result['successful_operations'] > 0:
            project = Project.get_by_id(project_id)
            if project:
                project.update(transmission_status='ACTIVE')
        
        return result
    
    def stop_project_transmission(self, project_id):
        """Parar transmisiones de todos los dispositivos del proyecto"""
        result = self._execute_bulk_operation(project_id, 'STOP')
        
        # Actualizar estado del proyecto
        project = Project.get_by_id(project_id)
        if project:
            project.update(transmission_status='INACTIVE')
        
        return result
    
    def _execute_bulk_operation(self, project_id, operation):
        """Ejecutar operación masiva en dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            raise ValueError("Proyecto no encontrado")
        
        devices = project.get_devices()
        if not devices:
            return {
                'project_id': project_id,
                'project_name': project.name,
                'operation': operation,
                'total_devices': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'results': [],
                'execution_time': datetime.utcnow().isoformat() + 'Z'
            }
        
        results = []
        successful = 0
        failed = 0
        
        for device in devices:
            try:
                success = False
                message = ""
                
                target_connection = device.get_default_connection_id()
                if not target_connection:
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'status': 'FAILED',
                        'message': 'No hay conexión configurada'
                    })
                    failed += 1
                    continue
                
                if self.scheduler:
                    if operation == 'PAUSE':
                        success = self.scheduler.pause_transmission(device.id, target_connection)
                        message = "Transmisión pausada" if success else "Error al pausar transmisión"
                        if success:
                            device.update_transmission_config(enabled=False)
                    elif operation == 'RESUME':
                        success = self.scheduler.resume_transmission(device.id, target_connection)
                        message = "Transmisión reanudada" if success else "Error al reanudar transmisión"
                        if success:
                            device.update_transmission_config(enabled=True)
                    elif operation == 'STOP':
                        success = self.scheduler.stop_transmission(device.id, target_connection)
                        message = "Transmisión detenida" if success else "Error al detener transmisión"
                        if success:
                            device.update_transmission_config(enabled=False)
                else:
                    message = "Scheduler no disponible"
                
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'status': 'SUCCESS' if success else 'FAILED',
                    'message': message
                })
                
                if success:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error executing {operation} for device {device.id}: {e}")
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'status': 'FAILED',
                    'message': str(e)
                })
                failed += 1
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'operation': operation,
            'total_devices': len(devices),
            'successful_operations': successful,
            'failed_operations': failed,
            'results': results,
            'execution_time': datetime.utcnow().isoformat() + 'Z'
        }
    
    def get_project_transmission_history(self, project_id, limit=100, offset=0):
        """Obtener historial de transmisiones de todos los dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            return []
        
        devices = project.get_devices()
        if not devices:
            return []
        
        device_ids = [device.id for device in devices]
        
        # Query para obtener transmisiones de todos los dispositivos del proyecto
        placeholders = ','.join(['?' for _ in device_ids])
        query = f'''
            SELECT dt.*, d.name as device_name, d.reference as device_reference,
                   c.name as connection_name
            FROM device_transmissions dt
            INNER JOIN devices d ON dt.device_id = d.id
            INNER JOIN connections c ON dt.connection_id = c.id
            WHERE dt.device_id IN ({placeholders})
            ORDER BY dt.transmission_time DESC
            LIMIT ? OFFSET ?
        '''
        
        params = device_ids + [limit, offset]
        rows = execute_query(query, params)
        
        history = []
        for row in rows:
            history.append({
                'id': row['id'],
                'device_id': row['device_id'],
                'device_name': row['device_name'],
                'device_reference': row['device_reference'],
                'connection_id': row['connection_id'],
                'connection_name': row['connection_name'],
                'transmission_type': row['transmission_type'],
                'status': row['status'],
                'transmission_time': row['transmission_time'],
                'error_message': row['error_message'],
                'row_index': row['row_index']
            })
        
        return history
    
    def get_project_transmission_stats(self, project_id):
        """Obtener estadísticas de transmisiones del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            return None
        
        devices = project.get_devices()
        if not devices:
            return {
                'project_id': project_id,
                'total_devices': 0,
                'total_transmissions': 0,
                'successful_transmissions': 0,
                'failed_transmissions': 0,
                'success_rate': 0.0
            }
        
        device_ids = [device.id for device in devices]
        placeholders = ','.join(['?' for _ in device_ids])
        
        # Estadísticas generales
        stats_query = f'''
            SELECT 
                COUNT(*) as total_transmissions,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_transmissions,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_transmissions
            FROM device_transmissions
            WHERE device_id IN ({placeholders})
        '''
        
        stats_result = execute_query(stats_query, device_ids)
        stats = stats_result[0] if stats_result else {}
        
        total = stats.get('total_transmissions', 0)
        successful = stats.get('successful_transmissions', 0)
        failed = stats.get('failed_transmissions', 0)
        
        return {
            'project_id': project_id,
            'total_devices': len(devices),
            'total_transmissions': total,
            'successful_transmissions': successful,
            'failed_transmissions': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0.0
        }
