# Plan de Implementación V2 - Device Simulator
## Fases de Mejora Post-Implementación (9-13)

### Estado Actual
- **Fases 1-8**: ✅ COMPLETADAS
- **Estado del Proyecto**: Funcional pero requiere mejoras críticas de seguridad y rendimiento
- **Objetivo**: Transformar de prototipo funcional a solución enterprise-ready

---

## FASE 9: SISTEMA DE INTERNACIONALIZACIÓN (i18n) - MULTILENGUAJE (Prioridad Media)

### 9.1 Análisis y Diseño del Sistema de Internacionalización

#### Descripción del Requerimiento
El sistema debe soportar múltiples idiomas (inglés y español) proporcionando una experiencia de usuario completamente localizada. Esto incluye la traducción de toda la interfaz de usuario, mensajes de error, notificaciones, emails y contenido dinámico generado por el sistema.

**Características Principales:**
- **Idiomas Soportados**: Inglés (EN) como predeterminado y Español (ES)
- **Detección Automática**: Detectar idioma del navegador del usuario
- **Persistencia**: Recordar preferencia de idioma del usuario
- **Cambio Dinámico**: Cambiar idioma sin recargar la página
- **Localización Completa**: UI, mensajes de error, validaciones, fechas, números
- **Contenido Backend**: Respuestas de API y logs en idioma seleccionado

#### Subtarea 9.1.1: Definir estructura de archivos de traducción
```javascript
// Estructura de carpetas
/frontend
  /locales
    /en
      common.json
      devices.json
      connections.json
      projects.json
      transmissions.json
      errors.json
    /es
      common.json
      devices.json
      connections.json
      projects.json
      transmissions.json
      errors.json
```

#### Subtarea 9.1.2: Diseñar esquema de base de datos para preferencias de idioma
```sql
-- Tabla para preferencias de usuario (futuro)
CREATE TABLE user_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT UNIQUE,
  language_code TEXT NOT NULL DEFAULT 'en' CHECK(language_code IN ('en', 'es')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índice para optimizar consultas por sesión
CREATE INDEX idx_user_preferences_session ON user_preferences(session_id);
```

#### Subtarea 9.1.3: Definir estructura de archivos de traducción JSON
```json
// /locales/en/common.json
{
  "app": {
    "title": "Device Manager",
    "subtitle": "IoT Data Transmission Platform"
  },
  "navigation": {
    "devices": "Devices",
    "connections": "Connections",
    "projects": "Projects",
    "dashboard": "Dashboard"
  },
  "actions": {
    "create": "Create",
    "edit": "Edit",
    "delete": "Delete",
    "save": "Save",
    "cancel": "Cancel",
    "confirm": "Confirm",
    "back": "Back",
    "next": "Next",
    "search": "Search",
    "filter": "Filter",
    "export": "Export"
  },
  "status": {
    "active": "Active",
    "inactive": "Inactive",
    "loading": "Loading...",
    "success": "Success",
    "error": "Error",
    "warning": "Warning"
  },
  "language": {
    "current": "English",
    "switch_to": "Switch to Spanish",
    "label": "Language"
  }
}

// /locales/es/common.json
{
  "app": {
    "title": "Gestor de Dispositivos",
    "subtitle": "Plataforma de Transmisión de Datos IoT"
  },
  "navigation": {
    "devices": "Dispositivos",
    "connections": "Conexiones",
    "projects": "Proyectos",
    "dashboard": "Panel"
  },
  "actions": {
    "create": "Crear",
    "edit": "Editar",
    "delete": "Eliminar",
    "save": "Guardar",
    "cancel": "Cancelar",
    "confirm": "Confirmar",
    "back": "Atrás",
    "next": "Siguiente",
    "search": "Buscar",
    "filter": "Filtrar",
    "export": "Exportar"
  },
  "status": {
    "active": "Activo",
    "inactive": "Inactivo",
    "loading": "Cargando...",
    "success": "Éxito",
    "error": "Error",
    "warning": "Advertencia"
  },
  "language": {
    "current": "Español",
    "switch_to": "Cambiar a Inglés",
    "label": "Idioma"
  }
}
```

### 9.2 Sistema de Traducción Frontend

#### Subtarea 9.2.1: Implementar clase I18n para gestión de traducciones
```javascript
class I18n {
  constructor() {
    this.currentLanguage = this.detectLanguage();
    this.translations = {};
    this.fallbackLanguage = 'en';
    this.loadedNamespaces = new Set();
  }
  
  detectLanguage() {
    // 1. Comprobar localStorage
    const stored = localStorage.getItem('preferred_language');
    if (stored && ['en', 'es'].includes(stored)) {
      return stored;
    }
    
    // 2. Comprobar idioma del navegador
    const browserLang = navigator.language.split('-')[0];
    if (['en', 'es'].includes(browserLang)) {
      return browserLang;
    }
    
    // 3. Fallback a inglés
    return 'en';
  }
  
  async loadNamespace(namespace) {
    if (this.loadedNamespaces.has(`${this.currentLanguage}-${namespace}`)) {
      return;
    }
    
    try {
      const response = await fetch(`/locales/${this.currentLanguage}/${namespace}.json`);
      const translations = await response.json();
      
      if (!this.translations[this.currentLanguage]) {
        this.translations[this.currentLanguage] = {};
      }
      
      this.translations[this.currentLanguage][namespace] = translations;
      this.loadedNamespaces.add(`${this.currentLanguage}-${namespace}`);
      
    } catch (error) {
      console.warn(`Failed to load translations for ${namespace}:`, error);
      
      // Cargar fallback si no está disponible el idioma actual
      if (this.currentLanguage !== this.fallbackLanguage) {
        try {
          const fallbackResponse = await fetch(`/locales/${this.fallbackLanguage}/${namespace}.json`);
          const fallbackTranslations = await fallbackResponse.json();
          
          if (!this.translations[this.fallbackLanguage]) {
            this.translations[this.fallbackLanguage] = {};
          }
          
          this.translations[this.fallbackLanguage][namespace] = fallbackTranslations;
        } catch (fallbackError) {
          console.error(`Failed to load fallback translations:`, fallbackError);
        }
      }
    }
  }
  
  t(key, options = {}) {
    const keys = key.split('.');
    const namespace = keys[0];
    const translationKey = keys.slice(1).join('.');
    
    // Buscar en idioma actual
    let translation = this.getTranslation(this.currentLanguage, namespace, translationKey);
    
    // Fallback a idioma por defecto
    if (!translation && this.currentLanguage !== this.fallbackLanguage) {
      translation = this.getTranslation(this.fallbackLanguage, namespace, translationKey);
    }
    
    // Fallback a la clave original
    if (!translation) {
      translation = key;
    }
    
    // Interpolación de variables
    return this.interpolate(translation, options);
  }
  
  getTranslation(language, namespace, key) {
    if (!this.translations[language] || !this.translations[language][namespace]) {
      return null;
    }
    
    return this.getNestedValue(this.translations[language][namespace], key);
  }
  
  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : null;
    }, obj);
  }
  
  interpolate(text, options) {
    if (!options || typeof text !== 'string') {
      return text;
    }
    
    return text.replace(/\{\{([^}]+)\}\}/g, (match, key) => {
      const trimmedKey = key.trim();
      return options[trimmedKey] !== undefined ? options[trimmedKey] : match;
    });
  }
  
  async changeLanguage(language) {
    if (!['en', 'es'].includes(language)) {
      throw new Error(`Unsupported language: ${language}`);
    }
    
    this.currentLanguage = language;
    localStorage.setItem('preferred_language', language);
    
    // Recargar todas las traducciones cargadas
    const namespacesToReload = Array.from(this.loadedNamespaces)
      .map(item => item.split('-')[1])
      .filter((item, index, arr) => arr.indexOf(item) === index);
    
    this.loadedNamespaces.clear();
    
    for (const namespace of namespacesToReload) {
      await this.loadNamespace(namespace);
    }
    
    // Actualizar interfaz
    this.updateDOM();
    
    // Notificar cambio de idioma
    document.dispatchEvent(new CustomEvent('languageChanged', {
      detail: { language }
    }));
  }
}
```

---

## FASE 10: SEGURIDAD Y AUTENTICACIÓN (Prioridad CRÍTICA)
**Duración Estimada**: 1-2 semanas

### 10.1 Sistema de Autenticación JWT

#### Subtarea 10.1.1: Configurar dependencias de autenticación
```bash
# Actualizar requirements.txt
Flask-JWT-Extended==4.5.2
bcrypt==4.0.1
```

#### Subtarea 10.1.2: Crear modelo de Usuario
```python
# backend/app/models.py - Agregar clase User
class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 role='user', is_active=True, created_at=None):
        # Implementar modelo de usuario con rol único
```

#### Subtarea 10.1.3: Implementar sistema de autenticación
```python
# backend/app/auth.py - Nuevo archivo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash

class AuthManager:
    def __init__(self, app):
        self.jwt = JWTManager(app)
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
```

#### Subtarea 10.1.4: Crear rutas de autenticación
```python
# backend/app/routes/auth.py - Nuevo archivo
@auth_bp.route('/api/auth/login', methods=['POST'])
@auth_bp.route('/api/auth/register', methods=['POST'])
@auth_bp.route('/api/auth/refresh', methods=['POST'])
@auth_bp.route('/api/auth/logout', methods=['DELETE'])
```

#### Subtarea 10.1.5: Proteger rutas existentes
- Agregar `@jwt_required()` a todas las rutas sensibles
- Implementar middleware de autorización por roles
- Crear decorador personalizado para permisos

### 10.2 Encriptación de Credenciales

#### Subtarea 10.2.1: Implementar sistema de encriptación
```python
# backend/app/encryption.py - Nuevo archivo
from cryptography.fernet import Fernet
import os
import base64

class CredentialEncryption:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
```

#### Subtarea 10.2.2: Migrar credenciales existentes
- Script de migración para encriptar auth_config existentes
- Actualizar modelo Connection para manejar encriptación automática
- Implementar métodos encrypt_auth_config() y decrypt_auth_config()

#### Subtarea 10.2.3: Actualizar clientes de conexión
- Modificar MQTTClient y HTTPSClient para desencriptar credenciales
- Implementar manejo seguro de credenciales en memoria
- Agregar logging de acceso a credenciales (sin exponer valores)

### 10.3 Configuración de Seguridad

#### Subtarea 10.3.1: Configurar CORS restrictivo
```python
# backend/app/app.py
CORS(app, origins=[
    'http://localhost:3000',  # Desarrollo
    'https://yourdomain.com'  # Producción
])
```

#### Subtarea 10.3.2: Implementar validación de entrada robusta
```python
# backend/app/validators.py - Extender
from marshmallow import Schema, fields, validate

class DeviceSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=500))
```

#### Subtarea 10.3.3: Configurar headers de seguridad
```python
# Agregar headers de seguridad HTTP
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

### 10.4 Frontend - Integración de Autenticación

#### Subtarea 10.4.1: Crear sistema de autenticación en frontend
```javascript
// frontend/static/auth.js - Nuevo archivo
class AuthManager {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }
    
    async login(username, password) { /* ... */ }
    async logout() { /* ... */ }
    async refreshAccessToken() { /* ... */ }
}
```

#### Subtarea 10.4.2: Implementar interceptor de requests
```javascript
// Agregar token JWT a todas las requests
const API = {
    async request(url, options = {}) {
        const token = AuthManager.getToken();
        if (token) {
            options.headers = {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            };
        }
        return fetch(url, options);
    }
};
```

#### Subtarea 10.4.3: Crear UI de login
```html
<!-- frontend/static/login.html - Nueva vista -->
<div id="login-view" class="auth-view">
    <form id="login-form">
        <input type="text" id="username" required>
        <input type="password" id="password" required>
        <button type="submit">Iniciar Sesión</button>
    </form>
</div>
```

---

## FASE 11: OPTIMIZACIÓN DE RENDIMIENTO (Prioridad ALTA)
**Duración Estimada**: 1 semana

### 11.1 Migración a SQLAlchemy

#### Subtarea 11.1.1: Configurar SQLAlchemy
```python
# backend/app/database.py - Reemplazar implementación actual
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

#### Subtarea 11.1.2: Convertir modelos a SQLAlchemy ORM
```python
# backend/app/models.py - Refactorizar
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    reference = Column(String(8), unique=True, nullable=False)
    # ... resto de campos
```

#### Subtarea 11.1.3: Implementar session management
```python
# backend/app/database.py
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### 11.2 Implementar Paginación

#### Subtarea 11.2.1: Crear clase base para paginación
```python
# backend/app/pagination.py - Nuevo archivo
class PaginationHelper:
    @staticmethod
    def paginate(query, page=1, per_page=20):
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
```

#### Subtarea 11.2.2: Actualizar endpoints con paginación
```python
# Ejemplo: backend/app/routes/devices.py
@devices_bp.route('/devices', methods=['GET'])
def get_devices():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    with get_db_session() as session:
        query = session.query(Device)
        result = PaginationHelper.paginate(query, page, per_page)
        return jsonify(result)
```

#### Subtarea 11.2.3: Actualizar frontend para paginación
```javascript
// frontend/static/pagination.js - Nuevo archivo
class PaginationComponent {
    constructor(containerId, onPageChange) {
        this.container = document.getElementById(containerId);
        this.onPageChange = onPageChange;
    }
    
    render(currentPage, totalPages) { /* ... */ }
}
```

### 11.3 Optimización de Consultas

#### Subtarea 11.3.1: Crear índices de base de datos
```sql
-- Agregar índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_transmission_enabled ON devices(transmission_enabled);
CREATE INDEX IF NOT EXISTS idx_transmissions_device_time ON device_transmissions(device_id, transmission_time);
CREATE INDEX IF NOT EXISTS idx_connections_active ON connections(is_active);
```

#### Subtarea 11.3.2: Optimizar consultas específicas
```python
# Reemplazar SELECT * con campos específicos
def get_devices_summary():
    return session.query(
        Device.id, 
        Device.name, 
        Device.reference, 
        Device.device_type,
        Device.transmission_enabled
    ).all()
```

#### Subtarea 11.3.3: Implementar eager loading
```python
# Para relaciones, usar joinedload para evitar N+1 queries
from sqlalchemy.orm import joinedload

def get_project_with_devices(project_id):
    return session.query(Project)\
        .options(joinedload(Project.devices))\
        .filter(Project.id == project_id)\
        .first()
```

### 11.4 Sistema de Cache

#### Subtarea 11.4.1: Configurar Redis
```python
# backend/requirements.txt - Agregar
redis==4.6.0
flask-caching==2.1.0

# backend/app/cache.py - Nuevo archivo
from flask_caching import Cache
cache = Cache()
```

#### Subtarea 11.4.2: Implementar cache en endpoints frecuentes
```python
@devices_bp.route('/devices/<int:device_id>', methods=['GET'])
@cache.cached(timeout=300, key_prefix='device')
def get_device(device_id):
    # Cache por 5 minutos
    pass
```

#### Subtarea 11.4.3: Cache invalidation strategy
```python
# Invalidar cache cuando se modifica un dispositivo
@devices_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    # Actualizar dispositivo
    cache.delete(f'device::{device_id}')
    return jsonify(result)
```

---

## FASE 12: OBSERVABILIDAD Y MONITOREO (Prioridad MEDIA)
**Duración Estimada**: 1 semana

### 12.1 Logging Estructurado

#### Subtarea 12.1.1: Configurar logging avanzado
```python
# backend/requirements.txt - Agregar
structlog==23.1.0
python-json-logger==2.0.7

# backend/app/logging_config.py - Nuevo archivo
import structlog
import logging
from pythonjsonlogger import jsonlogger

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

#### Subtarea 12.1.2: Implementar logging en operaciones críticas
```python
# Ejemplo de logging estructurado
logger = structlog.get_logger()

def start_transmission(device_id, connection_id):
    logger.info(
        "transmission_started",
        device_id=device_id,
        connection_id=connection_id,
        user_id=get_current_user_id()
    )
```

#### Subtarea 12.1.3: Crear middleware de logging de requests
```python
@app.before_request
def log_request_info():
    logger.info(
        "request_started",
        method=request.method,
        url=request.url,
        remote_addr=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
```

### 12.2 Métricas y Monitoreo

#### Subtarea 12.2.1: Implementar health checks
```python
# backend/app/routes/health.py - Nuevo archivo
@health_bp.route('/health', methods=['GET'])
def health_check():
    checks = {
        'database': check_database_connection(),
        'scheduler': check_scheduler_status(),
        'redis': check_redis_connection() if REDIS_ENABLED else True
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    })
```

#### Subtarea 12.2.2: Métricas de rendimiento
```python
# backend/app/metrics.py - Nuevo archivo
import time
from functools import wraps

def track_execution_time(operation_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    "operation_completed",
                    operation=operation_name,
                    execution_time=execution_time,
                    status="success"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "operation_failed",
                    operation=operation_name,
                    execution_time=execution_time,
                    error=str(e),
                    status="error"
                )
                raise
        return wrapper
    return decorator
```

#### Subtarea 12.2.3: Dashboard de monitoreo básico
```html
<!-- frontend/static/monitoring.html - Nueva vista -->
<div id="monitoring-view" class="view">
    <h2>🔍 Monitoreo del Sistema</h2>
    <div class="metrics-grid">
        <div class="metric-card">
            <h3>Estado del Sistema</h3>
            <div id="system-status"></div>
        </div>
        <div class="metric-card">
            <h3>Transmisiones Activas</h3>
            <div id="active-transmissions"></div>
        </div>
    </div>
</div>
```

### 12.3 Rate Limiting

#### Subtarea 12.3.1: Configurar Flask-Limiter
```python
# backend/requirements.txt - Agregar
Flask-Limiter==3.5.0

# backend/app/app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)
```

#### Subtarea 12.3.2: Aplicar límites específicos
```python
@devices_bp.route('/devices', methods=['POST'])
@limiter.limit("10 per minute")
def create_device():
    # Limitar creación de dispositivos
    pass

@connections_bp.route('/api/connections/<int:connection_id>/test', methods=['POST'])
@limiter.limit("5 per minute")
def test_connection(connection_id):
    # Limitar pruebas de conexión
    pass
```

---

## FASE 13: TESTING Y CI/CD (Prioridad MEDIA)
**Duración Estimada**: 1 semana

### 13.1 Testing Backend

#### Subtarea 13.1.1: Configurar framework de testing
```python
# backend/requirements-dev.txt - Nuevo archivo
pytest==7.4.0
pytest-flask==1.2.0
pytest-cov==4.1.0
factory-boy==3.3.0
faker==19.3.0
```

#### Subtarea 13.1.2: Tests unitarios para modelos
```python
# backend/tests/test_models.py - Nuevo archivo
import pytest
from app.models import Device, Connection, Project

class TestDevice:
    def test_create_device(self):
        device = Device.create("Test Device", "Description")
        assert device.name == "Test Device"
        assert len(device.reference) == 8
    
    def test_duplicate_device(self):
        original = Device.create("Original", "Desc")
        duplicates = Device.duplicate(original.id, 3)
        assert len(duplicates) == 3
        assert all(d.name.startswith("Original") for d in duplicates)
```

#### Subtarea 13.1.3: Tests de integración para APIs
```python
# backend/tests/test_api.py - Nuevo archivo
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_create_device_api(client):
    response = client.post('/api/devices', json={
        'name': 'Test Device',
        'description': 'Test Description'
    })
    assert response.status_code == 201
    assert 'reference' in response.json
```

#### Subtarea 13.1.4: Tests para sistema de transmisiones
```python
# backend/tests/test_transmissions.py - Nuevo archivo
def test_transmission_scheduling():
    # Test scheduler functionality
    pass

def test_mqtt_client():
    # Test MQTT client with mocks
    pass

def test_https_client():
    # Test HTTPS client with mocks
    pass
```

### 13.2 Testing Frontend

#### Subtarea 13.2.1: Configurar testing framework
```javascript
// package.json - Agregar dependencias de testing
{
  "devDependencies": {
    "jest": "^29.0.0",
    "jsdom": "^22.0.0",
    "@testing-library/dom": "^9.0.0"
  }
}
```

#### Subtarea 13.2.2: Tests para componentes JavaScript
```javascript
// frontend/tests/script.test.js - Nuevo archivo
import { API } from '../static/script.js';

describe('API Functions', () => {
    test('createDevice should make POST request', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({ id: 1, name: 'Test' })
            })
        );
        
        const result = await API.createDevice({ name: 'Test' });
        expect(result.name).toBe('Test');
    });
});
```

#### Subtarea 13.2.3: Tests end-to-end
```javascript
// e2e/device-management.test.js - Nuevo archivo
const puppeteer = require('puppeteer');

describe('Device Management E2E', () => {
    let browser, page;
    
    beforeAll(async () => {
        browser = await puppeteer.launch();
        page = await browser.newPage();
    });
    
    test('should create new device', async () => {
        await page.goto('http://localhost:5000');
        await page.click('#btn-new-device');
        await page.type('#device-name', 'E2E Test Device');
        await page.click('button[type="submit"]');
        
        await page.waitForSelector('.device-card');
        const deviceName = await page.$eval('.device-card h3', el => el.textContent);
        expect(deviceName).toBe('E2E Test Device');
    });
});
```

### 13.3 CI/CD Pipeline

#### Subtarea 13.3.1: Configurar GitHub Actions
```yaml
# .github/workflows/ci.yml - Nuevo archivo
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install -r backend/requirements-dev.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

#### Subtarea 13.3.2: Configurar Docker multi-stage builds
```dockerfile
# backend/Dockerfile - Optimizar
FROM python:3.9-slim as base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest

FROM base as production
COPY . .
CMD ["python", "run.py"]
```

#### Subtarea 13.3.3: Configurar deployment automático
```yaml
# .github/workflows/deploy.yml - Nuevo archivo
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - name: Deploy to server
      run: |
        # Script de deployment
        docker-compose -f docker-compose.prod.yml up -d --build
```

---

## CRONOGRAMA DE IMPLEMENTACIÓN

### **Semana 1: Fase 9 - Internacionalización (i18n)**
- Días 1-2: Análisis, estructura de locales y esquema de preferencias
- Días 3-4: Implementación clase `I18n` y carga de namespaces
- Días 5-6: Integración en UI y detección/persistencia de idioma
- Día 7: Validación, QA y refinamientos

### **Semana 2-3: Fase 10 - Seguridad**
- Días 1-3: Sistema de autenticación JWT
- Días 4-5: Encriptación de credenciales
- Días 6-7: Configuración de seguridad y frontend auth
- Días 8-10: Testing y refinamiento

### **Semana 4: Fase 11 - Rendimiento**
- Días 1-2: Migración a SQLAlchemy
- Días 3-4: Implementación de paginación
- Días 5-6: Optimización de consultas y cache
- Día 7: Testing de rendimiento

### **Semana 5: Fase 12 - Observabilidad**
- Días 1-2: Logging estructurado
- Días 3-4: Métricas y monitoreo
- Días 5-6: Rate limiting y dashboard
- Día 7: Integración y testing

### **Semana 6: Fase 13 - Testing**
- Días 1-2: Tests backend
- Días 3-4: Tests frontend y E2E
- Días 5-6: CI/CD pipeline
- Día 7: Documentación y deployment

---

## CRITERIOS DE ÉXITO

### **Fase 9 - Internacionalización (i18n)**
- ✅ UI completamente traducible (EN/ES)
- ✅ Detección automática + persistencia de preferencia de idioma
- ✅ Cambio de idioma sin recargar (contenido y labels)
- ✅ Estructura de archivos de traducción y fallback funcional

### **Fase 10 - Seguridad**
- ✅ Todas las rutas protegidas con JWT
- ✅ Credenciales encriptadas en base de datos
- ✅ CORS configurado restrictivamente
- ✅ Headers de seguridad implementados

### **Fase 11 - Rendimiento**
- ✅ Tiempo de respuesta < 200ms para endpoints básicos
- ✅ Paginación implementada en todos los listados
- ✅ Connection pooling configurado
- ✅ Cache hit rate > 80% para datos frecuentes

### **Fase 12 - Observabilidad**
- ✅ Logs estructurados en todas las operaciones críticas
- ✅ Health checks respondiendo correctamente
- ✅ Rate limiting funcionando
- ✅ Dashboard de monitoreo operativo

### **Fase 13 - Testing**
- ✅ Cobertura de tests > 80%
- ✅ CI/CD pipeline ejecutándose sin errores
- ✅ Tests E2E cubriendo flujos principales
- ✅ Deployment automático configurado

---

## RECURSOS NECESARIOS

### **Dependencias Nuevas**
```txt
# Seguridad
Flask-JWT-Extended==4.5.2
bcrypt==4.0.1
marshmallow==3.20.1

# Rendimiento
SQLAlchemy==1.4.46
redis==4.6.0
flask-caching==2.1.0

# Observabilidad
structlog==23.1.0
python-json-logger==2.0.7
Flask-Limiter==3.5.0

# Testing
pytest==7.4.0
pytest-flask==1.2.0
pytest-cov==4.1.0
```

### **Infraestructura**
- Redis server para cache y rate limiting
- Servidor de logs (opcional: ELK stack)
- CI/CD runner (GitHub Actions incluido)

### **Configuración de Entorno**
```bash
# Variables de entorno adicionales
JWT_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1
```

---

## NOTAS IMPORTANTES

1. **Migración de Datos**: La Fase 10 requiere migración cuidadosa de SQLite actual a SQLAlchemy ORM
2. **Backward Compatibility**: Mantener compatibilidad con frontend existente durante Fase 9
3. **Testing en Producción**: Implementar feature flags para rollout gradual
4. **Monitoreo**: Configurar alertas para métricas críticas en Fase 11
5. **Documentación**: Actualizar documentación API después de cada fase

Este plan transformará el Device Simulator de un prototipo funcional a una **solución enterprise-ready** con seguridad, rendimiento y observabilidad de nivel producción.
