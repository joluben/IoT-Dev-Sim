# =============================================================================
# DevSim Gunicorn Production Configuration
# =============================================================================
# Production-ready Gunicorn configuration for DevSim backend
# =============================================================================

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - optimized for production
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)  # Cap at 8 workers
worker_class = "sync"  # Use "gevent" for async workloads if needed
worker_connections = 1000
timeout = 60  # Increased for file uploads and processing
keepalive = 5  # Increased for better connection reuse
graceful_timeout = 30  # Time to gracefully shutdown workers

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 2000  # Increased for better performance
max_requests_jitter = 100  # Random jitter to prevent thundering herd

# Preload application for better performance
preload_app = True

# User and group to run as
user = "appuser"
group = "appuser"

# Logging
accesslog = "/app/logs/gunicorn_access.log"
errorlog = "/app/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "devsim-backend"

# Server mechanics
daemon = False
pidfile = "/app/logs/gunicorn.pid"
# Use shared memory for worker temp files for better perf in containers
worker_tmp_dir = "/dev/shm"

# SSL (if needed for internal communication)
# keyfile = None
# certfile = None

# Security and limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Request size limits are enforced at Flask (MAX_CONTENT_LENGTH)
# and at the reverse proxy (e.g., Nginx client_max_body_size)

# Application-specific settings
raw_env = [
    'FLASK_ENV=production',
    'FLASK_DEBUG=false',
]

# Hooks for application lifecycle
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting DevSim Backend (Production)")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading DevSim Backend")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("DevSim Backend ready to serve requests")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker {worker.pid} forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker {worker.pid} initialized")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGABRT signal")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path} - {resp.status_code}")

def child_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the worker process."""
    worker.log.info(f"Worker {worker.pid} exiting")

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("DevSim Backend shutting down")