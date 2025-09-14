"""
Database package compatibility shim

This package re-exports required symbols from the sibling module file
`backend/app/database.py` to avoid package/module name collisions.

Exports:
- init_db
- get_db_session
- Base (SQLAlchemy declarative base)
"""

from __future__ import annotations

# Try a direct relative import first
init_db = None  # type: ignore
get_db_session = None  # type: ignore
get_scoped_session = None  # type: ignore
close_scoped_session = None  # type: ignore
get_database_health = None  # type: ignore
recover_database_connections = None  # type: ignore
execute_query = None  # type: ignore
execute_insert = None  # type: ignore
execute_sqlalchemy_query = None  # type: ignore
execute_sqlalchemy_insert = None  # type: ignore
Base = None  # type: ignore

try:
    # When imported as package app.database, this resolves to backend/app/database.py module
    from .. import database as _legacy_db  # type: ignore
    init_db = getattr(_legacy_db, 'init_db', None)
    get_db_session = getattr(_legacy_db, 'get_db_session', None)
    get_scoped_session = getattr(_legacy_db, 'get_scoped_session', None)
    close_scoped_session = getattr(_legacy_db, 'close_scoped_session', None)
    get_database_health = getattr(_legacy_db, 'get_database_health', None)
    recover_database_connections = getattr(_legacy_db, 'recover_database_connections', None)
    execute_query = getattr(_legacy_db, 'execute_query', None)
    execute_insert = getattr(_legacy_db, 'execute_insert', None)
    execute_sqlalchemy_query = getattr(_legacy_db, 'execute_sqlalchemy_query', None)
    execute_sqlalchemy_insert = getattr(_legacy_db, 'execute_sqlalchemy_insert', None)
    Base = getattr(_legacy_db, 'Base', None)
except Exception:
    _legacy_db = None  # type: ignore

# If direct import failed or symbols missing, load by absolute file path
if init_db is None or get_db_session is None or Base is None:
    try:
        import importlib.util
        from pathlib import Path
        _path = Path(__file__).resolve().parent.parent / 'database.py'
        spec = importlib.util.spec_from_file_location('app_legacy_database_module', str(_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            init_db = getattr(mod, 'init_db', init_db)
            get_db_session = getattr(mod, 'get_db_session', get_db_session)
            get_scoped_session = getattr(mod, 'get_scoped_session', get_scoped_session)
            close_scoped_session = getattr(mod, 'close_scoped_session', close_scoped_session)
            get_database_health = getattr(mod, 'get_database_health', get_database_health)
            recover_database_connections = getattr(mod, 'recover_database_connections', recover_database_connections)
            execute_query = getattr(mod, 'execute_query', execute_query)
            execute_insert = getattr(mod, 'execute_insert', execute_insert)
            execute_sqlalchemy_query = getattr(mod, 'execute_sqlalchemy_query', execute_sqlalchemy_query)
            execute_sqlalchemy_insert = getattr(mod, 'execute_sqlalchemy_insert', execute_sqlalchemy_insert)
            Base = getattr(mod, 'Base', Base)
    except Exception:
        pass

__all__ = [
    'init_db',
    'get_db_session',
    'get_scoped_session',
    'close_scoped_session',
    'get_database_health',
    'recover_database_connections',
    'execute_query',
    'execute_insert',
    'execute_sqlalchemy_query',
    'execute_sqlalchemy_insert',
    'Base',
]