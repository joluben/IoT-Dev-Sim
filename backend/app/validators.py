"""
Validaciones y reglas de negocio para el sistema de transmisión de dispositivos.
"""

class ValidationError(Exception):
    """Excepción personalizada para errores de validación."""
    pass

class TransmissionValidator:
    """Validador para configuraciones y operaciones de transmisión."""
    
    MIN_FREQUENCY = 1  # 1 segundo mínimo
    MAX_FREQUENCY = 86400  # 24 horas máximo
    VALID_DEVICE_TYPES = ['WebApp', 'Sensor']
    
    @staticmethod
    def validate_device_type(device_type):
        """Valida que el tipo de dispositivo sea válido."""
        if device_type not in TransmissionValidator.VALID_DEVICE_TYPES:
            raise ValidationError(f"Tipo de dispositivo inválido. Debe ser uno de: {', '.join(TransmissionValidator.VALID_DEVICE_TYPES)}")
        return True
    
    @staticmethod
    def validate_transmission_frequency(frequency):
        """Valida que la frecuencia de transmisión esté en el rango permitido."""
        if not isinstance(frequency, int) or frequency < TransmissionValidator.MIN_FREQUENCY or frequency > TransmissionValidator.MAX_FREQUENCY:
            raise ValidationError(f"Frecuencia de transmisión debe estar entre {TransmissionValidator.MIN_FREQUENCY} y {TransmissionValidator.MAX_FREQUENCY} segundos")
        return True
    
    @staticmethod
    def validate_device_has_data(device):
        """Valida que el dispositivo tenga datos CSV para transmitir."""
        if not device.csv_data:
            raise ValidationError("El dispositivo no tiene datos CSV cargados para transmitir")
        
        csv_content = device.get_csv_data_parsed()
        if not csv_content or 'data' not in csv_content or not csv_content['data']:
            raise ValidationError("Los datos CSV del dispositivo están vacíos o son inválidos")
        
        return True
    
    @staticmethod
    def validate_sensor_position(device):
        """Valida que un sensor tenga una posición válida para transmitir."""
        if device.device_type != 'Sensor':
            return True
        
        csv_content = device.get_csv_data_parsed()
        if not csv_content or 'data' not in csv_content:
            raise ValidationError("Sensor no tiene datos CSV válidos")
        
        data_rows = csv_content['data']
        if device.current_row_index >= len(data_rows):
            raise ValidationError(f"Sensor ha alcanzado el final de los datos (fila {device.current_row_index} de {len(data_rows)})")
        
        return True
    
    @staticmethod
    def validate_connection_active(connection):
        """Valida que la conexión esté activa y disponible."""
        if not connection:
            raise ValidationError("Conexión no encontrada")
        
        # El modelo usa booleano `is_active` en lugar de `status`
        if not getattr(connection, 'is_active', False):
            raise ValidationError(f"La conexión '{connection.name}' no está activa")
        
        return True
    
    @staticmethod
    def validate_transmission_config(device_type, frequency, enabled):
        """Valida una configuración completa de transmisión."""
        if device_type is not None:
            TransmissionValidator.validate_device_type(device_type)
        
        if frequency is not None:
            TransmissionValidator.validate_transmission_frequency(frequency)
        
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("El estado de transmisión habilitada debe ser verdadero o falso")
        
        return True

class DeviceValidator:
    """Validador para operaciones de dispositivos."""
    
    @staticmethod
    def validate_device_name(name):
        """Valida el nombre del dispositivo."""
        if not name or not name.strip():
            raise ValidationError("El nombre del dispositivo es obligatorio")
        
        if len(name.strip()) < 2:
            raise ValidationError("El nombre del dispositivo debe tener al menos 2 caracteres")
        
        if len(name.strip()) > 100:
            raise ValidationError("El nombre del dispositivo no puede exceder 100 caracteres")
        
        return True
    
    @staticmethod
    def validate_device_description(description):
        """Valida la descripción del dispositivo."""
        if description and len(description) > 500:
            raise ValidationError("La descripción del dispositivo no puede exceder 500 caracteres")
        
        return True

class ConnectionValidator:
    """Validador para operaciones de conexiones."""
    
    VALID_CONNECTION_TYPES = ['MQTT', 'HTTPS']
    VALID_AUTH_TYPES = ['NONE', 'USER_PASS', 'TOKEN', 'API_KEY']
    
    @staticmethod
    def validate_connection_type(conn_type):
        """Valida el tipo de conexión."""
        if conn_type not in ConnectionValidator.VALID_CONNECTION_TYPES:
            raise ValidationError(f"Tipo de conexión inválido. Debe ser uno de: {', '.join(ConnectionValidator.VALID_CONNECTION_TYPES)}")
        return True
    
    @staticmethod
    def validate_auth_type(auth_type):
        """Valida el tipo de autenticación."""
        if auth_type not in ConnectionValidator.VALID_AUTH_TYPES:
            raise ValidationError(f"Tipo de autenticación inválido. Debe ser uno de: {', '.join(ConnectionValidator.VALID_AUTH_TYPES)}")
        return True
    
    @staticmethod
    def validate_host(host):
        """Valida el host de la conexión."""
        if not host or not host.strip():
            raise ValidationError("El host es obligatorio")
        
        # Validación básica de formato de host
        host = host.strip()
        if len(host) < 3 or len(host) > 255:
            raise ValidationError("El host debe tener entre 3 y 255 caracteres")
        
        return True
    
    @staticmethod
    def validate_port(port):
        """Valida el puerto de la conexión."""
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ValidationError("El puerto debe ser un número entre 1 y 65535")
        return True

def validate_transmission_request(device, connection):
    """Valida una solicitud completa de transmisión."""
    try:
        TransmissionValidator.validate_device_has_data(device)
        TransmissionValidator.validate_sensor_position(device)
        TransmissionValidator.validate_connection_active(connection)
        return True, None
    except ValidationError as e:
        return False, str(e)

def validate_device_creation(name, description=None):
    """Valida los datos para crear un dispositivo."""
    try:
        DeviceValidator.validate_device_name(name)
        DeviceValidator.validate_device_description(description)
        return True, None
    except ValidationError as e:
        return False, str(e)

def validate_transmission_config_update(device_type=None, frequency=None, enabled=None):
    """Valida una actualización de configuración de transmisión."""
    try:
        TransmissionValidator.validate_transmission_config(device_type, frequency, enabled)
        return True, None
    except ValidationError as e:
        return False, str(e)
