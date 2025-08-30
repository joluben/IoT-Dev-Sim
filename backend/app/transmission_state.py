"""
Sistema de gestión de estados de transmisión para dispositivos.
Implementa la lógica de estados definida en la Fase 7 del plan de implementación.
"""
from .models import Device, Connection
from .scheduler import get_scheduler
import logging

logger = logging.getLogger(__name__)

class TransmissionStateManager:
    STATES = {
        'INACTIVE': 'inactive',      # Sin transmisión programada
        'ACTIVE': 'active',          # Transmisión automática activa
        'PAUSED': 'paused',          # Transmisión pausada temporalmente
        'MANUAL': 'manual'           # Transmisión manual en ejecución
    }
    
    def __init__(self):
        self.device_states = {}  # {device_id: state}
    
    def start_automatic_transmission(self, device_id, connection_id):
        """Inicia transmisión automática según frecuencia"""
        try:
            device = Device.get_by_id(device_id)
            if not device:
                logger.error(f"Device {device_id} not found")
                return False
                
            # Validar frecuencia
            if not device.transmission_frequency or device.transmission_frequency <= 0:
                logger.error(f"Invalid transmission frequency for device {device_id}: {device.transmission_frequency}")
                return False
                
            # Validar conexión
            connection = Connection.get_by_id(connection_id)
            if not connection:
                logger.error(f"Connection {connection_id} not found")
                return False
                
            if not getattr(connection, 'is_active', False):
                logger.error(f"Connection {connection_id} is not active")
                return False
                
            scheduler = get_scheduler()
            if not scheduler:
                logger.error("Scheduler not available")
                return False
                
            # Programar transmisión
            job_id = scheduler.schedule_transmission(device_id, connection_id, device.transmission_frequency)
            if job_id:
                self.device_states[device_id] = self.STATES['ACTIVE']
                logger.info(f"Transmisión automática iniciada para dispositivo {device_id}")
                return True
            else:
                logger.error(f"Failed to schedule transmission for device {device_id}")
                return False
        except Exception as e:
            logger.error(f"Error starting automatic transmission for device {device_id}: {e}")
            return False
    
    def pause_transmission(self, device_id):
        """Pausa transmisión automática manteniendo configuración"""
        if self.device_states.get(device_id) == self.STATES['ACTIVE']:
            # Obtener conexiones activas para pausar
            connections = Connection.get_all()
            active_connections = [conn for conn in connections if getattr(conn, 'is_active', False)]
            
            scheduler = get_scheduler()
            if scheduler:
                for connection in active_connections:
                    scheduler.pause_transmission(device_id, connection.id)
                
                self.device_states[device_id] = self.STATES['PAUSED']
                logger.info(f"Transmisión pausada para dispositivo {device_id}")
                return True
        return False
    
    def resume_transmission(self, device_id):
        """Reanuda transmisión automática desde punto de pausa"""
        if self.device_states.get(device_id) == self.STATES['PAUSED']:
            # Obtener conexiones activas para reanudar
            connections = Connection.get_all()
            active_connections = [conn for conn in connections if getattr(conn, 'is_active', False)]
            
            scheduler = get_scheduler()
            if scheduler:
                for connection in active_connections:
                    scheduler.resume_transmission(device_id, connection.id)
                
                self.device_states[device_id] = self.STATES['ACTIVE']
                logger.info(f"Transmisión reanudada para dispositivo {device_id}")
                return True
        return False
    
    def stop_transmission(self, device_id):
        """Detiene completamente la transmisión automática"""
        # Obtener conexiones activas para detener
        connections = Connection.get_all()
        active_connections = [conn for conn in connections if getattr(conn, 'is_active', False)]
        
        scheduler = get_scheduler()
        if scheduler:
            for connection in active_connections:
                scheduler.stop_transmission(device_id, connection.id)
            
            self.device_states[device_id] = self.STATES['INACTIVE']
            logger.info(f"Transmisión detenida para dispositivo {device_id}")
            return True
        return False
    
    def execute_manual_transmission(self, device_id, connection_id):
        """Ejecuta transmisión manual inmediata"""
        if self.can_execute_manual(device_id):
            # Cambio temporal de estado durante ejecución
            original_state = self.device_states.get(device_id, self.STATES['INACTIVE'])
            self.device_states[device_id] = self.STATES['MANUAL']
            
            try:
                # Ejecutar transmisión manual
                from .transmission import TransmissionManager
                device = Device.get_by_id(device_id)
                connection = Connection.get_by_id(connection_id)
                
                if not device or not connection:
                    return {'success': False, 'error': 'Device or connection not found'}
                
                transmission_manager = TransmissionManager()
                success = transmission_manager.transmit_device_data(device, connection)
                
                result = {
                    'success': success,
                    'device_id': device_id,
                    'connection_id': connection_id,
                    'message': 'Manual transmission completed' if success else 'Manual transmission failed'
                }
                
                return result
            except Exception as e:
                logger.error(f"Error en transmisión manual: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                # Restaurar estado original
                self.device_states[device_id] = original_state
        else:
            return {
                'success': False, 
                'error': 'Cannot execute manual transmission while automatic transmission is active or another manual is in progress',
                'current_state': self.get_device_state(device_id)
            }
    
    def can_execute_manual(self, device_id):
        """Verifica si se puede ejecutar transmisión manual"""
        current_state = self.get_device_state(device_id)
        # Permitir manual solo cuando NO esté activa la automática ni otra manual
        return current_state in (self.STATES['INACTIVE'], self.STATES['PAUSED'])
    
    def get_device_state(self, device_id):
        """Obtiene el estado actual del dispositivo"""
        # Verificar si hay jobs programados para determinar el estado real
        scheduler = get_scheduler()
        if scheduler:
            connections = Connection.get_all()
            active_connections = [conn for conn in connections if getattr(conn, 'is_active', False)]
            
            for connection in active_connections:
                job_status = scheduler.get_job_status(device_id, connection.id)
                if job_status.get('exists'):
                    # Hay un job programado, verificar si está activo
                    device = Device.get_by_id(device_id)
                    if device and device.transmission_enabled:
                        return self.STATES['ACTIVE']
                    else:
                        return self.STATES['PAUSED']
        
        return self.device_states.get(device_id, self.STATES['INACTIVE'])
    
    def get_available_actions(self, device_id):
        """Retorna las acciones disponibles según el estado actual"""
        state = self.get_device_state(device_id)
        
        actions = {
            'transmit_now': {
                # Permitir "Transmitir ahora" en INACTIVE o PAUSED
                'enabled': state in (self.STATES['INACTIVE'], self.STATES['PAUSED']),
                'visible': True
            },
            'start': {
                'enabled': state == self.STATES['INACTIVE'],
                'visible': state == self.STATES['INACTIVE']
            },
            'pause': {
                'enabled': state == self.STATES['ACTIVE'],
                'visible': state == self.STATES['ACTIVE']
            },
            'resume': {
                'enabled': state == self.STATES['PAUSED'],
                'visible': state == self.STATES['PAUSED']
            },
            'stop': {
                'enabled': state in [self.STATES['ACTIVE'], self.STATES['PAUSED']],
                'visible': state in [self.STATES['ACTIVE'], self.STATES['PAUSED']]
            }
        }
        
        return actions

    def get_last_transmission_time(self, device_id):
        """Obtiene el timestamp de la última transmisión"""
        device = Device.get_by_id(device_id)
        if device and hasattr(device, 'last_transmission'):
            return device.last_transmission
        return None
    
    def get_next_scheduled_transmission(self, device_id):
        """Obtiene el timestamp de la próxima transmisión programada"""
        scheduler = get_scheduler()
        if scheduler:
            connections = Connection.get_all()
            active_connections = [conn for conn in connections if getattr(conn, 'is_active', False)]
            
            for connection in active_connections:
                job_status = scheduler.get_job_status(device_id, connection.id)
                if job_status.get('exists') and job_status.get('next_run_time'):
                    return job_status['next_run_time']
        return None

# Instancia global del state manager
transmission_state_manager = None

def get_state_manager():
    """Retorna la instancia global del state manager."""
    global transmission_state_manager
    if transmission_state_manager is None:
        transmission_state_manager = TransmissionStateManager()
    return transmission_state_manager
