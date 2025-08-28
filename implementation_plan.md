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

#### Subtarea 5.1.1: Crear requirements.txt
```
Flask==2.3.3
pandas==2.0.3
python-dotenv==1.0.0
Flask-CORS==4.0.0
paho-mqtt==1.6.1
requests==2.31.0
```

#### Subtarea 5.1.2: Crear Dockerfile para backend
#### Subtarea 5.1.3: Configurar volúmenes para uploads y BD

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
- **HTTPS REST API**: Servicios web RESTful sobre HTTP/HTTPS

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

## FASE 7: TESTING (Prioridad Media)

### 7.1 Tests Backend
#### Subtarea 7.1.1: Tests unitarios para modelos
#### Subtarea 7.1.2: Tests para rutas API
#### Subtarea 7.1.3: Tests para procesamiento CSV
#### Subtarea 7.1.4: Tests de integración
#### Subtarea 7.1.5: Tests para sistema de conexiones
- Tests de validación de configuraciones MQTT/HTTPS
- Tests de encriptación/desencriptación de credenciales
- Tests de clientes MQTT y HTTPS (con mocks)
- Tests de pruebas de conectividad

### 7.2 Tests Frontend
#### Subtarea 7.2.1: Tests de componentes JavaScript
#### Subtarea 7.2.2: Tests de integración con API
#### Subtarea 7.2.3: Tests de formularios dinámicos de conexiones
#### Subtarea 7.2.4: Tests de interfaz de usuario para conexiones

## FASE 8: DOCUMENTACIÓN (Prioridad Baja)

### 8.1 Documentación Técnica
#### Subtarea 8.1.1: Documentar endpoints API
#### Subtarea 8.1.2: Crear README con instrucciones
#### Subtarea 8.1.3: Documentar estructura del proyecto
#### Subtarea 8.1.4: Documentar sistema de conexiones
- Guía de configuración para diferentes tipos de conexión
- Ejemplos de configuración MQTT y HTTPS
- Documentación de seguridad y mejores prácticas
- Guía de troubleshooting para problemas de conectividad

## Orden de Ejecución Recomendado

- **Semana 1**: Fases 1-2 (Base de datos, modelos, lógica)
- **Semana 2**: Fase 3 (API completa)
- **Semana 3**: Fase 4 (Frontend completo)
- **Semana 4**: Fase 5 (Docker, containerización)
- **Semana 5**: Fase 6 (Sistema de conexiones externas)
- **Semana 6**: Fases 7-8 (Testing y documentación)

**Estimación total**: 5-6 semanas para un desarrollador