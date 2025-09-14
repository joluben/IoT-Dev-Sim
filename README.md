# DevSim - Gestión de Dispositivos CSV

🌐 [Español](./README.md) | [English](./README.en.md)

<a href="https://www.buymeacoffee.com/joluben" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" width="150">
</a>

DevSim es una aplicación diseñada para la simulación avanzada de señales a partir de ficheros CSV. Permite recrear entornos con múltiples dispositivos virtuales que emiten datos de forma controlada, adaptándose a las necesidades de cada escenario de prueba. El usuario puede definir la frecuencia de transmisión y seleccionar entre distintos protocolos de comunicación, como HTTPS y MQTT, lo que convierte a DevSim en una herramienta versátil para el desarrollo, validación e integración de sistemas conectados.

![Listado de dispositivos](./screenshots/image%20devices.jpg)
![Listado de conexiones](./screenshots/image%20connections.jpg)

## Características

- **Gestión integral**: Dispositivos, Proyectos y Conexiones con CRUD completo
- **Duplicación masiva de dispositivos**: Duplicar 1-50 copias con nombres incrementales y referencias únicas
- **Importación CSV**: Carga con validación (tamaño, formato, encoding) y previsualización (cabecera + 5 filas)
- **Previsualización JSON/CSV**: Vista lado a lado con formato legible
- **Conexiones externas**: MQTT, HTTPS y Kafka con autenticación NONE, USER_PASS, TOKEN y API_KEY
- **Transmisiones automáticas**: Programación con APScheduler (WebApp: dataset completo, Sensor: una fila por envío)
- **Transmisión manual**: Envío bajo demanda por conexión
- **i18n**: Traducciones ES/EN servidas desde `frontend/locales/`
- **Tiempo real básico**: Canal WebSocket (`/ws/transmissions`) para estado de conexión
- **Persistencia**: SQLite para datos y scheduler; volúmenes Docker para durabilidad
- **Integración con Keycloak**: Autenticación y autorización con Keycloak

## Stack Tecnológico

- **Backend**: Flask 2.x, SQLAlchemy 1.4, APScheduler 3.10, Flask-CORS, Flask-Sock (WebSocket)
- **Base de datos**: SQLite (datos + scheduler)
- **Conectividad**: paho-mqtt, confluent-kafka, requests, cryptography (gestión de secretos)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla); SPA servida por Nginx en contenedor
- **Internacionalización**: ficheros JSON en `frontend/locales/`
- **Containerización**: Docker y Docker Compose, Nginx como reverse proxy para frontend

## Estructura del Proyecto

```
devsim/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/
│   ├── static/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── script.js
│   ├── nginx.conf
│   └── Dockerfile
├── data/
├── .env
├── docker-compose.yml
└── README.md
```

## Instalación y Uso

### Opción 1: Docker (Recomendado)

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd devsim
   ```

2. **Configurar variables de entorno (opcional)**:
   - Copia `.example.env` a `.env` y ajusta valores según necesidad.

3. **Ejecutar con Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```

4. **Acceder a la aplicación**:
   - Frontend: http://localhost
   - Backend API: http://localhost:5000

5. **Persistencia**:
   - Los datos se almacenan en `./data` (montado en `/app/data`) y uploads en `./backend/uploads`.

### Opción 2: Desarrollo Local

1. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   # source venv/bin/activate
   pip install -r requirements.txt
   python run.py
   ```

2. **Frontend**:
   No es necesario un servidor aparte en desarrollo: el backend sirve el frontend desde `backend/app/app.py`:
   - `GET /` → `frontend/static/index.html`
   - `GET /<path>` → archivos estáticos
   - `GET /locales/<path>` → traducciones
   Accede a http://localhost:5000/

## Límites y Validaciones

- **CSV upload**: Máximo 10MB (`MAX_CONTENT_LENGTH`), validación de extensión y contenido.
- **Duplicación de dispositivos**: Entre 1 y 50 copias por operación.
- **Campos y referencias**: Las referencias de dispositivo son únicas; los duplicados regeneran referencia y reinician `current_row_index`.

## Requisitos de Máquina (Linux)

- **Desarrollo / PoC** (hasta ~1k dispositivos, datasets pequeños):
  - 1 vCPU, 1-2 GB RAM, 1-5 GB disco.
- **Pequeña Producción** (hasta ~10k dispositivos, uso moderado):
  - 2 vCPU, 2-4 GB RAM, 10+ GB disco.
- **Sistema Operativo**: Ubuntu 20.04/22.04 LTS o similar.
- **Dependencias**:
  - Docker 24+ y Docker Compose Plugin.
  - Puertos abiertos: 80 (frontend), 5000 (backend API, si se expone).
- **Almacenamiento**: SSD recomendado; monta `./data` y `./backend/uploads` en volúmenes persistentes.

## Operación y Despliegue

- **Logs**:
  - `docker-compose logs -f backend` y `docker-compose logs -f frontend`.
- **Reinicio programador (scheduler)**:
  - El scheduler se inicia automáticamente; al detener contenedores se apaga limpiamente.
- **Backups**:
  - Copia `./data` y `./backend/uploads` de forma periódica.

## Solución de Problemas

- **Archivo demasiado grande (413)**: Reduce el tamaño del CSV o aumenta `MAX_CONTENT_LENGTH`.
- **Errores 404 de traducciones**: Asegúrate de acceder vía backend (sirve `/locales/...`) o que Nginx copie `frontend/locales/` en el contenedor.
- **Jobs huérfanos del scheduler**: Si cambias masivamente dispositivos/conexiones, reinicia backend. Si persiste, elimina el archivo `scheduler_jobs.db` del volumen de datos (puede estar en `./data`) con el backend detenido y se regenerará.
- **Permisos en Linux**: Si Nginx/Flask no puede leer escribir en volúmenes, ajusta permisos/propietario de `./data` y `./backend/uploads`.

## Uso de la Aplicación

1. **Crear Dispositivo**: Hacer clic en "Nuevo Dispositivo" y llenar el formulario.
2. **Importar CSV**: En el detalle del dispositivo, arrastrar archivo CSV o seleccionarlo.
3. **Previsualizar**: Revisar la tabla CSV y JSON generados.
4. **Guardar**: Confirmar guardado de datos en base de datos.
5. **Transmitir**: Configurar conexión (MQTT/HTTPS/Kafka) y lanzar transmisión manual o automática.

## Licencia

MIT License
Esta aplicación es completamente Open Source, puedes usarla, modificarla y distribuirla libremente.

<a href="https://www.buymeacoffee.com/joluben" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="250">
</a>