import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'database.sqlite')

def init_db():
    """Inicializa la base de datos creando las tablas necesarias"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    with get_db_connection() as conn:
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
        
        conn.commit()

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
