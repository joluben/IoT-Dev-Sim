# DevSim - Gestión de Dispositivos CSV

Aplicación web para gestión de dispositivos con importación y procesamiento de archivos CSV.

## Características

- 📱 **Gestión de dispositivos**: Crear dispositivos con referencias alfanuméricas únicas
- 📄 **Importación CSV**: Upload con drag & drop y validación de formato
- 👁️ **Previsualización**: Vista lado a lado de CSV y JSON (cabecera + 5 filas)
- 💾 **Almacenamiento**: Base de datos SQLite persistente
- 🐳 **Containerización**: Despliegue completo con Docker

## Stack Tecnológico

- **Backend**: Python Flask + SQLite
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Containerización**: Docker + Docker Compose
- **Proxy**: Nginx

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

2. **Ejecutar con Docker Compose**:
   ```bash
   docker-compose up --build
   ```

3. **Acceder a la aplicación**:
   - Frontend: http://localhost
   - Backend API: http://localhost:5000

### Opción 2: Desarrollo Local

1. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   python run.py
   ```

2. **Frontend**:
   Servir archivos estáticos desde `frontend/static/` con cualquier servidor web.

## API Endpoints

- `POST /api/devices` - Crear dispositivo
- `GET /api/devices` - Listar dispositivos
- `GET /api/devices/<id>` - Obtener dispositivo específico
- `POST /api/devices/<id>/upload` - Subir CSV para previsualización
- `POST /api/devices/<id>/save` - Guardar datos CSV en BD

## Uso de la Aplicación

1. **Crear Dispositivo**: Hacer clic en "Nuevo Dispositivo" y llenar el formulario
2. **Importar CSV**: En el detalle del dispositivo, arrastrar archivo CSV o seleccionarlo
3. **Previsualizar**: Revisar la tabla CSV y JSON generados
4. **Guardar**: Confirmar guardado de datos en base de datos

## Desarrollo

### Comandos Docker Útiles

```bash
# Construir y ejecutar
docker-compose up --build

# Ejecutar en segundo plano
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar servicios
docker-compose down

# Limpiar volúmenes
docker-compose down -v
```

### Estructura de Base de Datos

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

## Licencia

MIT License
