import paho.mqtt.client as mqtt
import requests
import json
import time
from datetime import datetime
import ssl


class MQTTClient:
    def __init__(self, connection_config, auth_config=None):
        self.connection_config = connection_config
        self.auth_config = auth_config or {}
        self.client = None
        self.connected = False
        
    def connect(self):
        """Establece conexión MQTT"""
        try:
            client_id = self.connection_config.get('client_id', f"devsim_{int(time.time())}")
            # Compatibilidad paho-mqtt v1 y v2
            # En v2, se debe indicar callback_api_version para usar las firmas legacy (VERSION1)
            if hasattr(mqtt, 'CallbackAPIVersion'):
                self.client = mqtt.Client(
                    client_id=client_id,
                    protocol=mqtt.MQTTv311,
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1
                )
            else:
                # v1.x no acepta callback_api_version
                self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            
            # Configurar autenticación si es necesaria
            if self.auth_config.get('username') and self.auth_config.get('password'):
                self.client.username_pw_set(
                    self.auth_config['username'], 
                    self.auth_config['password']
                )
            
            # Configurar SSL si está habilitado
            if self.connection_config.get('ssl', False):
                context = ssl.create_default_context()
                if self.connection_config.get('ca_cert_path'):
                    context.load_verify_locations(self.connection_config['ca_cert_path'])
                self.client.tls_set_context(context)
            
            # Configurar callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # Conectar
            host = self._sanitize_host(self.connection_config['host'])
            port = self.connection_config.get('port', 1883)
            keep_alive = self.connection_config.get('keep_alive', 60)
            
            self.client.connect(host, port, keep_alive)
            self.client.loop_start()
            
            # Esperar conexión
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            return self.connected
            
        except Exception as e:
            raise Exception(f"Error conectando MQTT: {str(e)}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexión"""
        if rc == 0:
            self.connected = True
        else:
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback de desconexión"""
        self.connected = False
    
    def publish(self, topic, message):
        """Publica un mensaje en el topic especificado"""
        if not self.connected:
            raise Exception("Cliente MQTT no conectado")
        
        qos = self.connection_config.get('qos', 1)
        retain = self.connection_config.get('retain', False)
        
        if isinstance(message, dict):
            message = json.dumps(message)
        
        result = self.client.publish(topic, message, qos=qos, retain=retain)
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"Error publicando mensaje: {result.rc}")
        
        return True

    def send(self, data):
        """Interfaz unificada para TransmissionManager: conecta, publica y desconecta.
        Usa connection_config['endpoint'] como topic por defecto.
        """
        topic = self.connection_config.get('endpoint') or self.connection_config.get('topic') or 'devices/data'
        try:
            connected = self.connect()
            if not connected:
                return False, 'MQTT not connected'
            self.publish(topic, data)
            self.disconnect()
            return True, f'Published to topic {topic}'
        except Exception as e:
            try:
                self.disconnect()
            except Exception:
                pass
            return False, str(e)

    def _sanitize_host(self, host: str) -> str:
        """Elimina esquemas tipo mqtt://, tcp://, ssl://, ws:// del host si vienen incluidos"""
        if not host:
            return host
        prefixes = ['mqtt://', 'mqtts://', 'tcp://', 'ssl://', 'ws://', 'wss://']
        for p in prefixes:
            if host.startswith(p):
                return host[len(p):]
        return host
    
    def test_connection(self):
        """Prueba la conexión MQTT"""
        start_time = time.time()
        
        try:
            success = self.connect()
            response_time = int((time.time() - start_time) * 1000)
            
            if success:
                self.disconnect()
                return {
                    'success': True,
                    'response_time': response_time,
                    'message': 'Conexión MQTT exitosa'
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'message': 'No se pudo establecer conexión MQTT'
                }
                
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'response_time': response_time,
                'message': str(e)
            }
    
    def disconnect(self):
        """Desconecta el cliente MQTT"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False


class HTTPSClient:
    def __init__(self, connection_config, auth_config=None):
        self.connection_config = connection_config
        self.auth_config = auth_config or {}
        self.session = requests.Session()
        
        # Configurar headers por defecto
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DeviceManager/1.0'
        }
        
        if self.connection_config.get('headers'):
            default_headers.update(self.connection_config['headers'])
        
        self.session.headers.update(default_headers)
        
        # Configurar autenticación
        self._setup_auth()
    
    def _setup_auth(self):
        """Configura la autenticación según el tipo"""
        auth_type = self.connection_config.get('auth_type', 'NONE')
        
        if auth_type == 'USER_PASS':
            username = self.auth_config.get('username')
            password = self.auth_config.get('password')
            if username and password:
                self.session.auth = (username, password)
        
        elif auth_type == 'TOKEN':
            token = self.auth_config.get('token')
            token_type = self.auth_config.get('token_type', 'Bearer')
            if token:
                self.session.headers['Authorization'] = f"{token_type} {token}"
        
        elif auth_type == 'API_KEY':
            key = self.auth_config.get('key')
            location = self.auth_config.get('location', 'header')
            param_name = self.auth_config.get('parameter_name', 'X-API-Key')
            
            if key:
                if location == 'header':
                    self.session.headers[param_name] = key
                # Para query parameters se manejará en send_request
    
    def _build_url(self, endpoint=None):
        """Construye la URL completa"""
        host = self.connection_config['host']
        port = self.connection_config.get('port')
        endpoint = endpoint or self.connection_config.get('endpoint', '')
        
        # Determinar esquema
        scheme = 'https' if self.connection_config.get('ssl', True) else 'http'
        
        # Construir URL base
        if port and port not in [80, 443]:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
        
        # Agregar endpoint
        if endpoint and not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        return base_url + endpoint
    
    def send_request(self, data, endpoint=None, method=None):
        """Envía una petición HTTP"""
        url = self._build_url(endpoint)
        method = method or self.connection_config.get('method', 'POST')
        timeout = self.connection_config.get('timeout', 30)
        verify_ssl = self.connection_config.get('verify_ssl', True)
        
        # Preparar parámetros para API Key en query
        params = {}
        if (self.connection_config.get('auth_type') == 'API_KEY' and 
            self.auth_config.get('location') == 'query'):
            param_name = self.auth_config.get('parameter_name', 'api_key')
            params[param_name] = self.auth_config.get('key')
        
        # Preparar datos
        if isinstance(data, dict):
            json_data = data
            data = None
        else:
            json_data = None
        
        response = self.session.request(
            method=method,
            url=url,
            json=json_data,
            data=data,
            params=params,
            timeout=timeout,
            verify=verify_ssl
        )
        
        response.raise_for_status()
        return response

    def send(self, data):
        """Interfaz unificada para TransmissionManager: envía request HTTPS.
        Usa endpoint/metod/timeout de connection_config.
        """
        try:
            response = self.send_request(data)
            ok = 200 <= response.status_code < 300
            text = ''
            try:
                text = response.text
            except Exception:
                text = str(response.status_code)
            return ok, text
        except Exception as e:
            return False, str(e)
    
    def test_connection(self):
        """Prueba la conexión HTTPS"""
        start_time = time.time()
        
        try:
            # Hacer una petición simple (HEAD o GET)
            url = self._build_url()
            timeout = self.connection_config.get('timeout', 10)
            verify_ssl = self.connection_config.get('verify_ssl', True)
            
            response = self.session.head(url, timeout=timeout, verify=verify_ssl)
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'response_time': response_time,
                'message': f'Conexión HTTPS exitosa (Status: {response.status_code})'
            }
            
        except requests.exceptions.RequestException as e:
            response_time = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'response_time': response_time,
                'message': f'Error de conexión HTTPS: {str(e)}'
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'response_time': response_time,
                'message': f'Error inesperado: {str(e)}'
            }


class ConnectionClientFactory:
    """Factory para crear clientes de conexión"""
    
    @staticmethod
    def create_client(connection):
        """Crea un cliente según el tipo de conexión"""
        connection_config = json.loads(connection.connection_config) if connection.connection_config else {}
        auth_config = connection.get_decrypted_auth_config()
        
        # Agregar configuración básica
        connection_config.update({
            'host': connection.host,
            'port': connection.port,
            'endpoint': connection.endpoint,
            'auth_type': connection.auth_type
        })
        
        if connection.type == 'MQTT':
            return MQTTClient(connection_config, auth_config)
        elif connection.type == 'HTTPS':
            return HTTPSClient(connection_config, auth_config)
        else:
            raise ValueError(f"Tipo de conexión no soportado: {connection.type}")
