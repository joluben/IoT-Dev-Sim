import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'database.sqlite')

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
                type TEXT NOT NULL CHECK(type IN ('MQTT', 'HTTPS')),
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

        conn.commit()

def add_column_if_not_exists(conn, table_name, column_name, column_definition):
    """Añade una columna a una tabla si no existe."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row['name'] for row in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}')

@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None):
    """Ejecuta una query y retorna los resultados"""
    with get_db_connection() as conn:
        cursor = conn.execute(query, params or [])
        return cursor.fetchall()

def execute_insert(query, params=None):
    """Ejecuta un INSERT y retorna el ID del registro creado"""
    with get_db_connection() as conn:
        cursor = conn.execute(query, params or [])
        conn.commit()
        return cursor.lastrowid
