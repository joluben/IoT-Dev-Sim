# DevSim - CSV Device Management

🌐 [Español](./README.md) | [English](./README.en.md)

<a href="https://www.buymeacoffee.com/joluben" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" width="150">
</a>

Web application for device management with CSV file import and processing.

![Device list](./screenshots/image%20devices.jpg)
![Connection list](./screenshots/image%20connections.jpg)

## Features

- **Comprehensive management**: Devices, Projects, and Connections with full CRUD support  
- **Bulk device duplication**: Duplicate 1–50 copies with incremental names and unique references  
- **CSV Import**: Upload with validation (size, format, encoding) and preview (header + 5 rows)  
- **JSON/CSV Preview**: Side-by-side view with readable formatting  
- **External connections**: MQTT and HTTPS with authentication NONE, USER_PASS, TOKEN, and API_KEY  
- **Automatic transmissions**: Scheduling with APScheduler (WebApp: full dataset, Sensor: one row per send)  
- **Manual transmission**: On-demand sending per connection  
- **i18n**: ES/EN translations served from `frontend/locales/`  
- **Basic real-time**: WebSocket channel (`/ws/transmissions`) for connection status  
- **Persistence**: SQLite for data and scheduler; Docker volumes for durability  
- **Keycloak integration**: Authentication and authorization with Keycloak  

## Tech Stack

- **Backend**: Flask 2.x, SQLAlchemy 1.4, APScheduler 3.10, Flask-CORS, Flask-Sock (WebSocket)  
- **Database**: SQLite (data + scheduler)  
- **Connectivity**: paho-mqtt, requests, cryptography (secrets management)  
- **Frontend**: HTML5, CSS3, JavaScript (vanilla); SPA served by Nginx in a container  
- **Internationalization**: JSON files in `frontend/locales/`  
- **Containerization**: Docker and Docker Compose, Nginx as reverse proxy for frontend  

## Project Structure

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

## Installation and Usage

### Option 1: Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd devsim
   ```

2. **Configure environment variables (optional)**:
   - Copy `.example.env` to `.env` and adjust values as needed.  

3. **Run with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```

4. **Access the application**:
   - Frontend: http://localhost  
   - Backend API: http://localhost:5000  

5. **Persistence**:
   - Data is stored in `./data` (mounted at `/app/data`) and uploads in `./backend/uploads`.

### Option 2: Local Development

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
   No separate server is needed in development: the backend serves the frontend from `backend/app/app.py`:
   - `GET /` → `frontend/static/index.html`  
   - `GET /<path>` → static files  
   - `GET /locales/<path>` → translations  
   Access http://localhost:5000/  

## Limits and Validations

- **CSV upload**: Maximum 10MB (`MAX_CONTENT_LENGTH`), extension and content validation.  
- **Device duplication**: Between 1 and 50 copies per operation.  
- **Fields and references**: Device references are unique; duplicates regenerate reference and reset `current_row_index`.  

## Machine Requirements (Linux)

- **Development / PoC** (up to ~1k devices, small datasets):  
  - 1 vCPU, 1–2 GB RAM, 1–5 GB disk.  
- **Small Production** (up to ~10k devices, moderate usage):  
  - 2 vCPU, 2–4 GB RAM, 10+ GB disk.  
- **Operating System**: Ubuntu 20.04/22.04 LTS or similar.  
- **Dependencies**:  
  - Docker 24+ and Docker Compose Plugin.  
  - Open ports: 80 (frontend), 5000 (backend API, if exposed).  
- **Storage**: SSD recommended; mount `./data` and `./backend/uploads` on persistent volumes.  

## Operation and Deployment

- **Logs**:  
  - `docker-compose logs -f backend` and `docker-compose logs -f frontend`.  
- **Scheduler restart**:  
  - The scheduler starts automatically; it shuts down cleanly when containers stop.  
- **Backups**:  
  - Regularly back up `./data` and `./backend/uploads`.  

## Troubleshooting

- **File too large (413)**: Reduce CSV size or increase `MAX_CONTENT_LENGTH`.  
- **Translation 404 errors**: Ensure access via backend (serves `/locales/...`) or that Nginx copies `frontend/locales/` into the container.  
- **Orphan scheduler jobs**: If you massively change devices/connections, restart backend. If it persists, delete `scheduler_jobs.db` from the data volume (may be in `./data`) with backend stopped—it will regenerate.  
- **Linux permissions**: If Nginx/Flask cannot read/write volumes, adjust permissions/ownership of `./data` and `./backend/uploads`.  

## Application Usage

1. **Create Device**: Click "New Device" and fill in the form.  
2. **Import CSV**: In the device detail, drag CSV file or select it.  
3. **Preview**: Review generated CSV and JSON tables.  
4. **Save**: Confirm saving data into the database.  
5. **Transmit**: Configure connection (MQTT/HTTPS) and launch manual or automatic transmission.  

## License

MIT License  
This application is fully Open Source. You may use, modify, and distribute it freely.

<a href="https://www.buymeacoffee.com/joluben" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="250">
</a>
