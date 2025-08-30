import secrets
import string
import json
from datetime import datetime
from cryptography.fernet import Fernet
import os
import base64
from .database import execute_query, execute_insert

class Device:
    DEVICE_TYPES = ['WebApp', 'Sensor']

    def __init__(self, id=None, reference=None, name=None, description=None, csv_data=None, created_at=None,
                 device_type='WebApp', transmission_frequency=3600, transmission_enabled=False,
                 current_row_index=0, last_transmission=None, selected_connection_id=None):
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
        """Obtiene todos los dispositivos"""
        rows = execute_query('SELECT * FROM devices ORDER BY created_at DESC')
        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls, device_id):
        """Obtiene un dispositivo por ID"""
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
            selected_connection_id=get_value('selected_connection_id', None)
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
            'selected_connection_id': self.selected_connection_id
        }

    def get_transmission_data(self):
        """Retorna datos formateados para la transmisión según el tipo de dispositivo."""
        if self.device_type == 'WebApp':
            return self._get_full_csv_data()
        elif self.device_type == 'Sensor':
            return self._get_next_row_data()
        return None

    def _get_full_csv_data(self):
        """Prepara el payload para un dispositivo WebApp (todo el CSV)."""
        csv_content = self.get_csv_data_parsed()
        if not csv_content:
            return None
        # Fallback: usar 'json_preview' si 'data' no está presente
        data_rows = csv_content.get('data')
        if data_rows is None and 'json_preview' in csv_content:
            data_rows = csv_content.get('json_preview')
        if data_rows is None:
            return None
        return {
            "device_id": self.reference,
            "device_name": self.name,
            "device_type": self.device_type,
            "transmission_timestamp": datetime.utcnow().isoformat() + 'Z',
            "data_count": len(data_rows),
            "data": data_rows
        }

    def _get_next_row_data(self):
        """Prepara el payload para un dispositivo Sensor (siguiente fila)."""
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

        row_data = data_rows[self.current_row_index]
        row_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        return {
            "device_id": self.reference,
            "device_name": self.name,
            "device_type": self.device_type,
            "transmission_timestamp": row_data['timestamp'],
            "row_index": self.current_row_index,
            "data": row_data
        }

    def update_transmission_config(self, device_type=None, frequency=None, enabled=None, connection_id=None):
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


class EncryptionManager:
    """Gestor de encriptación para credenciales sensibles"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Obtiene o crea la clave de encriptación"""
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
        self.encryption_manager = EncryptionManager()

    @classmethod
    def create(cls, name, description, type, host, port, endpoint, auth_type, 
               auth_config=None, connection_config=None):
        """Crea una nueva conexión"""
        instance = cls()
        
        # Encriptar datos sensibles en auth_config
        encrypted_auth_config = None
        if auth_config:
            encrypted_auth_config = instance._encrypt_auth_config(auth_config)
        
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
                value = json.dumps(self._encrypt_auth_config(value))
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

    def _encrypt_auth_config(self, auth_config):
        """Encripta campos sensibles en auth_config"""
        if not auth_config:
            return None
            
        encrypted_config = auth_config.copy()
        
        # Campos que necesitan encriptación
        sensitive_fields = ['password', 'token', 'key']
        
        for field in sensitive_fields:
            if field in encrypted_config:
                encrypted_config[field] = self.encryption_manager.encrypt(encrypted_config[field])
        
        return encrypted_config

    def get_decrypted_auth_config(self):
        """Obtiene auth_config con datos desencriptados"""
        if not self.auth_config:
            return None
            
        config = json.loads(self.auth_config)
        decrypted_config = config.copy()
        
        # Campos que necesitan desencriptación
        sensitive_fields = ['password', 'token', 'key']
        
        for field in sensitive_fields:
            if field in decrypted_config:
                decrypted_config[field] = self.encryption_manager.decrypt(decrypted_config[field])
        
        return decrypted_config

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
            result['auth_config'] = self.get_decrypted_auth_config()
        
        if self.connection_config:
            result['connection_config'] = json.loads(self.connection_config)
        
        return result


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
