import secrets
import string
import json
from datetime import datetime
from cryptography.fernet import Fernet
import os
import base64
from .database import execute_query, execute_insert
from .orm_adapter import DeviceORMAdapter, ConnectionORMAdapter, ProjectORMAdapter, TransmissionORMAdapter
from .secrets_mgmt.secret_manager import get_secret_manager
from .secrets_mgmt import encrypt_credential, decrypt_credential

class Device:
    DEVICE_TYPES = ['WebApp', 'Sensor']

    def __init__(self, id=None, reference=None, name=None, description=None, csv_data=None, created_at=None,
                 device_type='WebApp', transmission_frequency=3600, transmission_enabled=False,
                 current_row_index=0, last_transmission=None, selected_connection_id=None,
                 include_device_id_in_payload=False, auto_reset_counter=False):
        self.id = id
        self.reference = reference
        self.name = name
        self.description = description
        self.csv_data = csv_data
        self.created_at = created_at
        self.device_type = device_type
        self.transmission_frequency = transmission_frequency
        self.transmission_enabled = transmission_enabled
        self.current_row_index = current_row_index
        self.last_transmission = last_transmission
        self.selected_connection_id = selected_connection_id
        self.include_device_id_in_payload = include_device_id_in_payload
        self.auto_reset_counter = auto_reset_counter

    @staticmethod
    def generate_reference():
        """Genera una referencia alfanumérica única de 8 caracteres"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

    @classmethod
    def create(cls, name, description):
        """Crea un nuevo dispositivo"""
        reference = cls.generate_reference()
        
        # Verificar que la referencia sea única
        while cls.get_by_reference(reference):
            reference = cls.generate_reference()
        
        device_id = execute_insert(
            'INSERT INTO devices (reference, name, description) VALUES (?, ?, ?)',
            [reference, name, description]
        )
        
        return cls.get_by_id(device_id)

    @classmethod
    def get_all(cls):
        """Obtiene todos los dispositivos - optimized with SQLAlchemy"""
        try:
            # Use SQLAlchemy ORM adapter for better performance
            devices_data = DeviceORMAdapter.get_all()
            devices = []
            for device_data in devices_data:
                # Handle potential missing fields
                device_data = dict(device_data) if hasattr(device_data, 'keys') else device_data
                devices.append(cls(**device_data))
            return devices
        except Exception as e:
            # Fallback to legacy method
            rows = execute_query('SELECT * FROM devices ORDER BY created_at DESC')
            return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls, device_id):
        """Obtiene un dispositivo por ID - optimized with SQLAlchemy"""
        try:
            # Use SQLAlchemy ORM adapter for better performance
            device_data = DeviceORMAdapter.get_by_id(device_id)
            if device_data:
                device_data = dict(device_data) if hasattr(device_data, 'keys') else device_data
                return cls(**device_data)
            return None
        except Exception:
            # Fallback to legacy method
            rows = execute_query('SELECT * FROM devices WHERE id = ?', [device_id])
            return cls._from_row(rows[0]) if rows else None

    @classmethod
    def get_by_reference(cls, reference):
        """Obtiene un dispositivo por referencia"""
        rows = execute_query('SELECT * FROM devices WHERE reference = ?', [reference])
        return cls._from_row(rows[0]) if rows else None

    def update_csv_data(self, csv_data):
        """Actualiza los datos CSV del dispositivo"""
        execute_insert(
            'UPDATE devices SET csv_data = ? WHERE id = ?',
            [json.dumps(csv_data), self.id]
        )
        self.csv_data = json.dumps(csv_data)

    def get_csv_data_parsed(self):
        """Retorna los datos CSV parseados como dict"""
        return json.loads(self.csv_data) if self.csv_data else None

    @classmethod
    def _from_row(cls, row):
        """Crea una instancia de Device desde una fila de BD"""
        # sqlite3.Row no implementa dict.get; usamos acceso seguro por claves
        keys = row.keys()

        def get_value(key, default=None):
            return row[key] if key in keys and row[key] is not None else default

        return cls(
            id=row['id'],
            reference=row['reference'],
            name=row['name'],
            description=get_value('description', None),
            csv_data=get_value('csv_data', None),
            created_at=get_value('created_at', None),
            device_type=get_value('device_type', 'WebApp'),
            transmission_frequency=get_value('transmission_frequency', 3600),
            transmission_enabled=bool(get_value('transmission_enabled', False)),
            current_row_index=get_value('current_row_index', 0),
            last_transmission=get_value('last_transmission', None),
            selected_connection_id=get_value('selected_connection_id', None),
            include_device_id_in_payload=bool(get_value('include_device_id_in_payload', False)),
            auto_reset_counter=bool(get_value('auto_reset_counter', False))
        )

    def to_dict(self):
        """Convierte el dispositivo a diccionario para JSON"""
        return {
            'id': self.id,
            'reference': self.reference,
            'name': self.name,
            'description': self.description,
            'csv_data': self.get_csv_data_parsed(),
            'created_at': self.created_at,
            'device_type': self.device_type,
            'transmission_frequency': self.transmission_frequency,
            'transmission_enabled': self.transmission_enabled,
            'current_row_index': self.current_row_index,
            'last_transmission': self.last_transmission,
            'selected_connection_id': self.selected_connection_id,
            'include_device_id_in_payload': self.include_device_id_in_payload,
            'auto_reset_counter': self.auto_reset_counter
        }

    def get_transmission_data(self):
        """Retorna datos formateados para la transmisión según el tipo de dispositivo."""
        if self.device_type == 'WebApp':
            return self._get_full_csv_data()
        elif self.device_type == 'Sensor':
            return self._get_next_row_data()
        return None

    def _get_full_csv_data(self):
        """Prepara el payload para un dispositivo WebApp (todo el CSV) devolviendo solo filas CSV.
        Si include_device_id_in_payload=True, agrega 'device_id' a cada fila.
        """
        csv_content = self.get_csv_data_parsed()
        if not csv_content:
            return None
        # Fallback: usar 'json_preview' si 'data' no está presente
        data_rows = csv_content.get('data')
        if data_rows is None and 'json_preview' in csv_content:
            data_rows = csv_content.get('json_preview')
        if data_rows is None:
            return None
        # Clonar para no mutar self.csv_data
        result_rows = []
        for r in data_rows:
            row = dict(r)
            if self.include_device_id_in_payload:
                row['device_id'] = self.reference
            result_rows.append(row)
        return result_rows

    def _get_next_row_data(self):
        """Prepara el payload para un dispositivo Sensor (siguiente fila) devolviendo solo la fila CSV.
        Si include_device_id_in_payload=True, agrega 'device_id' a la fila.
        """
        csv_content = self.get_csv_data_parsed()
        if not csv_content:
            return None
        # Fallback: usar 'json_preview' si 'data' no está presente
        data_rows = csv_content.get('data')
        if data_rows is None and 'json_preview' in csv_content:
            data_rows = csv_content.get('json_preview')
        if data_rows is None:
            return None
        if self.current_row_index >= len(data_rows):
            return None  # No hay más filas para enviar

        row = dict(data_rows[self.current_row_index])
        row['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        if self.include_device_id_in_payload:
            row['device_id'] = self.reference
        return row

    def update_transmission_config(self, device_type=None, frequency=None, enabled=None, connection_id=None, include_device_id_in_payload=None, auto_reset_counter=None):
        """Actualiza la configuración de transmisión del dispositivo."""
        if device_type and device_type in self.DEVICE_TYPES:
            self.device_type = device_type
            execute_insert('UPDATE devices SET device_type = ? WHERE id = ?', [self.device_type, self.id])

        if frequency is not None:
            self.transmission_frequency = frequency
            execute_insert('UPDATE devices SET transmission_frequency = ? WHERE id = ?', [self.transmission_frequency, self.id])

        if enabled is not None:
            self.transmission_enabled = enabled
            execute_insert('UPDATE devices SET transmission_enabled = ? WHERE id = ?', [self.transmission_enabled, self.id])

        if connection_id is not None:
            # Persist selected connection for manual or scheduled transmissions
            self.selected_connection_id = connection_id
            execute_insert('UPDATE devices SET selected_connection_id = ? WHERE id = ?', [self.selected_connection_id, self.id])

        if include_device_id_in_payload is not None:
            self.include_device_id_in_payload = bool(include_device_id_in_payload)
            execute_insert('UPDATE devices SET include_device_id_in_payload = ? WHERE id = ?', [int(self.include_device_id_in_payload), self.id])

        if auto_reset_counter is not None:
            self.auto_reset_counter = bool(auto_reset_counter)
            execute_insert('UPDATE devices SET auto_reset_counter = ? WHERE id = ?', [int(self.auto_reset_counter), self.id])

    def advance_sensor_row(self):
        """Avanza el índice de la fila para dispositivos Sensor y actualiza la BD."""
        if self.device_type == 'Sensor':
            self.current_row_index += 1
            execute_insert('UPDATE devices SET current_row_index = ? WHERE id = ?', [self.current_row_index, self.id])

    def reset_sensor_position(self):
        """Reinicia el índice de la fila para dispositivos Sensor a 0."""
        self.current_row_index = 0
        execute_insert('UPDATE devices SET current_row_index = ? WHERE id = ?', [self.current_row_index, self.id])

    def update_last_transmission(self):
        """Actualiza el timestamp de la última transmisión."""
        self.last_transmission = datetime.utcnow()
        execute_insert('UPDATE devices SET last_transmission = ? WHERE id = ?', [self.last_transmission, self.id])

    @classmethod
    def get_unassigned(cls):
        """Obtiene dispositivos sin proyecto asignado"""
        rows = execute_query('''
            SELECT * FROM devices 
            WHERE current_project_id IS NULL 
            ORDER BY created_at DESC
        ''')
        return [cls._from_row(row) for row in rows]

    def has_active_connections(self):
        """Verifica si el dispositivo tiene conexiones activas disponibles"""
        if self.selected_connection_id:
            connection = Connection.get_by_id(self.selected_connection_id)
            return connection and connection.is_active
        return False

    def has_csv_data(self):
        """Verifica si el dispositivo tiene datos CSV cargados"""
        return bool(self.csv_data)

    def get_default_connection_id(self):
        """Obtiene el ID de la conexión por defecto del dispositivo"""
        return self.selected_connection_id

    @classmethod
    def duplicate(cls, device_id, count):
        """
        Duplica un dispositivo n veces
        Args:
            device_id: ID del dispositivo a duplicar
            count: Número de duplicados a crear
        Returns:
            Lista de dispositivos duplicados
        """
        # Validaciones
        if count < 1 or count > 50:
            raise ValueError("El número de duplicados debe estar entre 1 y 50")
        
        # Obtener dispositivo original
        original_device = cls.get_by_id(device_id)
        if not original_device:
            raise ValueError(f"Dispositivo con ID {device_id} no encontrado")
        
        duplicated_devices = []
        
        for i in range(1, count + 1):
            # Generar nueva referencia única
            new_reference = cls.generate_reference()
            while cls.get_by_reference(new_reference):
                new_reference = cls.generate_reference()
            
            # Generar nombre incremental
            new_name = f"{original_device.name} {i}"
            
            # Crear dispositivo duplicado
            duplicate_id = execute_insert('''
                INSERT INTO devices (
                    reference, name, description, csv_data, device_type,
                    transmission_frequency, transmission_enabled, current_row_index,
                    selected_connection_id, last_transmission, include_device_id_in_payload, auto_reset_counter
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                new_reference,
                new_name,
                original_device.description,
                original_device.csv_data,  # Copia completa del CSV
                original_device.device_type,
                original_device.transmission_frequency,
                original_device.transmission_enabled,
                0,  # Resetear current_row_index a 0
                original_device.selected_connection_id,
                None,  # Resetear last_transmission
                getattr(original_device, 'include_device_id_in_payload', False),
                getattr(original_device, 'auto_reset_counter', False)
            ])
            
            # Obtener el dispositivo duplicado y agregarlo a la lista
            duplicated_device = cls.get_by_id(duplicate_id)
            duplicated_devices.append(duplicated_device)
        
        return duplicated_devices

    @classmethod
    def delete(cls, device_id):
        """
        Elimina un dispositivo de forma permanente
        Args:
            device_id: ID del dispositivo a eliminar
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Verificar que el dispositivo existe
            device = cls.get_by_id(device_id)
            if not device:
                return False
            
            # TODO: Detener transmisiones activas y schedulers relacionados
            # TODO: Desvincular de proyectos (actualizar current_project_id a NULL)
            
            # Limpiar relaciones con proyectos
            execute_insert('DELETE FROM project_devices WHERE device_id = ?', [device_id])
            
            # Eliminar el dispositivo
            execute_insert('DELETE FROM devices WHERE id = ?', [device_id])
            
            return True
            
        except Exception as e:
            print(f"Error deleting device {device_id}: {e}")
            return False


class EncryptionManager:
    """Gestor de encriptación para credenciales sensibles"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Obtiene o crea la clave de encriptación.
        Prioriza ENCRYPTION_KEY desde variables de entorno (base64 de Fernet).
        Fallback a archivo local para desarrollo.
        """
        env_key = os.environ.get('ENCRYPTION_KEY')
        if env_key:
            # Asumimos que es una clave Fernet válida (base64 urlsafe de 32 bytes)
            try:
                return env_key.encode()
            except Exception:
                pass  # Fallback a archivo
        
        key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'encryption.key')
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt(self, data):
        """Encripta datos sensibles"""
        if not data:
            return None
        return base64.b64encode(self.cipher.encrypt(data.encode())).decode()
    
    def decrypt(self, encrypted_data):
        """Desencripta datos sensibles"""
        if not encrypted_data:
            return None
        return self.cipher.decrypt(base64.b64decode(encrypted_data.encode())).decode()


class Connection:
    CONNECTION_TYPES = ['MQTT', 'HTTPS', 'KAFKA']

    def __init__(self, id=None, name=None, description=None, type=None, host=None, 
                 port=None, endpoint=None, auth_type=None, auth_config=None, 
                 connection_config=None, is_active=True, created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.auth_config = auth_config
        self.connection_config = connection_config
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at
        # Use new SecretManager instead of legacy EncryptionManager
        self.secret_manager = get_secret_manager()

    @classmethod
    def create(cls, name, description, type, host, port, endpoint, auth_type, 
               auth_config=None, connection_config=None):
        """Crea una nueva conexión"""
        instance = cls()
        
        # Encrypt sensitive data in auth_config using new SecretManager
        encrypted_auth_config = None
        if auth_config:
            encrypted_auth_config = instance._encrypt_auth_config_secure(auth_config)
        
        connection_id = execute_insert('''
            INSERT INTO connections 
            (name, description, type, host, port, endpoint, auth_type, auth_config, connection_config, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [name, description, type, host, port, endpoint, auth_type, 
              json.dumps(encrypted_auth_config) if encrypted_auth_config else None,
              json.dumps(connection_config) if connection_config else None, True])
        
        return cls.get_by_id(connection_id)

    @classmethod
    def get_all(cls):
        """Obtiene todas las conexiones"""
        rows = execute_query('SELECT * FROM connections ORDER BY created_at DESC')
        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls, connection_id):
        """Obtiene una conexión por ID"""
        rows = execute_query('SELECT * FROM connections WHERE id = ?', [connection_id])
        return cls._from_row(rows[0]) if rows else None

    def update(self, **kwargs):
        """Actualiza la conexión"""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key == 'auth_config' and value:
                value = json.dumps(self._encrypt_auth_config_secure(value))
            elif key == 'connection_config' and value:
                value = json.dumps(value)
            
            fields.append(f"{key} = ?")
            values.append(value)
        
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE connections SET {', '.join(fields)} WHERE id = ?"
            values.append(self.id)
            execute_insert(query, values)

    def delete(self):
        """Elimina la conexión"""
        execute_insert('DELETE FROM connections WHERE id = ?', [self.id])

    def _encrypt_auth_config_secure(self, auth_config):
        """Encrypt sensitive fields in auth_config using SecretManager"""
        if not auth_config:
            return None
            
        encrypted_config = auth_config.copy()
        
        # Fields that need encryption
        sensitive_fields = ['password', 'token', 'key', 'secret', 'api_key', 'client_secret']
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                try:
                    # Use new SecretManager for encryption
                    encrypted_payload = encrypt_credential(encrypted_config[field])
                    encrypted_config[field] = encrypted_payload
                except Exception as e:
                    # Log error but don't expose sensitive data
                    import logging
                    logging.error(f"Failed to encrypt field {field} for connection")
                    raise RuntimeError("Failed to encrypt sensitive credential data")
        
        return encrypted_config

    def get_decrypted_auth_config(self):
        """Get auth_config with decrypted sensitive data"""
        if not self.auth_config:
            return None
            
        try:
            config = json.loads(self.auth_config)
            decrypted_config = config.copy()
            
            # Fields that need decryption
            sensitive_fields = ['password', 'token', 'key', 'secret', 'api_key', 'client_secret']
            
            for field in sensitive_fields:
                if field in decrypted_config and isinstance(decrypted_config[field], dict):
                    # Check if this is an encrypted payload from SecretManager
                    if 'data' in decrypted_config[field] and 'version' in decrypted_config[field]:
                        try:
                            decrypted_value = decrypt_credential(decrypted_config[field])
                            decrypted_config[field] = decrypted_value
                        except Exception as e:
                            # If decryption fails, try legacy format
                            decrypted_config[field] = self._decrypt_legacy_field(decrypted_config[field])
                    elif isinstance(decrypted_config[field], str):
                        # Handle legacy encrypted strings
                        decrypted_config[field] = self._decrypt_legacy_field(decrypted_config[field])
            
            return decrypted_config
            
        except Exception as e:
            import logging
            logging.error("Failed to decrypt auth_config (sensitive data not logged)")
            raise RuntimeError("Failed to decrypt credential data")

    def _decrypt_legacy_field(self, encrypted_value):
        """Decrypt legacy encrypted field using old EncryptionManager"""
        try:
            # Try legacy decryption for backward compatibility
            from cryptography.fernet import Fernet
            import base64
            import os
            
            # Get legacy key
            key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'encryption.key')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    legacy_key = f.read()
                cipher = Fernet(legacy_key)
                return cipher.decrypt(base64.b64decode(encrypted_value.encode())).decode()
            else:
                # If no legacy key, return masked value
                return '••••••'
        except Exception:
            return '••••••'

    def to_dict(self, include_sensitive=False):
        """Convierte la conexión a diccionario para JSON"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'endpoint': self.endpoint,
            'auth_type': self.auth_type,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        if include_sensitive:
            # Only in authorized contexts: return decrypted data
            result['auth_config'] = self.get_decrypted_auth_config()
        else:
            # Provide masked information for UI without exposing secrets
            if self.auth_config:
                try:
                    raw_cfg = json.loads(self.auth_config)
                    masked = {}
                    sensitive_fields = ['password', 'token', 'key', 'secret', 'api_key', 'client_secret']
                    
                    for k, v in (raw_cfg.items() if isinstance(raw_cfg, dict) else []):
                        if k in sensitive_fields and v:
                            masked[k] = '••••••'
                        else:
                            masked[k] = v if isinstance(v, (bool, int)) else (v if v is None else str(v)[:10] + '...' if len(str(v)) > 10 else v)
                    result['auth_config_masked'] = masked
                except Exception:
                    result['auth_config_masked'] = {'masked': True}

        if self.connection_config:
            result['connection_config'] = json.loads(self.connection_config)
        
        return result

    @classmethod
    def _from_row(cls, row):
        """Crea una instancia de Connection desde una fila de BD"""
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            type=row['type'],
            host=row['host'],
            port=row['port'],
            endpoint=row['endpoint'],
            auth_type=row['auth_type'],
            auth_config=row['auth_config'],
            connection_config=row['connection_config'],
            is_active=bool(row['is_active']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


class ConnectionTest:
    def __init__(self, id=None, connection_id=None, test_result=None, 
                 response_time=None, error_message=None, tested_at=None):
        self.id = id
        self.connection_id = connection_id
        self.test_result = test_result
        self.response_time = response_time
        self.error_message = error_message
        self.tested_at = tested_at

    @classmethod
    def create(cls, connection_id, test_result, response_time=None, error_message=None):
        """Crea un nuevo registro de prueba"""
        test_id = execute_insert('''
            INSERT INTO connection_tests 
            (connection_id, test_result, response_time, error_message)
            VALUES (?, ?, ?, ?)
        ''', [connection_id, test_result, response_time, error_message])
        
        return cls.get_by_id(test_id)

    @classmethod
    def get_by_connection(cls, connection_id, limit=10):
        """Obtiene el historial de pruebas de una conexión"""
        rows = execute_query('''
            SELECT * FROM connection_tests 
            WHERE connection_id = ? 
            ORDER BY tested_at DESC 
            LIMIT ?
        ''', [connection_id, limit])
        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls, test_id):
        """Obtiene una prueba por ID"""
        rows = execute_query('SELECT * FROM connection_tests WHERE id = ?', [test_id])
        return cls._from_row(rows[0]) if rows else None

    @classmethod
    def _from_row(cls, row):
        """Crea una instancia de ConnectionTest desde una fila de BD"""
        return cls(
            id=row['id'],
            connection_id=row['connection_id'],
            test_result=row['test_result'],
            response_time=row['response_time'],
            error_message=row['error_message'],
            tested_at=row['tested_at']
        )

    def to_dict(self):
        """Convierte la prueba a diccionario para JSON"""
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'test_result': self.test_result,
            'response_time': self.response_time,
            'error_message': self.error_message,
            'tested_at': self.tested_at
        }


class Project:
    def __init__(self, id=None, name=None, description=None, is_active=True, 
                 transmission_status='INACTIVE', created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.transmission_status = transmission_status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, name, description=None):
        """Crea un nuevo proyecto"""
        if cls.name_exists(name):
            raise ValueError("Ya existe un proyecto con ese nombre")
        
        project_id = execute_insert('''
            INSERT INTO projects (name, description, is_active, transmission_status)
            VALUES (?, ?, ?, ?)
        ''', [name, description, True, 'INACTIVE'])
        
        return cls.get_by_id(project_id)

    @classmethod
    def get_all(cls):
        """Obtiene todos los proyectos"""
        rows = execute_query('SELECT * FROM projects ORDER BY created_at DESC')
        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls, project_id):
        """Obtiene un proyecto por ID"""
        rows = execute_query('SELECT * FROM projects WHERE id = ?', [project_id])
        return cls._from_row(rows[0]) if rows else None

    @classmethod
    def name_exists(cls, name, exclude_id=None):
        """Verifica si ya existe un proyecto con el nombre dado"""
        query = 'SELECT COUNT(*) as count FROM projects WHERE name = ?'
        params = [name]
        
        if exclude_id:
            query += ' AND id != ?'
            params.append(exclude_id)
        
        result = execute_query(query, params)
        return result[0]['count'] > 0

    def update(self, name=None, description=None, is_active=None, transmission_status=None):
        """Actualiza el proyecto"""
        fields = []
        values = []
        
        if name is not None:
            if Project.name_exists(name, exclude_id=self.id):
                raise ValueError("Ya existe un proyecto con ese nombre")
            fields.append("name = ?")
            values.append(name)
            self.name = name
        
        if description is not None:
            fields.append("description = ?")
            values.append(description)
            self.description = description
        
        if is_active is not None:
            fields.append("is_active = ?")
            values.append(is_active)
            self.is_active = is_active
        
        if transmission_status is not None:
            fields.append("transmission_status = ?")
            values.append(transmission_status)
            self.transmission_status = transmission_status
        
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
            values.append(self.id)
            execute_insert(query, values)

    def delete(self):
        """Elimina el proyecto y desvincula todos los dispositivos"""
        # Las relaciones project_devices se eliminan automáticamente por CASCADE
        execute_insert('DELETE FROM projects WHERE id = ?', [self.id])

    def add_device(self, device_id):
        """Agregar dispositivo al proyecto"""
        if self.has_device(device_id):
            return False
        
        try:
            execute_insert('''
                INSERT INTO project_devices (project_id, device_id)
                VALUES (?, ?)
            ''', [self.id, device_id])
            
            # Actualizar current_project_id en el dispositivo
            execute_insert('''
                UPDATE devices SET current_project_id = ? WHERE id = ?
            ''', [self.id, device_id])
            
            return True
        except Exception:
            return False

    def remove_device(self, device_id):
        """Remover dispositivo del proyecto"""
        if not self.has_device(device_id):
            return False
        
        execute_insert('''
            DELETE FROM project_devices WHERE project_id = ? AND device_id = ?
        ''', [self.id, device_id])
        
        # Limpiar current_project_id en el dispositivo
        execute_insert('''
            UPDATE devices SET current_project_id = NULL WHERE id = ?
        ''', [device_id])
        
        return True

    def has_device(self, device_id):
        """Verificar si dispositivo pertenece al proyecto"""
        result = execute_query('''
            SELECT COUNT(*) as count FROM project_devices 
            WHERE project_id = ? AND device_id = ?
        ''', [self.id, device_id])
        return result[0]['count'] > 0

    def get_devices(self):
        """Obtener todos los dispositivos del proyecto"""
        rows = execute_query('''
            SELECT d.* FROM devices d
            INNER JOIN project_devices pd ON d.id = pd.device_id
            WHERE pd.project_id = ?
            ORDER BY pd.assigned_at DESC
        ''', [self.id])
        return [Device._from_row(row) for row in rows]

    def get_devices_count(self):
        """Obtener cantidad de dispositivos en el proyecto"""
        result = execute_query('''
            SELECT COUNT(*) as count FROM project_devices WHERE project_id = ?
        ''', [self.id])
        return result[0]['count']

    def validate_transmission_requirements(self):
        """Validar que dispositivos tengan conexiones configuradas"""
        issues = []
        devices = self.get_devices()
        
        for device in devices:
            # Verificar si tiene datos CSV
            if not device.csv_data:
                issues.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'issue': 'NO_CSV_DATA'
                })
            
            # Verificar si tiene conexión seleccionada
            if not device.selected_connection_id:
                issues.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'issue': 'NO_CONNECTION_SELECTED'
                })
            else:
                # Verificar si la conexión existe y está activa
                connection = Connection.get_by_id(device.selected_connection_id)
                if not connection or not connection.is_active:
                    issues.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'issue': 'INACTIVE_CONNECTION'
                    })
        
        return issues

    @classmethod
    def _from_row(cls, row):
        """Crea una instancia de Project desde una fila de BD"""
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            is_active=bool(row['is_active']),
            transmission_status=row['transmission_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self, include_devices=False):
        """Convierte el proyecto a diccionario para JSON"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'transmission_status': self.transmission_status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'devices_count': self.get_devices_count()
        }
        
        if include_devices:
            result['devices'] = [device.to_dict() for device in self.get_devices()]
        
        return result

    def to_dict_detailed(self):
        """Convierte el proyecto a diccionario detallado incluyendo dispositivos"""
        return self.to_dict(include_devices=True)
