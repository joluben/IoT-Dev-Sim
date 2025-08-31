# Plan de Implementación - Gestión de Dispositivos CSV

## FASE 1: CONFIGURACIÓN BASE Y ESTRUCTURA (Prioridad Alta)

### 1.1 Estructura del Proyecto
- Crear directorios según arquitectura definida
- Configurar .gitignore para Python y archivos temporales
- Inicializar estructura de carpetas vacías

### 1.2 Base de Datos

#### Subtarea 1.2.1: Definir esquema SQLite
```sql
CREATE TABLE devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reference TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  csv_data TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Subtarea 1.2.2: Implementar database.py con conexión SQLite
#### Subtarea 1.2.3: Crear función de inicialización de BD

### 1.3 Configuración Flask
#### Subtarea 1.3.1: Configurar app.py con Flask básico
#### Subtarea 1.3.2: Configurar CORS para desarrollo
#### Subtarea 1.3.3: Configurar manejo de archivos upload

## FASE 2: MODELOS Y LÓGICA DE NEGOCIO (Prioridad Alta)

### 2.1 Modelo Device
#### Subtarea 2.1.1: Crear clase Device en models.py
#### Subtarea 2.1.2: Implementar métodos CRUD (create, read, update, delete)
#### Subtarea 2.1.3: Implementar generador de referencias alfanuméricas

```python
import secrets
import string

def generate_reference():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
```

### 2.2 Procesamiento CSV

#### Subtarea 2.2.1: Implementar validador de archivos CSV
- Verificar extensión .csv
- Validar encoding UTF-8
- Comprobar tamaño máximo (10MB)
- Verificar que tenga al menos 1 fila de datos

#### Subtarea 2.2.2: Crear procesador con pandas
- Leer CSV y extraer cabecera
- Obtener primeras 5 filas de datos
- Manejar errores de formato

#### Subtarea 2.2.3: Implementar conversor CSV → JSON
- Convertir DataFrame a JSON
- Mantener tipos de datos apropiados
- Formatear para previsualización

## FASE 3: API BACKEND (Prioridad Alta)

### 3.1 Rutas de Dispositivos

#### Subtarea 3.1.1: POST /api/devices
```python
# Crear dispositivo con nombre y descripción
# Generar referencia automática
# Retornar dispositivo creado
```

#### Subtarea 3.1.2: GET /api/devices
```python
# Listar todos los dispositivos
# Incluir paginación si es necesario
```

#### Subtarea 3.1.3: GET /api/devices/<id>
```python
# Obtener dispositivo específico
# Incluir datos CSV si existen
```

### 3.2 Rutas de Upload

#### Subtarea 3.2.1: POST /api/devices/<id>/upload
```python
# Recibir archivo CSV
# Validar formato
# Procesar y retornar previsualización
# NO guardar en BD todavía
```

#### Subtarea 3.2.2: POST /api/devices/<id>/save
```python
# Guardar datos CSV procesados en BD
# Asociar con dispositivo específico
```

### 3.3 Manejo de Errores
#### Subtarea 3.3.1: Implementar respuestas HTTP estándar
#### Subtarea 3.3.2: Crear middleware de manejo de excepciones
#### Subtarea 3.3.3: Validación de entrada con mensajes descriptivos

## FASE 4: FRONTEND (Prioridad Alta)

### 4.1 Estructura HTML

#### Subtarea 4.1.1: Crear index.html con estructura base
```html
<!-- Vista lista de dispositivos -->
<!-- Vista crear dispositivo -->
<!-- Vista detalle dispositivo con upload -->
```

#### Subtarea 4.1.2: Implementar navegación SPA con JavaScript
#### Subtarea 4.1.3: Crear templates para cada vista

### 4.2 Estilos CSS
#### Subtarea 4.2.1: Implementar CSS Grid/Flexbox para layout
#### Subtarea 4.2.2: Crear componentes reutilizables (botones, formularios, tablas)
#### Subtarea 4.2.3: Implementar diseño responsive
#### Subtarea 4.2.4: Añadir animaciones y transiciones

### 4.3 JavaScript Funcional

#### Subtarea 4.3.1: Crear módulo de API calls
```javascript
const API = {
  createDevice: (data) => fetch('/api/devices', {...}),
  getDevices: () => fetch('/api/devices'),
  uploadCSV: (id, file) => fetch(`/api/devices/${id}/upload`, {...})
};
```

#### Subtarea 4.3.2: Implementar formulario de creación
#### Subtarea 4.3.3: Crear tabla de dispositivos con acciones
#### Subtarea 4.3.4: Implementar upload con drag & drop
#### Subtarea 4.3.5: Desarrollar previsualización CSV (tabla HTML)
#### Subtarea 4.3.6: Desarrollar previsualización JSON (formato legible)
#### Subtarea 4.3.7: Implementar previsualización CSV y JSON al ver el detalle de un dispositivo

## FASE 5: CONTAINERIZACIÓN (Prioridad Media)

### 5.1 Backend Docker

#### Subtarea 5.1.1: Crear requirements.txt con dependencias
```txt
Flask==2.3.3
pandas==2.0.3
python-dotenv==1.0.0
```

#### Subtarea 5.1.2: Crear Dockerfile para backend
#### Subtarea 5.1.3: Configurar volúmenes para uploads y BD
#### Subtarea 5.1.4: Crear docker-compose.yml para backend

### 5.2 Frontend Docker
#### Subtarea 5.2.1: Configurar nginx para servir archivos estáticos
#### Subtarea 5.2.2: Crear Dockerfile para frontend
#### Subtarea 5.2.3: Configurar proxy reverso a backend

### 5.3 Orquestación
#### Subtarea 5.3.1: Crear docker-compose.yml
#### Subtarea 5.3.2: Configurar redes entre servicios
#### Subtarea 5.3.3: Configurar volúmenes persistentes

## FASE 6: SISTEMA DE CONEXIONES EXTERNAS (Prioridad Alta)

### 6.1 Análisis y Diseño del Sistema de Conexiones

#### Descripción del Requerimiento
El sistema debe permitir la gestión completa de conexiones con sistemas externos, soportando múltiples protocolos de comunicación y diversos métodos de autenticación. Los usuarios podrán crear, configurar, probar y gestionar conexiones que posteriormente podrán ser utilizadas para enviar datos de dispositivos a sistemas externos.

**Tipos de Conexión Soportados:**
- **MQTT (Mosquitto)**: Protocolo de mensajería ligero para IoT
- **HTTPS REST API**: Servicios web RESTful sobre HTTPS

**Métodos de Autenticación Soportados:**
- **Usuario y Contraseña**: Autenticación básica
- **Token Bearer**: Autenticación por token JWT/OAuth
- **API Key**: Clave de API en header o query parameter
- **Sin Autenticación**: Para servicios públicos

#### Subtarea 6.1.1: Definir esquema de base de datos para conexiones
```sql
CREATE TABLE connections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  type TEXT NOT NULL CHECK(type IN ('MQTT', 'HTTPS')),
  host TEXT NOT NULL,
  port INTEGER,
  endpoint TEXT, -- Para HTTPS: /api/endpoint, Para MQTT: topic
  auth_type TEXT NOT NULL CHECK(auth_type IN ('NONE', 'USER_PASS', 'TOKEN', 'API_KEY')),
  auth_config TEXT, -- JSON con configuración de autenticación
  connection_config TEXT, -- JSON con configuración específica del protocolo
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE connection_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  connection_id INTEGER NOT NULL,
  test_result TEXT NOT NULL CHECK(test_result IN ('SUCCESS', 'FAILED')),
  response_time INTEGER, -- en milisegundos
  error_message TEXT,
  tested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (connection_id) REFERENCES connections (id)
);
```

#### Subtarea 6.1.2: Diseñar estructura de configuración JSON
```json
// Ejemplo auth_config para diferentes tipos
{
  "USER_PASS": {
    "username": "user123",
    "password": "encrypted_password"
  },
  "TOKEN": {
    "token": "Bearer eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer"
  },
  "API_KEY": {
    "key": "api_key_value",
    "location": "header|query",
    "parameter_name": "X-API-Key"
  }
}

// Ejemplo connection_config
{
  "MQTT": {
    "client_id": "device_manager_001",
    "keep_alive": 60,
    "qos": 1,
    "retain": false,
    "ssl": true,
    "ca_cert_path": "/path/to/ca.crt"
  },
  "HTTPS": {
    "timeout": 30,
    "verify_ssl": true,
    "headers": {
      "Content-Type": "application/json",
      "User-Agent": "DeviceManager/1.0"
    },
    "method": "POST"
  }
}
```

### 6.2 Modelos y Lógica de Negocio para Conexiones

#### Subtarea 6.2.1: Crear clase Connection en models.py
- Implementar métodos CRUD para conexiones
- Encriptación/desencriptación de credenciales sensibles
- Validaciones de configuración según tipo de conexión

#### Subtarea 6.2.2: Implementar validadores de conexión
```python
class ConnectionValidator:
    @staticmethod
    def validate_mqtt_config(config):
        # Validar host, puerto, topic, certificados SSL
        pass
    
    @staticmethod
    def validate_https_config(config):
        # Validar URL, método HTTP, headers
        pass
    
    @staticmethod
    def validate_auth_config(auth_type, auth_config):
        # Validar credenciales según tipo de autenticación
        pass
```

#### Subtarea 6.2.3: Crear sistema de encriptación para credenciales
- Implementar encriptación AES para passwords y tokens
- Gestión segura de claves de encriptación
- Funciones de encrypt/decrypt para datos sensibles

#### Subtarea 6.2.4: Implementar clases de cliente para cada protocolo
```python
class MQTTClient:
    def __init__(self, connection_config):
        pass
    
    def connect(self):
        pass
    
    def publish(self, topic, message):
        pass
    
    def test_connection(self):
        pass

class HTTPSClient:
    def __init__(self, connection_config):
        pass
    
    def send_request(self, data):
        pass
    
    def test_connection(self):
        pass
```

### 6.3 API Backend para Conexiones

#### Subtarea 6.3.1: Rutas CRUD de conexiones
```python
# GET /api/connections - Listar todas las conexiones
# POST /api/connections - Crear nueva conexión
# GET /api/connections/<id> - Obtener conexión específica
# PUT /api/connections/<id> - Actualizar conexión
# DELETE /api/connections/<id> - Eliminar conexión
```

#### Subtarea 6.3.2: Ruta de prueba de conexión
```python
# POST /api/connections/<id>/test
# Realizar prueba de conectividad
# Guardar resultado en connection_tests
# Retornar estado y tiempo de respuesta
```

#### Subtarea 6.3.3: Rutas de configuración y metadatos
```python
# GET /api/connections/types - Obtener tipos de conexión disponibles
# GET /api/connections/auth-types - Obtener tipos de autenticación
# GET /api/connections/<id>/history - Historial de pruebas
```

#### Subtarea 6.3.4: Ruta de envío de datos de dispositivos
```python
# POST /api/devices/<device_id>/send/<connection_id>
# Enviar datos CSV de dispositivo a través de conexión específica
# Formatear datos según protocolo de destino
# Registrar resultado del envío
```

### 6.4 Frontend para Gestión de Conexiones

#### Subtarea 6.4.1: Crear vistas HTML para conexiones
```html
<!-- Vista lista de conexiones -->
<!-- Vista crear/editar conexión -->
<!-- Vista detalle de conexión con historial -->
<!-- Modal de prueba de conexión -->
```

#### Subtarea 6.4.2: Implementar formulario dinámico de creación
- Formulario que se adapte según el tipo de conexión seleccionado
- Campos específicos para cada protocolo (MQTT/HTTPS)
- Sección de autenticación dinámica según el tipo seleccionado
- Validación en tiempo real de campos

#### Subtarea 6.4.3: Crear componente de prueba de conexión
- Botón de "Probar Conexión" con indicador de carga
- Visualización de resultados de prueba en tiempo real
- Historial de pruebas anteriores
- Indicadores visuales de estado (éxito/error)

#### Subtarea 6.4.4: Implementar tabla de conexiones con acciones
- Lista de todas las conexiones con información básica
- Acciones: Editar, Eliminar, Probar, Activar/Desactivar
- Filtros por tipo de conexión y estado
- Indicadores de estado de conectividad

#### Subtarea 6.4.5: Crear interfaz de envío de datos
- Integración con vista de dispositivos
- Selector de conexiones activas para envío
- Previsualización del formato de datos a enviar
- Confirmación y resultado del envío

### 6.5 JavaScript para Conexiones

#### Subtarea 6.5.1: Extender módulo API
```javascript
const ConnectionAPI = {
  getConnections: () => fetch('/api/connections'),
  createConnection: (data) => fetch('/api/connections', {...}),
  updateConnection: (id, data) => fetch(`/api/connections/${id}`, {...}),
  deleteConnection: (id) => fetch(`/api/connections/${id}`, {...}),
  testConnection: (id) => fetch(`/api/connections/${id}/test`, {...}),
  getConnectionTypes: () => fetch('/api/connections/types'),
  sendDeviceData: (deviceId, connectionId) => fetch(`/api/devices/${deviceId}/send/${connectionId}`, {...})
};
```

#### Subtarea 6.5.2: Implementar lógica de formulario dinámico
- Controlador para mostrar/ocultar campos según tipo de conexión
- Validaciones específicas por protocolo
- Gestión de estado del formulario

#### Subtarea 6.5.3: Crear sistema de notificaciones
- Notificaciones para éxito/error en operaciones
- Indicadores de progreso para operaciones asíncronas
- Mensajes informativos para el usuario

### 6.6 Seguridad y Configuración

#### Subtarea 6.6.1: Implementar gestión de secretos
- Variables de entorno para claves de encriptación
- Configuración segura de certificados SSL/TLS
- Políticas de rotación de credenciales

#### Subtarea 6.6.2: Validación y sanitización de entrada
- Validación estricta de URLs y configuraciones
- Sanitización de datos de configuración JSON
- Prevención de inyección de código

#### Subtarea 6.6.3: Logging y auditoría
- Registro de todas las operaciones de conexión
- Logs de pruebas de conectividad
- Auditoría de acceso a credenciales

### 6.7 Dependencias Adicionales

#### Subtarea 6.7.1: Actualizar requirements.txt
```
# Dependencias existentes
Flask==2.3.3
pandas==2.0.3
python-dotenv==1.0.0

# Nuevas dependencias para conexiones
paho-mqtt==1.6.1
requests==2.31.0
cryptography==41.0.3
pyjwt==2.8.0
```

#### Subtarea 6.7.2: Configurar librerías JavaScript
- Cliente MQTT para JavaScript (si se requiere monitoreo en tiempo real)
- Librerías de validación de formularios
- Componentes de interfaz para indicadores de estado

## FASE 7: SISTEMA DE TIPOLOGÍA Y TRANSMISIÓN DE DISPOSITIVOS (Prioridad Alta)

### 7.1 Análisis y Diseño del Sistema de Tipología de Dispositivos

#### Descripción del Requerimiento
El sistema debe diferenciar entre dos tipos de dispositivos que determinan la forma de transmisión de datos a través de las conexiones externas. Cada tipo de dispositivo tiene un comportamiento específico de envío que se adapta a diferentes casos de uso IoT y aplicaciones web.

**Tipos de Dispositivos:**

1. **WebApp (Aplicación Web)**
   - **Comportamiento de Envío**: Transmite el dataset CSV completo en cada envío
   - **Formato de Datos**: JSON con todas las filas del CSV
   - **Frecuencia**: Configurable (minutos, horas, días)
   - **Uso Típico**: Dashboards, reportes, análisis batch de datos
   - **Volumen**: Alto volumen de datos por transmisión

2. **Sensor (Dispositivo IoT)**
   - **Comportamiento de Envío**: Transmite una sola línea del CSV por envío de forma secuencial
   - **Formato de Datos**: JSON de una fila + timestamp automático
   - **Frecuencia**: Configurable (segundos, minutos)
   - **Uso Típico**: Sensores IoT, streaming de datos en tiempo real
   - **Volumen**: Bajo volumen de datos por transmisión, alta frecuencia

**Funcionalidades del Sistema:**
- **Configuración de Frecuencia**: Programador de tareas automáticas por dispositivo
- **Estado de Transmisión**: Control del progreso de envío para dispositivos tipo Sensor
- **Historial de Envíos**: Registro detallado de todas las transmisiones
- **Control Manual**: Posibilidad de iniciar/pausar/detener envíos
- **Simulación de Tiempo Real**: Para dispositivos Sensor, simular flujo temporal de datos

#### Subtarea 7.1.1: Actualizar esquema de base de datos
```sql
-- Actualizar tabla devices
ALTER TABLE devices ADD COLUMN device_type TEXT NOT NULL DEFAULT 'WebApp' CHECK(device_type IN ('WebApp', 'Sensor'));
ALTER TABLE devices ADD COLUMN transmission_frequency INTEGER DEFAULT 3600; -- en segundos
ALTER TABLE devices ADD COLUMN transmission_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN current_row_index INTEGER DEFAULT 0; -- Para tipo Sensor
ALTER TABLE devices ADD COLUMN last_transmission DATETIME;

-- Nueva tabla para historial de transmisiones
CREATE TABLE device_transmissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  transmission_type TEXT NOT NULL CHECK(transmission_type IN ('FULL_CSV', 'SINGLE_ROW')),
  data_sent TEXT, -- JSON de los datos enviados
  row_index INTEGER, -- Para tipo Sensor, índice de la fila enviada
  status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED', 'PENDING')),
  response_data TEXT, -- Respuesta del sistema externo
  error_message TEXT,
  transmission_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices (id),
  FOREIGN KEY (connection_id) REFERENCES connections (id)
);

-- Tabla para programación de tareas automáticas
CREATE TABLE scheduled_transmissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  next_execution DATETIME NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices (id),
  FOREIGN KEY (connection_id) REFERENCES connections (id)
);
```

#### Subtarea 7.1.2: Diseñar estructura de datos de transmisión
```json
// Formato para dispositivo WebApp
{
  "device_id": "ABC12345",
  "device_name": "Temperature Monitor Dashboard",
  "device_type": "WebApp",
  "transmission_timestamp": "2024-08-28T10:30:00Z",
  "data_count": 1500,
  "data": [
    {
      "temperature": 23.5,
      "humidity": 65.2,
      "pressure": 1013.25,
      "recorded_at": "2024-08-28T08:00:00Z"
    },
    // ... todas las filas del CSV
  ]
}

// Formato para dispositivo Sensor
{
  "device_id": "XYZ67890",
  "device_name": "IoT Temperature Sensor",
  "device_type": "Sensor",
  "transmission_timestamp": "2024-08-28T10:30:00Z",
  "row_index": 245,
  "data": {
    "temperature": 24.1,
    "humidity": 62.8,
    "pressure": 1012.85,
    "recorded_at": "2024-08-28T08:04:00Z",
    "timestamp": "2024-08-28T10:30:00Z" // Timestamp automático del envío
  }
}
```

### 7.2 Modelos y Lógica de Negocio para Tipología de Dispositivos

#### Subtarea 7.2.1: Extender clase Device con tipología
```python
class Device:
    DEVICE_TYPES = ['WebApp', 'Sensor']
    
    def __init__(self):
        self.device_type = 'WebApp'
        self.transmission_frequency = 3600  # segundos
        self.transmission_enabled = False
        self.current_row_index = 0
        self.last_transmission = None
    
    def get_transmission_data(self):
        """Retorna datos según el tipo de dispositivo"""
        if self.device_type == 'WebApp':
            return self._get_full_csv_data()
        elif self.device_type == 'Sensor':
            return self._get_next_row_data()
    
    def _get_full_csv_data(self):
        """Retorna todo el CSV en formato JSON"""
        pass
    
    def _get_next_row_data(self):
        """Retorna la siguiente fila con timestamp automático"""
        pass
    
    def reset_sensor_position(self):
        """Reinicia el índice para dispositivos Sensor"""
        pass
```

#### Subtarea 7.2.2: Implementar sistema de gestión de estados de transmisión
```python
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
        self.device_states[device_id] = self.STATES['ACTIVE']
        # Lógica para iniciar scheduler
        pass
    
    def pause_transmission(self, device_id):
        """Pausa transmisión automática manteniendo configuración"""
        if self.device_states.get(device_id) == self.STATES['ACTIVE']:
            self.device_states[device_id] = self.STATES['PAUSED']
            # Lógica para pausar scheduler sin cancelar
        pass
    
    def resume_transmission(self, device_id):
        """Reanuda transmisión automática desde punto de pausa"""
        if self.device_states.get(device_id) == self.STATES['PAUSED']:
            self.device_states[device_id] = self.STATES['ACTIVE']
            # Lógica para reactivar scheduler
        pass
    
    def stop_transmission(self, device_id):
        """Detiene completamente la transmisión automática"""
        self.device_states[device_id] = self.STATES['INACTIVE']
        # Lógica para cancelar scheduler completamente
        pass
    
    def execute_manual_transmission(self, device_id, connection_id):
        """Ejecuta transmisión manual inmediata"""
        if self.can_execute_manual(device_id):
            # Cambio temporal de estado durante ejecución
            original_state = self.device_states.get(device_id, self.STATES['INACTIVE'])
            self.device_states[device_id] = self.STATES['MANUAL']
            
            try:
                # Ejecutar transmisión manual
                result = self._execute_transmission(device_id, connection_id)
                return result
            finally:
                # Restaurar estado original
                self.device_states[device_id] = original_state
    
    def can_execute_manual(self, device_id):
        """Verifica si se puede ejecutar transmisión manual"""
        current_state = self.device_states.get(device_id, self.STATES['INACTIVE'])
        return current_state == self.STATES['INACTIVE']
    
    def get_device_state(self, device_id):
        """Obtiene el estado actual del dispositivo"""
        return self.device_states.get(device_id, self.STATES['INACTIVE'])
    
    def get_available_actions(self, device_id):
        """Retorna las acciones disponibles según el estado actual"""
        state = self.get_device_state(device_id)
        
        actions = {
            'transmit_now': {
                'enabled': state == self.STATES['INACTIVE'],
                'visible': True
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
                'visible': True
            }
        }
        
        return actions
```

#### Subtarea 7.2.3: Crear gestor de transmisiones
```python
class TransmissionManager:
    def __init__(self):
        self.transmission_history = []
    
    def transmit_device_data(self, device, connection):
        """Ejecuta transmisión según tipo de dispositivo"""
        pass
    
    def log_transmission(self, device_id, connection_id, data, status):
        """Registra resultado de transmisión"""
        pass
    
    def get_transmission_history(self, device_id):
        """Obtiene historial de transmisiones"""
        pass
    
    def get_transmission_stats(self, device_id):
        """Obtiene estadísticas de transmisión"""
        pass
```

### 7.3 API Backend para Tipología y Transmisión

#### Subtarea 7.3.1: Extender rutas de dispositivos
```python
# PUT /api/devices/<id>/type - Cambiar tipo de dispositivo
# PUT /api/devices/<id>/transmission-config - Configurar frecuencia y estado
# GET /api/devices/<id>/transmission-status - Estado actual de transmisión
# POST /api/devices/<id>/reset-position - Reiniciar posición para Sensor
```

#### Subtarea 7.3.2: Rutas de control de transmisión con gestión de estados
```python
# POST /api/devices/<id>/start-transmission/<connection_id> - Iniciar transmisión automática
# POST /api/devices/<id>/pause-transmission - Pausar transmisión automática
# POST /api/devices/<id>/resume-transmission - Reanudar transmisión automática  
# POST /api/devices/<id>/stop-transmission - Detener transmisión automática
# POST /api/devices/<id>/transmit-now/<connection_id> - Transmisión manual inmediata
# GET /api/devices/<id>/transmission-state - Obtener estado actual y acciones disponibles

@app.route('/api/devices/<int:device_id>/transmission-state', methods=['GET'])
def get_transmission_state(device_id):
    """Retorna estado actual y acciones disponibles para el dispositivo"""
    state_manager = TransmissionStateManager()
    current_state = state_manager.get_device_state(device_id)
    available_actions = state_manager.get_available_actions(device_id)
    
    return jsonify({
        'device_id': device_id,
        'current_state': current_state,
        'available_actions': available_actions,
        'last_transmission': get_last_transmission_time(device_id),
        'next_scheduled': get_next_scheduled_transmission(device_id)
    })

@app.route('/api/devices/<int:device_id>/transmit-now/<int:connection_id>', methods=['POST'])
def transmit_now(device_id, connection_id):
    """Ejecuta transmisión manual solo si está permitido"""
    state_manager = TransmissionStateManager()
    
    if not state_manager.can_execute_manual(device_id):
        return jsonify({
            'error': 'Cannot execute manual transmission while automatic transmission is active',
            'current_state': state_manager.get_device_state(device_id)
        }), 400
    
    try:
        result = state_manager.execute_manual_transmission(device_id, connection_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

#### Subtarea 7.3.3: Rutas de historial y monitoreo
```python
# GET /api/devices/<id>/transmissions - Historial de transmisiones
# GET /api/devices/<id>/transmission-stats - Estadísticas de transmisión
# GET /api/transmissions/active - Transmisiones activas del sistema
# GET /api/transmissions/scheduled - Próximas transmisiones programadas
```

### 7.4 Frontend para Tipología y Transmisión

#### Subtarea 7.4.1: Actualizar formulario de dispositivos
- Selector de tipo de dispositivo (WebApp/Sensor)
- Configuración de frecuencia de transmisión
- Campos específicos según el tipo seleccionado
- Previsualización del comportamiento de transmisión

#### Subtarea 7.4.2: Crear panel de control de transmisión
- Panel de estado de transmisión con indicadores visuales
- Sistema de botones de control con lógica de estados:
  * **Transmitir Ahora**: Ejecuta transmisión manual inmediata
  * **Pausar/Reanudar**: Control de transmisiones automáticas en progreso
  * **Parar**: Detiene completamente las transmisiones automáticas
- Indicadores de progreso para dispositivos Sensor
- Mostrar próxima transmisión programada
- Estado de conexión en tiempo real
- Estadísticas de transmisión (éxito/fallo)

##### Estados y Comportamiento de Botones de Control:

**Estado INACTIVO (Sin transmisión activa):**
- ✅ **Transmitir Ahora**: Habilitado - Permite transmisión manual inmediata
- ❌ **Pausar**: Oculto - No hay transmisión que pausar
- ❌ **Reanudar**: Oculto - No hay transmisión pausada
- ❌ **Parar**: Deshabilitado - No hay transmisión activa que parar

**Estado TRANSMITIENDO (Transmisión automática activa):**
- ❌ **Transmitir Ahora**: Deshabilitado - Evita conflictos con transmisión automática
- ✅ **Pausar**: Habilitado - Permite pausar transmisión sin perder configuración
- ❌ **Reanudar**: Oculto - La transmisión está activa
- ✅ **Parar**: Habilitado - Permite detener completamente la transmisión

**Estado PAUSADO (Transmisión pausada temporalmente):**
- ❌ **Transmitir Ahora**: Deshabilitado - La transmisión sigue programada
- ❌ **Pausar**: Oculto - Ya está pausada
- ✅ **Reanudar**: Habilitado - Permite continuar desde donde se pausó
- ✅ **Parar**: Habilitado - Permite cancelar definitivamente la transmisión

**Transiciones de Estado:**
1. **INACTIVO → TRANSMITIENDO**: Al configurar y activar transmisión automática
2. **TRANSMITIENDO → PAUSADO**: Al presionar "Pausar"
3. **PAUSADO → TRANSMITIENDO**: Al presionar "Reanudar"
4. **TRANSMITIENDO/PAUSADO → INACTIVO**: Al presionar "Parar"
5. **Cualquier estado → Ejecución puntual**: "Transmitir Ahora" (solo si está habilitado)

#### Subtarea 7.4.3: Crear historial de transmisiones
- Tabla con filtros por dispositivo, conexión, estado
- Detalles de cada transmisión (datos enviados, respuesta)
- Exportación de historial a CSV/JSON
- Gráficos de tendencias de transmisión

### 7.5 JavaScript para Control de Transmisión

#### Subtarea 7.5.1: Extender API client con gestión de estados
```javascript
const TransmissionAPI = {
  updateDeviceType: (id, type) => fetch(`/api/devices/${id}/type`, {...}),
  configureTransmission: (id, config) => fetch(`/api/devices/${id}/transmission-config`, {...}),
  
  // Control de transmisión con gestión de estados
  startTransmission: (deviceId, connectionId) => fetch(`/api/devices/${deviceId}/start-transmission/${connectionId}`, {...}),
  pauseTransmission: (id) => fetch(`/api/devices/${id}/pause-transmission`, {...}),
  resumeTransmission: (id) => fetch(`/api/devices/${id}/resume-transmission`, {...}),
  stopTransmission: (id) => fetch(`/api/devices/${id}/stop-transmission`, {...}),
  transmitNow: (deviceId, connectionId) => fetch(`/api/devices/${deviceId}/transmit-now/${connectionId}`, {...}),
  
  // Gestión de estados
  getTransmissionState: (id) => fetch(`/api/devices/${id}/transmission-state`),
  getTransmissionHistory: (id) => fetch(`/api/devices/${id}/transmissions`),
  getTransmissionStats: (id) => fetch(`/api/devices/${id}/transmission-stats`)
};

class TransmissionControlUI {
  constructor(deviceId) {
    this.deviceId = deviceId;
    this.currentState = 'INACTIVE';
    this.buttons = {
      transmitNow: document.getElementById('btn-transmit-now'),
      pause: document.getElementById('btn-pause'),
      resume: document.getElementById('btn-resume'),
      stop: document.getElementById('btn-stop')
    };
    
    this.initializeEventListeners();
    this.updateButtonStates();
  }
  
  async updateButtonStates() {
    try {
      const response = await TransmissionAPI.getTransmissionState(this.deviceId);
      const data = await response.json();
      
      this.currentState = data.current_state;
      const actions = data.available_actions;
      
      // Actualizar visibilidad y estado de botones
      this.buttons.transmitNow.disabled = !actions.transmit_now.enabled;
      this.buttons.transmitNow.style.display = actions.transmit_now.visible ? 'inline-block' : 'none';
      
      this.buttons.pause.disabled = !actions.pause.enabled;
      this.buttons.pause.style.display = actions.pause.visible ? 'inline-block' : 'none';
      
      this.buttons.resume.disabled = !actions.resume.enabled;
      this.buttons.resume.style.display = actions.resume.visible ? 'inline-block' : 'none';
      
      this.buttons.stop.disabled = !actions.stop.enabled;
      
      // Actualizar indicadores visuales
      this.updateStateIndicator(this.currentState);
      
    } catch (error) {
      console.error('Error updating button states:', error);
    }
  }
  
  initializeEventListeners() {
    this.buttons.transmitNow.addEventListener('click', () => this.handleTransmitNow());
    this.buttons.pause.addEventListener('click', () => this.handlePause());
    this.buttons.resume.addEventListener('click', () => this.handleResume());
    this.buttons.stop.addEventListener('click', () => this.handleStop());
  }
  
  async handleTransmitNow() {
    if (this.currentState !== 'INACTIVE') {
      this.showError('No se puede transmitir manualmente mientras hay una transmisión automática activa');
      return;
    }
    
    const connectionId = this.getSelectedConnectionId();
    if (!connectionId) {
      this.showError('Debe seleccionar una conexión');
      return;
    }
    
    try {
      this.setButtonLoading(this.buttons.transmitNow, true);
      const response = await TransmissionAPI.transmitNow(this.deviceId, connectionId);
      
      if (response.ok) {
        this.showSuccess('Transmisión manual ejecutada exitosamente');
      } else {
        const error = await response.json();
        this.showError(error.error || 'Error en la transmisión');
      }
    } catch (error) {
      this.showError('Error de conexión: ' + error.message);
    } finally {
      this.setButtonLoading(this.buttons.transmitNow, false);
      this.updateButtonStates();
    }
  }
  
  async handlePause() {
    try {
      await TransmissionAPI.pauseTransmission(this.deviceId);
      this.showSuccess('Transmisión pausada');
      this.updateButtonStates();
    } catch (error) {
      this.showError('Error al pausar transmisión: ' + error.message);
    }
  }
  
  async handleResume() {
    try {
      await TransmissionAPI.resumeTransmission(this.deviceId);
      this.showSuccess('Transmisión reanudada');
      this.updateButtonStates();
    } catch (error) {
      this.showError('Error al reanudar transmisión: ' + error.message);
    }
  }
  
  async handleStop() {
    if (!confirm('¿Está seguro de que desea detener completamente la transmisión?')) {
      return;
    }
    
    try {
      await TransmissionAPI.stopTransmission(this.deviceId);
      this.showSuccess('Transmisión detenida');
      this.updateButtonStates();
    } catch (error) {
      this.showError('Error al detener transmisión: ' + error.message);
    }
  }
  
  updateStateIndicator(state) {
    const indicator = document.getElementById('transmission-state-indicator');
    const stateText = document.getElementById('transmission-state-text');
    
    const stateConfig = {
      'INACTIVE': { text: 'Inactivo', class: 'state-inactive', color: '#6c757d' },
      'ACTIVE': { text: 'Transmitiendo', class: 'state-active', color: '#28a745' },
      'PAUSED': { text: 'Pausado', class: 'state-paused', color: '#ffc107' },
      'MANUAL': { text: 'Transmisión Manual', class: 'state-manual', color: '#17a2b8' }
    };
    
    const config = stateConfig[state] || stateConfig['INACTIVE'];
    
    indicator.className = `transmission-indicator ${config.class}`;
    indicator.style.backgroundColor = config.color;
    stateText.textContent = config.text;
  }
  
  setButtonLoading(button, loading) {
    if (loading) {
      button.disabled = true;
      button.innerHTML = '<span class="spinner"></span> Procesando...';
    } else {
      button.disabled = false;
      button.innerHTML = button.getAttribute('data-original-text');
    }
  }
  
  showSuccess(message) {
    this.showNotification(message, 'success');
  }
  
  showError(message) {
    this.showNotification(message, 'error');
  }
  
  showNotification(message, type) {
    // Implementar sistema de notificaciones
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 5000);
  }
  
  getSelectedConnectionId() {
    const selector = document.getElementById('connection-selector');
    return selector ? selector.value : null;
  }
}
```

#### Subtarea 7.5.2: Implementar control en tiempo real
- WebSocket o polling para actualizaciones de estado
- Notificaciones de transmisiones exitosas/fallidas
- Actualización automática de contadores y progreso

#### Subtarea 7.5.3: Crear visualizaciones de datos
- Gráficos de líneas para frecuencia de transmisión
- Indicadores de progreso para dispositivos Sensor
- Mapas de calor de actividad de transmisión

### 7.6 Sistema de Tareas Programadas con APScheduler

#### Subtarea 7.6.1: Implementar scheduler con APScheduler
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

class TransmissionScheduler:
    def __init__(self, app):
        self.app = app
        self.scheduler = None
        self.setup_scheduler()
    
    def setup_scheduler(self):
        """Configurar APScheduler con persistencia en BD"""
        jobstores = {
            'default': SQLAlchemyJobStore(url=self.app.config['DATABASE_URL'])
        }
        executors = {
            'default': ThreadPoolExecutor(20)  # Máximo 20 threads concurrentes
        }
        job_defaults = {
            'coalesce': False,  # No agrupar ejecuciones perdidas
            'max_instances': 1  # Una instancia por job
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
    
    def start(self):
        """Iniciar el scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
    
    def shutdown(self):
        """Detener el scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
    
    def schedule_transmission(self, device_id, connection_id, frequency_seconds):
        """Programar transmisión automática"""
        job_id = f"transmission_{device_id}_{connection_id}"
        
        self.scheduler.add_job(
            func=self._execute_transmission,
            trigger='interval',
            seconds=frequency_seconds,
            args=[device_id, connection_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=30  # 30 segundos de gracia para ejecuciones perdidas
        )
        
        return job_id
    
    def pause_transmission(self, device_id, connection_id):
        """Pausar transmisión sin eliminar la programación"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.pause_job(job_id)
            return True
        except:
            return False
    
    def resume_transmission(self, device_id, connection_id):
        """Reanudar transmisión pausada"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.resume_job(job_id)
            return True
        except:
            return False
    
    def stop_transmission(self, device_id, connection_id):
        """Detener y eliminar transmisión programada"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.remove_job(job_id)
            return True
        except:
            return False
    
    def _execute_transmission(self, device_id, connection_id):
        """Ejecutar transmisión programada"""
        with self.app.app_context():
            try:
                transmission_manager = TransmissionManager()
                result = transmission_manager.execute_device_transmission(device_id, connection_id)
                
                # Log del resultado
                self._log_transmission_result(device_id, connection_id, result)
                
            except Exception as e:
                # Log del error
                self._log_transmission_error(device_id, connection_id, str(e))
    
    def get_job_status(self, device_id, connection_id):
        """Obtener estado del job programado"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    'exists': True,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
        except:
            pass
        
        return {'exists': False}
```

#### Subtarea 7.6.2: Integrar scheduler con Flask app
```python
# En app.py
from flask import Flask
from transmission_scheduler import TransmissionScheduler

def create_app():
    app = Flask(__name__)
    
    # Configurar scheduler
    scheduler = TransmissionScheduler(app)
    app.scheduler = scheduler
    
    # Iniciar scheduler cuando la app esté lista
    @app.before_first_request
    def start_scheduler():
        app.scheduler.start()
    
    # Detener scheduler al cerrar la app
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        if hasattr(app, 'scheduler'):
            app.scheduler.shutdown()
    
    return app
```

#### Subtarea 7.6.3: Implementar sistema de monitoreo y logging
```python
class SchedulerMonitor:
    def __init__(self, scheduler):
        self.scheduler = scheduler
    
    def get_active_jobs(self):
        """Obtener lista de jobs activos"""
        jobs = []
        for job in self.scheduler.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'function': job.func.__name__
            })
        return jobs
    
    def get_scheduler_stats(self):
        """Obtener estadísticas del scheduler"""
        return {
            'running': self.scheduler.scheduler.running,
            'total_jobs': len(self.scheduler.scheduler.get_jobs()),
            'executor_info': self.scheduler.scheduler.state
        }
```

### 7.7 Validaciones y Reglas de Negocio

#### Subtarea 7.7.1: Validaciones específicas por tipo
- WebApp: Validar disponibilidad completa del CSV
- Sensor: Validar existencia de filas pendientes
- Validar frecuencias mínimas y máximas por tipo

#### Subtarea 7.7.2: Reglas de comportamiento
- Auto-pausa cuando se completan todas las filas (Sensor)
- Gestión de concurrencia en transmisiones
- Límites de transmisiones simultáneas por dispositivo

### 7.8 Dependencias Adicionales para Transmisión

#### Subtarea 7.8.1: Actualizar requirements.txt
```
# Dependencias existentes...

# Nuevas dependencias para transmisión
apscheduler==3.10.4
websocket-client==1.6.1
sqlalchemy==1.4.46  # Para persistencia de jobs en APScheduler
```

## FASE 8: SISTEMA DE GESTIÓN DE PROYECTOS 

### 8.1 Análisis y Diseño del Sistema de Proyectos

#### Descripción del Requerimiento
El sistema debe permitir la gestión completa de proyectos que actúan como contenedores organizacionales para agrupar dispositivos relacionados. Los proyectos facilitan la administración masiva de dispositivos, permitiendo operaciones de transmisión coordinadas y seguimiento centralizado del historial de transmisiones.

**Características Principales:**
- **Gestión CRUD**: Crear, leer, actualizar y eliminar proyectos
- **Agrupación de Dispositivos**: Un proyecto puede contener múltiples dispositivos
- **Selección Flexible**: Asignar/desasignar dispositivos de proyectos
- **Control Masivo**: Iniciar/pausar/parar transmisiones de todos los dispositivos del proyecto
- **Historial Centralizado**: Vista unificada del historial de transmisiones por proyecto
- **Desvinculación Segura**: Al eliminar proyecto, dispositivos quedan desvinculados de ese proyecto

#### Subtarea 8.1.1: Definir esquema de base de datos para proyectos
```sql
-- Tabla de proyectos
CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  transmission_status TEXT DEFAULT 'INACTIVE' CHECK(transmission_status IN ('INACTIVE', 'ACTIVE', 'PAUSED')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de relación muchos a muchos: proyecto-dispositivo
CREATE TABLE project_devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  device_id INTEGER NOT NULL,
  assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
  FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE,
  UNIQUE(project_id, device_id)
);

-- Índices para optimizar consultas
CREATE INDEX idx_project_devices_project ON project_devices(project_id);
CREATE INDEX idx_project_devices_device ON project_devices(device_id);
CREATE INDEX idx_projects_status ON projects(transmission_status);

-- Actualizar tabla devices para mostrar proyecto actual (opcional)
ALTER TABLE devices ADD COLUMN current_project_id INTEGER;
ALTER TABLE devices ADD FOREIGN KEY (current_project_id) REFERENCES projects (id) ON DELETE SET NULL;
```

#### Subtarea 8.1.2: Diseñar estructura de datos para operaciones masivas
```json
// Estructura de respuesta para operaciones del proyecto
{
  "project_id": 1,
  "project_name": "Sensores de Temperatura Campus",
  "operation": "START_TRANSMISSION",
  "total_devices": 15,
  "successful_operations": 12,
  "failed_operations": 3,
  "results": [
    {
      "device_id": 1,
      "device_name": "Sensor Edificio A",
      "status": "SUCCESS",
      "message": "Transmisión iniciada correctamente"
    },
    {
      "device_id": 2,
      "device_name": "Sensor Edificio B", 
      "status": "FAILED",
      "message": "No hay conexión configurada",
      "error_code": "NO_CONNECTION"
    }
  ],
  "execution_time": "2024-08-30T10:30:00Z"
}
```

### 8.2 Modelos y Lógica de Negocio para Proyectos

#### Subtarea 8.2.1: Crear clase Project en models.py
```python
class Project:
    def __init__(self):
        self.id = None
        self.name = ""
        self.description = ""
        self.is_active = True
        self.transmission_status = 'INACTIVE'
        self.created_at = None
        self.updated_at = None
        self.devices = []
    
    def add_device(self, device_id):
        """Agregar dispositivo al proyecto"""
        if not self.has_device(device_id):
            # Lógica para agregar relación en project_devices
            return True
        return False
    
    def remove_device(self, device_id):
        """Remover dispositivo del proyecto"""
        # Lógica para eliminar relación en project_devices
        pass
    
    def has_device(self, device_id):
        """Verificar si dispositivo pertenece al proyecto"""
        pass
    
    def get_devices(self):
        """Obtener todos los dispositivos del proyecto"""
        pass
    
    def get_devices_count(self):
        """Obtener cantidad de dispositivos en el proyecto"""
        pass
    
    def validate_transmission_requirements(self):
        """Validar que dispositivos tengan conexiones configuradas"""
        issues = []
        for device in self.get_devices():
            if not device.has_active_connections():
                issues.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'issue': 'NO_ACTIVE_CONNECTIONS'
                })
            if not device.has_csv_data():
                issues.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'issue': 'NO_CSV_DATA'
                })
        return issues
```

#### Subtarea 8.2.2: Implementar gestor de operaciones masivas
```python
class ProjectOperationManager:
    def __init__(self):
        self.transmission_manager = TransmissionManager()
        self.scheduler = TransmissionScheduler()
    
    def start_project_transmission(self, project_id, connection_id=None):
        """Iniciar transmisión automática para todos los dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            raise ValueError("Proyecto no encontrado")
        
        devices = project.get_devices()
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
                
                # Iniciar transmisión para el dispositivo
                success = self.scheduler.schedule_transmission(device.id, target_connection, device.transmission_frequency)
                
                if success:
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
                    
            except Exception as e:
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'status': 'FAILED',
                    'message': str(e)
                })
                failed += 1
        
        # Actualizar estado del proyecto
        if successful > 0:
            project.transmission_status = 'ACTIVE'
            project.save()
        
        return {
            'total_devices': len(devices),
            'successful_operations': successful,
            'failed_operations': failed,
            'results': results
        }
    
    def pause_project_transmission(self, project_id):
        """Pausar transmisiones de todos los dispositivos del proyecto"""
        return self._execute_bulk_operation(project_id, 'PAUSE')
    
    def resume_project_transmission(self, project_id):
        """Reanudar transmisiones de todos los dispositivos del proyecto"""
        return self._execute_bulk_operation(project_id, 'RESUME')
    
    def stop_project_transmission(self, project_id):
        """Parar transmisiones de todos los dispositivos del proyecto"""
        result = self._execute_bulk_operation(project_id, 'STOP')
        
        # Actualizar estado del proyecto
        project = Project.get_by_id(project_id)
        if project:
            project.transmission_status = 'INACTIVE'
            project.save()
        
        return result
    
    def _execute_bulk_operation(self, project_id, operation):
        """Ejecutar operación masiva en dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        devices = project.get_devices()
        results = []
        successful = 0
        failed = 0
        
        for device in devices:
            try:
                success = False
                message = ""
                
                if operation == 'PAUSE':
                    success = self.scheduler.pause_transmission(device.id, device.get_default_connection_id())
                    message = "Transmisión pausada" if success else "Error al pausar transmisión"
                elif operation == 'RESUME':
                    success = self.scheduler.resume_transmission(device.id, device.get_default_connection_id())
                    message = "Transmisión reanudada" if success else "Error al reanudar transmisión"
                elif operation == 'STOP':
                    success = self.scheduler.stop_transmission(device.id, device.get_default_connection_id())
                    message = "Transmisión detenida" if success else "Error al detener transmisión"
                
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
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'status': 'FAILED',
                    'message': str(e)
                })
                failed += 1
        
        return {
            'total_devices': len(devices),
            'successful_operations': successful,
            'failed_operations': failed,
            'results': results
        }
    
    def get_project_transmission_history(self, project_id, limit=100, offset=0):
        """Obtener historial de transmisiones de todos los dispositivos del proyecto"""
        project = Project.get_by_id(project_id)
        if not project:
            return []
        
        device_ids = [device.id for device in project.get_devices()]
        
        # Query para obtener transmisiones de todos los dispositivos del proyecto
        history = db.session.query(DeviceTransmission)\
            .filter(DeviceTransmission.device_id.in_(device_ids))\
            .order_by(DeviceTransmission.transmission_time.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()
        
        return [transmission.to_dict() for transmission in history]
```

### 8.3 API Backend para Gestión de Proyectos

#### Subtarea 8.3.1: Rutas CRUD de proyectos
```python
# GET /api/projects - Listar todos los proyectos
@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.get_all()
    return jsonify([project.to_dict() for project in projects])

# POST /api/projects - Crear nuevo proyecto
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    
    # Validaciones
    if not data.get('name'):
        return jsonify({'error': 'Nombre del proyecto requerido'}), 400
    
    if Project.name_exists(data['name']):
        return jsonify({'error': 'Ya existe un proyecto con ese nombre'}), 400
    
    project = Project()
    project.name = data['name']
    project.description = data.get('description', '')
    project.save()
    
    return jsonify(project.to_dict()), 201

# GET /api/projects/<id> - Obtener proyecto específico
@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    return jsonify(project.to_dict_detailed())

# PUT /api/projects/<id> - Actualizar proyecto
@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        if Project.name_exists(data['name'], exclude_id=project_id):
            return jsonify({'error': 'Ya existe un proyecto con ese nombre'}), 400
        project.name = data['name']
    
    if 'description' in data:
        project.description = data['description']
    
    project.save()
    return jsonify(project.to_dict())

# DELETE /api/projects/<id> - Eliminar proyecto
@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    # Parar transmisiones activas antes de eliminar
    if project.transmission_status in ['ACTIVE', 'PAUSED']:
        operation_manager = ProjectOperationManager()
        operation_manager.stop_project_transmission(project_id)
    
    project.delete()  # Esto desvinculará automáticamente los dispositivos
    return jsonify({'message': 'Proyecto eliminado correctamente'})
```

#### Subtarea 8.3.2: Rutas de gestión de dispositivos en proyectos
```python
# GET /api/projects/<id>/devices - Obtener dispositivos del proyecto
@app.route('/api/projects/<int:project_id>/devices', methods=['GET'])
def get_project_devices(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    devices = project.get_devices()
    return jsonify([device.to_dict() for device in devices])

# POST /api/projects/<id>/devices - Agregar dispositivos al proyecto
@app.route('/api/projects/<int:project_id>/devices', methods=['POST'])
def add_devices_to_project(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    data = request.get_json()
    device_ids = data.get('device_ids', [])
    
    results = []
    for device_id in device_ids:
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
                'status': 'SUCCESS',
                'message': 'Dispositivo agregado al proyecto'
            })
        else:
            results.append({
                'device_id': device_id,
                'status': 'FAILED',
                'message': 'Dispositivo ya pertenece al proyecto'
            })
    
    return jsonify({'results': results})

# DELETE /api/projects/<id>/devices/<device_id> - Remover dispositivo del proyecto
@app.route('/api/projects/<int:project_id>/devices/<int:device_id>', methods=['DELETE'])
def remove_device_from_project(project_id, device_id):
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    
    if project.remove_device(device_id):
        return jsonify({'message': 'Dispositivo removido del proyecto'})
    else:
        return jsonify({'error': 'Dispositivo no pertenece al proyecto'}), 400

# GET /api/devices/unassigned - Dispositivos sin proyecto asignado
@app.route('/api/devices/unassigned', methods=['GET'])
def get_unassigned_devices():
    devices = Device.get_unassigned()
    return jsonify([device.to_dict() for device in devices])
```

#### Subtarea 8.3.3: Rutas de control masivo de transmisiones
```python
# POST /api/projects/<id>/start-transmission - Iniciar transmisiones del proyecto
@app.route('/api/projects/<int:project_id>/start-transmission', methods=['POST'])
def start_project_transmission(project_id):
    data = request.get_json()
    connection_id = data.get('connection_id')  # Opcional: usar conexión específica
    
    operation_manager = ProjectOperationManager()
    result = operation_manager.start_project_transmission(project_id, connection_id)
    
    return jsonify(result)

# POST /api/projects/<id>/pause-transmission - Pausar transmisiones del proyecto
@app.route('/api/projects/<int:project_id>/pause-transmission', methods=['POST'])
def pause_project_transmission(project_id):
    operation_manager = ProjectOperationManager()
    result = operation_manager.pause_project_transmission(project_id)
    
    # Actualizar estado del proyecto
    project = Project.get_by_id(project_id)
    if project and result['successful_operations'] > 0:
        project.transmission_status = 'PAUSED'
        project.save()
    
    return jsonify(result)

# POST /api/projects/<id>/resume-transmission - Reanudar transmisiones del proyecto
@app.route('/api/projects/<int:project_id>/resume-transmission', methods=['POST'])
def resume_project_transmission(project_id):
    operation_manager = ProjectOperationManager()
    result = operation_manager.resume_project_transmission(project_id)
    
    # Actualizar estado del proyecto
    project = Project.get_by_id(project_id)
    if project and result['successful_operations'] > 0:
        project.transmission_status = 'ACTIVE'
        project.save()
    
    return jsonify(result)

# POST /api/projects/<id>/stop-transmission - Parar transmisiones del proyecto
@app.route('/api/projects/<int:project_id>/stop-transmission', methods=['POST'])
def stop_project_transmission(project_id):
    operation_manager = ProjectOperationManager()
    result = operation_manager.stop_project_transmission(project_id)
    
    return jsonify(result)

# GET /api/projects/<id>/transmission-history - Historial de transmisiones del proyecto
@app.route('/api/projects/<int:project_id>/transmission-history', methods=['GET'])
def get_project_transmission_history(project_id):
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    operation_manager = ProjectOperationManager()
    history = operation_manager.get_project_transmission_history(project_id, limit, offset)
    
    return jsonify({
        'project_id': project_id,
        'transmissions': history,
        'limit': limit,
        'offset': offset
    })
```

### 8.4 Frontend para Gestión de Proyectos

#### Subtarea 8.4.1: Crear vistas HTML para proyectos
- Vista lista de proyectos con información básica y acciones
- Vista crear/editar proyecto con formulario
- Vista detalle de proyecto con dispositivos asignados
- Modal de selección de dispositivos para asignar al proyecto
- Panel de control masivo de transmisiones por proyecto

#### Subtarea 8.4.2: Implementar formulario de creación/edición de proyectos
- Formulario con validación en tiempo real
- Campos: nombre (obligatorio), descripción (opcional)
- Validación de nombres únicos
- Feedback visual de validaciones

#### Subtarea 8.4.3: Crear interfaz de gestión de dispositivos del proyecto
- Lista de dispositivos actuales en el proyecto
- Botón "Agregar Dispositivos" que abre modal de selección
- Lista de dispositivos disponibles (sin proyecto asignado)
- Checkbox múltiple para selección de dispositivos
- Botones individuales para remover dispositivos del proyecto

#### Subtarea 8.4.4: Implementar panel de control masivo de transmisiones
- Botones: "Iniciar Transmisión", "Pausar", "Reanudar", "Parar"
- Estados visuales del proyecto (INACTIVO/ACTIVO/PAUSADO)
- Indicador de progreso durante operaciones masivas
- Resultados detallados de operaciones (éxitos/fallos)
- Selector de conexión para transmisiones (opcional)

#### Subtarea 8.4.5: Crear vista de historial de transmisiones del proyecto
- Tabla de transmisiones de todos los dispositivos del proyecto
- Filtros por dispositivo, estado, fecha
- Detalles de cada transmisión expandibles
- Paginación para historial extenso
- Exportación a CSV/JSON

### 8.5 JavaScript para Gestión de Proyectos

#### Subtarea 8.5.1: Extender API client para proyectos
```javascript
const ProjectAPI = {
  // CRUD de proyectos
  getProjects: () => fetch('/api/projects'),
  createProject: (data) => fetch('/api/projects', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }),
  getProject: (id) => fetch(`/api/projects/${id}`),
  updateProject: (id, data) => fetch(`/api/projects/${id}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }),
  deleteProject: (id) => fetch(`/api/projects/${id}`, {method: 'DELETE'}),
  
  // Gestión de dispositivos
  getProjectDevices: (id) => fetch(`/api/projects/${id}/devices`),
  addDevicesToProject: (projectId, deviceIds) => fetch(`/api/projects/${projectId}/devices`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({device_ids: deviceIds})
  }),
  removeDeviceFromProject: (projectId, deviceId) => 
    fetch(`/api/projects/${projectId}/devices/${deviceId}`, {method: 'DELETE'}),
  getUnassignedDevices: () => fetch('/api/devices/unassigned'),
  
  // Control de transmisiones
  startProjectTransmission: (projectId, connectionId) => fetch(`/api/projects/${projectId}/start-transmission`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({connection_id: connectionId})
  }),
  pauseProjectTransmission: (projectId) => fetch(`/api/projects/${projectId}/pause-transmission`, {method: 'POST'}),
  resumeProjectTransmission: (projectId) => fetch(`/api/projects/${projectId}/resume-transmission`, {method: 'POST'}),
  stopProjectTransmission: (projectId) => fetch(`/api/projects/${projectId}/stop-transmission`, {method: 'POST'}),
  
  // Historial
  getProjectTransmissionHistory: (projectId, limit, offset) => 
    fetch(`/api/projects/${projectId}/transmission-history?limit=${limit}&offset=${offset}`)
};
```

#### Subtarea 8.5.2: Implementar controlador de operaciones masivas
```javascript
class ProjectTransmissionController {
  constructor(projectId) {
    this.projectId = projectId;
    this.isOperationInProgress = false;
    this.initializeEventListeners();
  }
  
  initializeEventListeners() {
    document.getElementById('btn-start-transmission').addEventListener('click', () => this.startTransmission());
    document.getElementById('btn-pause-transmission').addEventListener('click', () => this.pauseTransmission());
    document.getElementById('btn-resume-transmission').addEventListener('click', () => this.resumeTransmission());
    document.getElementById('btn-stop-transmission').addEventListener('click', () => this.stopTransmission());
  }
  
  async startTransmission() {
    if (this.isOperationInProgress) return;
    
    const connectionId = document.getElementById('connection-selector').value;
    
    if (!connectionId) {
      this.showError('Debe seleccionar una conexión para la transmisión');
      return;
    }
    
    this.setOperationInProgress(true);
    
    try {
      const response = await ProjectAPI.startProjectTransmission(this.projectId, connectionId);
      const result = await response.json();
      
      this.showOperationResults('Iniciar Transmisión', result);
      this.updateProjectStatus();
      
    } catch (error) {
      this.showError('Error al iniciar transmisiones: ' + error.message);
    } finally {
      this.setOperationInProgress(false);
    }
  }
  
  async pauseTransmission() {
    if (this.isOperationInProgress) return;
    
    this.setOperationInProgress(true);
    
    try {
      const response = await ProjectAPI.pauseProjectTransmission(this.projectId);
      const result = await response.json();
      
      this.showOperationResults('Pausar Transmisión', result);
      this.updateProjectStatus();
      
    } catch (error) {
      this.showError('Error al pausar transmisiones: ' + error.message);
    } finally {
      this.setOperationInProgress(false);
    }
  }
  
  showOperationResults(operation, result) {
    const modal = document.getElementById('operation-results-modal');
    const title = modal.querySelector('.operation-title');
    const summary = modal.querySelector('.operation-summary');
    const details = modal.querySelector('.operation-details');
    
    title.textContent = `Resultado: ${operation}`;
    summary.innerHTML = `
      <div class="result-summary">
        <span class="total">Total: ${result.total_devices}</span>
        <span class="success">Éxitos: ${result.successful_operations}</span>
        <span class="failed">Fallos: ${result.failed_operations}</span>
      </div>
    `;
    
    details.innerHTML = result.results.map(r => `
      <div class="device-result ${r.status.toLowerCase()}">
        <strong>${r.device_name}</strong>
        <span class="status">${r.status}</span>
        <span class="message">${r.message}</span>
      </div>
    `).join('');
    
    modal.style.display = 'block';
  }
}
```

### 8.6 Validaciones y Reglas de Negocio para Proyectos

#### Subtarea 8.6.1: Validaciones de integridad
- Un proyecto no puede tener nombre vacío o duplicado
- Un dispositivo puede pertenecer a múltiples proyectos
- No se puede eliminar un proyecto con transmisiones activas sin confirmar
- Validar que dispositivos tengan conexiones antes de iniciar transmisiones masivas

#### Subtarea 8.6.2: Reglas de operaciones masivas
- Solo permitir operaciones si hay dispositivos en el proyecto
- Mostrar advertencias si algunos dispositivos no tienen conexiones configuradas
- Registrar todas las operaciones masivas en logs de auditoría
- Limitar operaciones concurrentes por proyecto

## FASE 9: TESTING (Prioridad Media)

### 9.1 Tests Backend
#### Subtarea 9.1.1: Tests unitarios para modelos
#### Subtarea 9.1.2: Tests para rutas API
#### Subtarea 9.1.3: Tests para procesamiento CSV
#### Subtarea 9.1.4: Tests de integración
#### Subtarea 9.1.5: Tests para sistema de conexiones
- Tests de validación de configuraciones MQTT/HTTPS
- Tests de encriptación/desencriptación de credenciales
- Tests de clientes MQTT y HTTPS (con mocks)
- Tests de pruebas de conectividad
#### Subtarea 9.1.6: Tests para tipología y transmisión de dispositivos
- Tests de comportamiento por tipo de dispositivo (WebApp vs Sensor)
- Tests del sistema de programación de tareas
- Tests de transmisiones secuenciales para Sensor
- Tests de transmisiones completas para WebApp
- Tests del sistema de logging de transmisiones
- Tests de validaciones específicas por tipo
#### Subtarea 9.1.7: Tests para sistema de proyectos
- Tests CRUD de proyectos
- Tests de asignación/desasignación de dispositivos
- Tests de operaciones masivas de transmisión
- Tests de historial de transmisiones por proyecto
- Tests de validaciones de integridad
- Tests de eliminación segura de proyectos

### 9.2 Tests Frontend
#### Subtarea 9.2.1: Tests de componentes JavaScript
#### Subtarea 9.2.2: Tests de integración con API
#### Subtarea 9.2.3: Tests de formularios dinámicos de conexiones
#### Subtarea 9.2.4: Tests de interfaz de usuario para conexiones
#### Subtarea 9.2.5: Tests de controles de transmisión
#### Subtarea 9.2.6: Tests de gestión de proyectos
#### Subtarea 9.2.7: Tests de operaciones masivas en proyectos

## FASE 10: DOCUMENTACIÓN (Prioridad Baja)

### 10.1 Documentación Técnica
#### Subtarea 10.1.1: Documentar endpoints API
#### Subtarea 10.1.2: Crear README con instrucciones
#### Subtarea 10.1.3: Documentar estructura del proyecto
#### Subtarea 10.1.4: Documentar sistema de conexiones
- Guía de configuración para diferentes tipos de conexión
- Ejemplos de configuración MQTT y HTTPS
- Documentación de seguridad y mejores prácticas
- Guía de troubleshooting para problemas de conectividad
#### Subtarea 10.1.5: Documentar sistema de tipología y transmisión
- Guía de configuración por tipo de dispositivo
- Ejemplos de formatos de transmisión WebApp vs Sensor
- Documentación del sistema de programación automática
- Guía de monitoreo y troubleshooting de transmisiones
#### Subtarea 10.1.6: Documentar sistema de proyectos
- Guía de gestión de proyectos y asignación de dispositivos
- Documentación de operaciones masivas
- Ejemplos de casos de uso para proyectos
- Mejores prácticas para organización por proyectos

## Orden de Ejecución Recomendado

- **Semana 1**: Fases 1-2 (Base de datos, modelos, lógica)
- **Semana 2**: Fase 3 (API completa)
- **Semana 3**: Fase 4 (Frontend completo)
- **Semana 4**: Fase 5 (Docker, containerización)
- **Semana 5**: Fase 6 (Sistema de conexiones externas)
- **Semana 6**: Fase 7 (Sistema de tipología y transmisión)
- **Semana 7**: Fase 8 (Sistema de gestión de proyectos)
- **Semana 8**: Fases 9-10 (Testing y documentación)

## Resumen de Funcionalidades del Sistema

### **Gestión de Dispositivos**
- Crear, editar, eliminar dispositivos
- Upload y procesamiento de archivos CSV
- Tipología: WebApp (envío completo) vs Sensor (envío secuencial)
- Sistema de referencias alfanuméricas automáticas

### **Sistema de Conexiones Externas**
- Soporte para MQTT (Mosquitto) y HTTPS (REST API)
- Múltiples tipos de autenticación (User/Pass, Token, API Key)
- Pruebas de conectividad con historial
- Encriptación segura de credenciales

### **Control de Transmisiones**
- Transmisiones automáticas programadas por frecuencia
- Control manual: Transmitir Ahora, Pausar, Reanudar, Parar
- Estados inteligentes que previenen conflictos
- Historial completo de transmisiones

### **Gestión de Proyectos**
- Agrupación lógica de dispositivos relacionados
- Operaciones masivas: control de transmisiones por lote
- Asignación flexible de dispositivos a proyectos
- Historial centralizado por proyecto

### **Infraestructura y Deployment**
- Containerización con Docker
- Base de datos SQLite con esquemas optimizados
- API RESTful completa
- Frontend SPA responsive con JavaScript vanilla
- Sistema de logging y auditoría