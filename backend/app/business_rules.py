"""
Business rules for transmission behavior and device management.
"""
from .models import Device, Connection
from .validators import ValidationError
import logging

logger = logging.getLogger(__name__)

class TransmissionBusinessRules:
    """Business rules for transmission operations."""
    
    MAX_CONCURRENT_TRANSMISSIONS_PER_DEVICE = 1
    MAX_GLOBAL_CONCURRENT_TRANSMISSIONS = 10
    
    @staticmethod
    def can_start_transmission(device_id):
        """Check if a device can start a new transmission."""
        # Check if device already has active transmission
        active_transmissions = TransmissionBusinessRules._get_active_transmissions()
        device_transmissions = [t for t in active_transmissions if t['device_id'] == device_id]
        
        if len(device_transmissions) >= TransmissionBusinessRules.MAX_CONCURRENT_TRANSMISSIONS_PER_DEVICE:
            return False, f"Device {device_id} already has maximum concurrent transmissions"
        
        # Check global transmission limit
        if len(active_transmissions) >= TransmissionBusinessRules.MAX_GLOBAL_CONCURRENT_TRANSMISSIONS:
            return False, "Maximum global concurrent transmissions reached"
        
        return True, None
    
    @staticmethod
    def _get_active_transmissions():
        """Get list of currently active transmissions."""
        # This would integrate with the scheduler to get active jobs
        from .scheduler import get_scheduler
        scheduler = get_scheduler()
        jobs = scheduler.get_scheduled_jobs()
        
        active_transmissions = []
        for job in jobs:
            if 'device_' in job['id']:
                # Extract device_id from job_id format: "device_{id}_connection_{id}"
                parts = job['id'].split('_')
                if len(parts) >= 2:
                    try:
                        device_id = int(parts[1])
                        active_transmissions.append({
                            'device_id': device_id,
                            'job_id': job['id'],
                            'next_run': job['next_run']
                        })
                    except ValueError:
                        continue
        
        return active_transmissions
    
    @staticmethod
    def should_auto_pause_sensor(device):
        """Check if a sensor should be auto-paused when completing all rows."""
        if device.device_type != 'Sensor':
            return False
        
        csv_data = device.get_csv_data_parsed()
        if not csv_data:
            return True  # Pause if no data
        
        data_rows = csv_data.get('data') or csv_data.get('json_preview', [])
        if device.current_row_index >= len(data_rows):
            logger.info(f"Sensor {device.id} completed all rows, should auto-pause")
            return True
        
        return False
    
    @staticmethod
    def apply_sensor_completion_rule(device):
        """Apply auto-pause rule when sensor completes all rows."""
        if TransmissionBusinessRules.should_auto_pause_sensor(device):
            # Reset position and disable transmission
            device.reset_sensor_position()
            device.transmission_enabled = False
            device.save()
            
            # Remove from scheduler
            from .scheduler import get_scheduler
            scheduler = get_scheduler()
            connections = Connection.get_all()
            for conn in connections:
                scheduler.unschedule_device_transmission(device.id, conn.id)
            
            logger.info(f"Auto-paused sensor {device.id} after completing all rows")
            return True
        
        return False
    
    @staticmethod
    def validate_frequency_by_device_type(device_type, frequency):
        """Validate transmission frequency based on device type."""
        if device_type == 'Sensor':
            # Sensors should have more frequent transmissions (min 1 second)
            if frequency < 1:
                raise ValidationError("Sensor devices must have frequency of at least 1 second")
            if frequency > 3600:  # 1 hour max for sensors
                raise ValidationError("Sensor devices should not exceed 1 hour frequency")
        
        elif device_type == 'WebApp':
            # WebApps can have less frequent transmissions (min 60 seconds)
            if frequency < 60:
                raise ValidationError("WebApp devices must have frequency of at least 60 seconds")
            if frequency > 86400:  # 24 hours max
                raise ValidationError("WebApp devices should not exceed 24 hour frequency")
        
        return True

class DeviceLifecycleRules:
    """Business rules for device lifecycle management."""
    
    @staticmethod
    def on_device_created(device):
        """Apply rules when a device is created."""
        # Set default transmission configuration
        device.device_type = device.device_type or 'WebApp'
        device.transmission_frequency = device.transmission_frequency or 3600
        device.transmission_enabled = False
        device.current_row_index = 0
        device.save()
        
        logger.info(f"Applied creation rules for device {device.id}")
    
    @staticmethod
    def on_device_updated(device, old_values=None):
        """Apply rules when a device is updated."""
        # If device type changed, validate frequency
        if old_values and old_values.get('device_type') != device.device_type:
            try:
                TransmissionBusinessRules.validate_frequency_by_device_type(
                    device.device_type, 
                    device.transmission_frequency
                )
            except ValidationError:
                # Reset to default frequency for new device type
                if device.device_type == 'Sensor':
                    device.transmission_frequency = 60  # 1 minute default for sensors
                else:
                    device.transmission_frequency = 3600  # 1 hour default for webapps
                device.save()
        
        # If transmission was enabled, update scheduler
        if device.transmission_enabled:
            from .scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.update_device_schedule(device.id)
        
        logger.info(f"Applied update rules for device {device.id}")
    
    @staticmethod
    def on_csv_uploaded(device):
        """Apply rules when CSV data is uploaded to a device."""
        # Reset sensor position when new CSV is uploaded
        if device.device_type == 'Sensor':
            device.reset_sensor_position()
        
        # Validate data availability
        csv_data = device.get_csv_data_parsed()
        if not csv_data or not csv_data.get('data'):
            logger.warning(f"Invalid CSV data uploaded to device {device.id}")
            return False
        
        logger.info(f"Applied CSV upload rules for device {device.id}")
        return True

class ConnectionLifecycleRules:
    """Business rules for connection lifecycle management."""
    
    @staticmethod
    def on_connection_deactivated(connection_id):
        """Apply rules when a connection is deactivated."""
        # Remove all scheduled transmissions using this connection
        from .scheduler import get_scheduler
        scheduler = get_scheduler()
        
        devices = Device.get_all()
        for device in devices:
            scheduler.unschedule_device_transmission(device.id, connection_id)
        
        logger.info(f"Removed scheduled transmissions for deactivated connection {connection_id}")
    
    @staticmethod
    def on_connection_activated(connection_id):
        """Apply rules when a connection is activated."""
        # Schedule transmissions for all enabled devices
        from .scheduler import get_scheduler
        scheduler = get_scheduler()
        
        devices = Device.get_all()
        enabled_devices = [d for d in devices if d.transmission_enabled]
        
        for device in enabled_devices:
            scheduler.schedule_device_transmission(
                device.id, 
                connection_id, 
                device.transmission_frequency
            )
        
        logger.info(f"Scheduled transmissions for activated connection {connection_id}")

def apply_transmission_rules(device, connection, operation='transmit'):
    """Apply all relevant business rules for a transmission operation."""
    try:
        # Check transmission limits
        can_transmit, error = TransmissionBusinessRules.can_start_transmission(device.id)
        if not can_transmit:
            return False, error
        
        # Check sensor completion
        if device.device_type == 'Sensor':
            if TransmissionBusinessRules.should_auto_pause_sensor(device):
                TransmissionBusinessRules.apply_sensor_completion_rule(device)
                return False, "Sensor has completed all rows and was auto-paused"
        
        # Validate frequency
        TransmissionBusinessRules.validate_frequency_by_device_type(
            device.device_type, 
            device.transmission_frequency
        )
        
        return True, None
        
    except ValidationError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Error applying transmission rules: {e}")
        return False, f"Business rule error: {str(e)}"
