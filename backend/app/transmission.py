from .models import Device, Connection
from .database import execute_insert, execute_query
from .connection_clients import ConnectionClientFactory
from datetime import datetime, timedelta
import threading
import time
import json

class TransmissionManager:
    """Gestiona la ejecución y el registro de las transmisiones de datos."""

    def transmit_device_data(self, device, connection):
        """Ejecuta la transmisión de datos según el tipo de dispositivo."""
        data_to_send = device.get_transmission_data()
        if not data_to_send:
            self.log_transmission(device.id, connection.id, None, 'FAILED', error_message='No data to send')
            return False

        client = self._get_client_for_connection(connection)
        if not client:
            self.log_transmission(device.id, connection.id, data_to_send, 'FAILED', error_message='Unsupported connection type')
            return False

        try:
            success, response = client.send(data_to_send)
            status = 'SUCCESS' if success else 'FAILED'
            self.log_transmission(device.id, connection.id, data_to_send, status, response_data=str(response))
            if success and device.device_type == 'Sensor':
                device.advance_sensor_row()
            device.update_last_transmission()
            return success
        except Exception as e:
            self.log_transmission(device.id, connection.id, data_to_send, 'FAILED', error_message=str(e))
            return False

    def _get_client_for_connection(self, connection):
        """Retorna el cliente apropiado para el tipo de conexión."""
        return ConnectionClientFactory.create_client(connection)

    def log_transmission(self, device_id, connection_id, data_sent, status, response_data=None, error_message=None):
        """Registra el resultado de una transmisión en la base de datos."""
        transmission_type = 'FULL_CSV'
        row_index = None

        # Con el nuevo formato, el payload puede ser:
        # - lista de filas (FULL_CSV para WebApp)
        # - una sola fila (dict) para Sensor (SINGLE_ROW)
        try:
            payload = json.loads(data_sent) if isinstance(data_sent, str) else data_sent
            if isinstance(payload, list):
                transmission_type = 'FULL_CSV'
            elif isinstance(payload, dict):
                transmission_type = 'SINGLE_ROW'
        except (json.JSONDecodeError, TypeError):
            # Mantener defaults si no se puede parsear
            pass
        
        execute_insert(
            'INSERT INTO device_transmissions (device_id, connection_id, transmission_type, data_sent, row_index, status, response_data, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [device_id, connection_id, transmission_type, json.dumps(data_sent), row_index, status, response_data, error_message]
        )

    @staticmethod
    def get_transmission_history(device_id, limit=20):
        """Obtiene el historial de transmisiones para un dispositivo."""
        rows = execute_query('SELECT * FROM device_transmissions WHERE device_id = ? ORDER BY transmission_time DESC LIMIT ?', [device_id, limit])
        return [dict(row) for row in rows]


class TransmissionScheduler:
    """Programa y gestiona las transmisiones automáticas de dispositivos."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.active_schedules = {}
            self.scheduler_thread = threading.Thread(target=self._run, daemon=True)
            self.initialized = True
            self.scheduler_thread.start()

    def _run(self):
        """Ciclo principal del planificador que se ejecuta en un hilo separado."""
        while True:
            now = datetime.utcnow()
            for (device_id, connection_id), schedule in list(self.active_schedules.items()):
                if schedule['is_active'] and now >= schedule['next_execution']:
                    device = Device.get_by_id(device_id)
                    connection = Connection.get_by_id(connection_id)
                    if device and connection and device.transmission_enabled:
                        manager = TransmissionManager()
                        manager.transmit_device_data(device, connection)
                        schedule['next_execution'] = now + timedelta(seconds=device.transmission_frequency)
                    else:
                        # Si el dispositivo o la conexión ya no existen, se desactiva
                        schedule['is_active'] = False
            time.sleep(1) # Revisa cada segundo

    def schedule_device_transmission(self, device_id, connection_id):
        """Activa o actualiza la programación de un dispositivo."""
        device = Device.get_by_id(device_id)
        if not device or not device.transmission_enabled:
            self.unschedule_device_transmission(device_id, connection_id)
            return

        schedule_key = (device_id, connection_id)
        self.active_schedules[schedule_key] = {
            'is_active': True,
            'next_execution': datetime.utcnow() + timedelta(seconds=device.transmission_frequency)
        }

    def unschedule_device_transmission(self, device_id, connection_id):
        """Desactiva la programación de un dispositivo."""
        schedule_key = (device_id, connection_id)
        if schedule_key in self.active_schedules:
            self.active_schedules[schedule_key]['is_active'] = False

    def get_scheduled_transmissions(self):
        """Retorna una lista de las próximas transmisiones programadas."""
        return self.active_schedules
