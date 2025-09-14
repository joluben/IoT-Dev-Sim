import sqlite3
import os
from contextlib import contextmanager

# SQLAlchemy imports for Phase 10 optimization
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'database.sqlite')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemy setup with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        'check_same_thread': False,  # Allow SQLite to be used across threads
    },
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL debugging
)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe session factory
db_session = scoped_session(SessionLocal)

def init_db():
    """Inicializa y migra la base de datos creando y actualizando tablas."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    with get_db_connection() as conn:
        # Creación de tablas iniciales si no existen
        conn.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                csv_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL CHECK(type IN ('MQTT', 'HTTPS', 'KAFKA')),
                host TEXT NOT NULL,
                port INTEGER,
                endpoint TEXT,
                auth_type TEXT NOT NULL CHECK(auth_type IN ('NONE', 'USER_PASS', 'TOKEN', 'API_KEY')),
                auth_config TEXT,
                connection_config TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS connection_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL,
                test_result TEXT NOT NULL CHECK(test_result IN ('SUCCESS', 'FAILED')),
                response_time INTEGER,
                error_message TEXT,
                tested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES connections (id)
            )
        ''')

        # --- Migraciones para Fase 7 ---
        add_column_if_not_exists(conn, 'devices', 'device_type', "TEXT NOT NULL DEFAULT 'WebApp' CHECK(device_type IN ('WebApp', 'Sensor'))")
        add_column_if_not_exists(conn, 'devices', 'transmission_frequency', 'INTEGER DEFAULT 3600')
        add_column_if_not_exists(conn, 'devices', 'transmission_enabled', 'BOOLEAN DEFAULT FALSE')
        add_column_if_not_exists(conn, 'devices', 'current_row_index', 'INTEGER DEFAULT 0')
        add_column_if_not_exists(conn, 'devices', 'last_transmission', 'DATETIME')
        add_column_if_not_exists(conn, 'devices', 'selected_connection_id', 'INTEGER')
        # Nueva configuración: opcionalmente incluir device_id en payload de transmisión
        add_column_if_not_exists(conn, 'devices', 'include_device_id_in_payload', 'BOOLEAN DEFAULT FALSE')

        # Nuevas tablas para Fase 7
        conn.execute('''
            CREATE TABLE IF NOT EXISTS device_transmissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                connection_id INTEGER NOT NULL,
                transmission_type TEXT NOT NULL CHECK(transmission_type IN ('FULL_CSV', 'SINGLE_ROW')),
                data_sent TEXT,
                row_index INTEGER,
                status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED', 'PENDING')),
                response_data TEXT,
                error_message TEXT,
                transmission_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices (id),
                FOREIGN KEY (connection_id) REFERENCES connections (id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_transmissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                connection_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                next_execution DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices (id),
                FOREIGN KEY (connection_id) REFERENCES connections (id)
            )
        ''')

        # --- Nuevas tablas para Fase 8: Sistema de Proyectos ---
        conn.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                transmission_status TEXT DEFAULT 'INACTIVE' CHECK(transmission_status IN ('INACTIVE', 'ACTIVE', 'PAUSED')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                device_id INTEGER NOT NULL,
                assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE,
                UNIQUE(project_id, device_id)
            )
        ''')

        # Migración: actualizar constraint de tipo de conexión para aceptar KAFKA
        migrate_connections_type_constraint(conn)

        # Índices para optimizar consultas de proyectos
        conn.execute('CREATE INDEX IF NOT EXISTS idx_project_devices_project ON project_devices(project_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_project_devices_device ON project_devices(device_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(transmission_status)')

        # Migración opcional: agregar columna current_project_id a devices
        add_column_if_not_exists(conn, 'devices', 'current_project_id', 'INTEGER REFERENCES projects (id) ON DELETE SET NULL')

        conn.commit()

def add_column_if_not_exists(conn, table_name, column_name, column_definition):
    """Añade una columna a una tabla si no existe."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row['name'] for row in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}')

def migrate_connections_type_constraint(conn):
    """Ensure connections.type CHECK constraint includes KAFKA.
    If the existing table was created with only ('MQTT','HTTPS'), recreate it with KAFKA and migrate data.
    """
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='connections'").fetchone()
        sql = row['sql'] if row else ''
        if sql and "CHECK(type IN ('MQTT', 'HTTPS'))" in sql and 'KAFKA' not in sql:
            # Recreate table with the new constraint
            conn.execute('BEGIN TRANSACTION')
            conn.execute('''
                CREATE TABLE connections_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL CHECK(type IN ('MQTT', 'HTTPS', 'KAFKA')),
                    host TEXT NOT NULL,
                    port INTEGER,
                    endpoint TEXT,
                    auth_type TEXT NOT NULL CHECK(auth_type IN ('NONE', 'USER_PASS', 'TOKEN', 'API_KEY')),
                    auth_config TEXT,
                    connection_config TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Copy data
            conn.execute('''
                INSERT INTO connections_new (id, name, description, type, host, port, endpoint, auth_type, auth_config, connection_config, is_active, created_at, updated_at)
                SELECT id, name, description, type, host, port, endpoint, auth_type, auth_config, connection_config, is_active, created_at, updated_at
                FROM connections
            ''')
            conn.execute('DROP TABLE connections')
            conn.execute('ALTER TABLE connections_new RENAME TO connections')
            conn.execute('COMMIT')
    except Exception:
        # If anything fails, rollback to avoid corrupting the DB and continue
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass

# SQLAlchemy session management (Phase 10 optimization)
@contextmanager
def get_db_session():
    """Context manager for SQLAlchemy sessions with automatic rollback"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_scoped_session():
    """Get thread-safe scoped session"""
    return db_session

def close_scoped_session():
    """Remove scoped session"""
    db_session.remove()

# Legacy SQLite functions (maintained for backward compatibility)
@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos (legacy)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None):
    """Ejecuta una query y retorna los resultados (legacy)"""
    with get_db_connection() as conn:
        cursor = conn.execute(query, params or [])
        return cursor.fetchall()

def execute_insert(query, params=None):
    """Ejecuta un INSERT y retorna el ID del registro creado (legacy)"""
    with get_db_connection() as conn:
        cursor = conn.execute(query, params or [])
        conn.commit()
        return cursor.lastrowid

# SQLAlchemy query helpers
def execute_sqlalchemy_query(query_text, params=None):
    """Execute raw SQL using SQLAlchemy engine"""
    with engine.connect() as conn:
        result = conn.execute(text(query_text), params or {})
        return result.fetchall()

def execute_sqlalchemy_insert(query_text, params=None):
    """Execute INSERT using SQLAlchemy engine"""
    with engine.connect() as conn:
        result = conn.execute(text(query_text), params or {})
        conn.commit()
        return result.lastrowid
