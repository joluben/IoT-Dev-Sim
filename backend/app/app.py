from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sock import Sock
import os
import atexit
from .database import init_db
from .routes.devices import devices_bp
from .routes.upload import upload_bp
from .routes.connections import connections_bp
from .routes.transmissions import transmissions_bp
from .scheduler import init_scheduler

def create_app():
    app = Flask(__name__)
    sock = Sock(app)
    
    # Configuración
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB máximo
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///scheduler_jobs.db')
    
    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configurar CORS para desarrollo
    CORS(app, origins=['*'])
    
    # Inicializar base de datos
    init_db()
    
    # Configurar scheduler
    scheduler = init_scheduler(app)
    app.scheduler = scheduler
    # Iniciar scheduler inmediatamente (evita dependencia de before_first_request)
    try:
        app.scheduler.start()
    except Exception as e:
        import logging
        logging.error(f"Error starting scheduler: {e}")
    # Detener scheduler al finalizar el proceso (apagado limpio)
    atexit.register(lambda: hasattr(app, 'scheduler') and app.scheduler and app.scheduler.shutdown())
    
    # Registrar blueprints
    app.register_blueprint(devices_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(connections_bp)
    app.register_blueprint(transmissions_bp)

    # WebSocket para actualizaciones de transmisiones
    @sock.route('/ws/transmissions')
    def ws_transmissions(ws):
        """Canal WS básico para tiempo real.
        Por ahora no hay bus de eventos; mantenemos la conexión y
        aceptamos mensajes del cliente (no-op) para evitar polling."""
        import json
        try:
            # Notificar estado inicial a la UI
            ws.send(json.dumps({
                'type': 'connection',
                'payload': {'status': 'connected', 'type': 'websocket'}
            }))
        except Exception:
            return
        # Bucle de recepción simple (eco no-op)
        while True:
            try:
                message = ws.receive()
                if message is None:
                    break
                # En el futuro se podrían interpretar comandos del cliente
                # y enviar eventos push desde TransmissionStateManager
            except Exception:
                break
    
    # Ruta para servir frontend
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'static')
    
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory(frontend_dir, path)
    
    # Manejo de errores
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'Archivo demasiado grande. Máximo 10MB.'}), 413
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Recurso no encontrado'}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Error interno del servidor'}), 500
    
    
    return app
