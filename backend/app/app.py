from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sock import Sock
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import atexit
import logging
from dotenv import load_dotenv
from .environment_config import get_config, print_config_summary
from .database import init_db
from .routes.devices import devices_bp
from .routes.upload import upload_bp
from .routes.connections import connections_bp
from .routes.transmissions import transmissions_bp
from .routes.projects import projects_bp
from .routes.security import security_bp
from .routes.health import health_bp
from .routes.auth_routes import auth_bp
from .scheduler import init_scheduler
from .secrets_mgmt.secret_manager import get_secret_manager
from .startup_validation import validate_startup_configuration
from .middleware.auth_middleware import create_auth_middleware
from .middleware.security_middleware import SecurityMiddleware

def create_app():
    # Load environment variables from .env for local development
    load_dotenv()

    # Load environment-aware configuration
    config = get_config()
    
    # Print configuration summary in development
    if config.environment == 'development':
        print_config_summary(config)

    # Validate startup configuration before initializing Flask app
    print("🔍 Validating startup configuration...")
    if not validate_startup_configuration(exit_on_failure=True):
        raise RuntimeError("Startup validation failed - cannot initialize application")
    
    app = Flask(__name__)
    sock = Sock(app)
    
    redis_url = os.getenv('REDIS_URL')
    storage_uri = redis_url if redis_url else 'memory://'
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        app=app,
        default_limits=["100 per minute"]
    )
    app.limiter = limiter
    
    # Apply configuration to Flask app
    app.config['MAX_CONTENT_LENGTH'] = config.max_content_length
    app.config['UPLOAD_FOLDER'] = config.upload_folder
    app.config['DATABASE_URL'] = config.database.url
    app.config['SECRET_KEY'] = config.secret_key
    
    # Store config for access by other components
    app.config['DEVSIM_CONFIG'] = config
    
    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configure CORS based on environment
    if config.environment == 'production':
        # Strict CORS for production
        CORS(app, 
             origins=config.security.cors_origins,
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        print(f"🔒 CORS configured for production: {config.security.cors_origins}")
    else:
        # Relaxed CORS for development
        CORS(app, origins=config.security.cors_origins)
        print(f"🔧 CORS configured for development: {config.security.cors_origins}")
    
    # Production security validation
    if config.environment == 'production':
        if config.security.debug_enabled:
            raise RuntimeError("Debug mode cannot be enabled in production")
        if config.security.allow_sensitive_connections:
            raise RuntimeError("Sensitive connections cannot be allowed in production")
        print("🔒 Production security validated: Debug disabled, sensitive connections blocked")
    
    # Inicializar base de datos
    init_db()
    
    # Initialize SecretManager early to ensure encryption system is ready
    try:
        secret_manager = get_secret_manager()
        app.logger.info("SecretManager initialized successfully")
        
        # Validate secret manager health
        health_status = secret_manager.get_health_status()
        if not health_status.get('secret_provider', {}).get('available', False):
            raise RuntimeError("Secret provider is not available")
            
    except Exception as e:
        app.logger.error(f"Failed to initialize SecretManager: {e}")
        raise RuntimeError("Critical security error: Cannot start without encryption system")
    
    # Configurar scheduler
    scheduler = init_scheduler(app)
    app.scheduler = scheduler
    # Iniciar scheduler inmediatamente (evita dependencia de before_first_request)
    try:
        import logging
        logging.info("Starting transmission scheduler...")
        app.scheduler.start()
        logging.info("✅ Transmission scheduler started successfully")
    except Exception as e:
        import logging
        import traceback
        logging.error(f"❌ Error starting scheduler: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        # Continue without scheduler - transmissions won't work but app will run
        app.scheduler = None
    # Detener scheduler al finalizar el proceso (apagado limpio)
    atexit.register(lambda: hasattr(app, 'scheduler') and app.scheduler and app.scheduler.shutdown())
    
    # Initialize security middleware (must be before auth middleware)
    security_middleware = SecurityMiddleware(app)
    
    # Initialize authentication middleware
    create_auth_middleware(app)
    
    limiter = app.limiter
    limiter.exempt(health_bp)
    limiter.limit("5 per minute")(auth_bp)
    limiter.limit("2 per minute")(upload_bp)
    
    # Registrar blueprints
    app.register_blueprint(devices_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(connections_bp)
    app.register_blueprint(transmissions_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)

    # Depuración: listar rutas registradas al iniciar la app
    try:
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            methods = ','.join(sorted(m for m in rule.methods if m not in ('HEAD', 'OPTIONS')))
            app.logger.info(f"ROUTE {methods} {rule.rule}")
    except Exception:
        pass

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
    locales_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'locales')
    
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/locales/<path:path>')
    def serve_locales(path):
        return send_from_directory(locales_dir, path)
    
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

    @app.errorhandler(429)
    def ratelimit_handler(e):
        retry_after = getattr(e, "retry_after", None)
        app.logger.warning(f"Rate limit exceeded: ip={request.remote_addr} path={request.path}")
        resp = jsonify({'error': 'Too Many Requests', 'message': 'Rate limit exceeded'})
        if retry_after:
            resp.headers['Retry-After'] = str(retry_after)
        return resp, 429

    return app
