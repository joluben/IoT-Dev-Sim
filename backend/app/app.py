from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from .database import init_db
from .routes.devices import devices_bp
from .routes.upload import upload_bp
from .routes.connections import connections_bp

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB máximo
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    
    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configurar CORS para desarrollo
    CORS(app, origins=['*'])
    
    # Inicializar base de datos
    init_db()
    
    # Registrar blueprints
    app.register_blueprint(devices_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(connections_bp)
    
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
