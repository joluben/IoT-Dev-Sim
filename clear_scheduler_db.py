#!/usr/bin/env python3
"""
Script para limpiar la base de datos del scheduler y resolver conflictos de jobs.
Ejecutar antes de reiniciar el backend cuando hay errores JobLookupError.
"""

import os
import sqlite3
import sys

def clear_scheduler_database():
    """Limpia la base de datos del scheduler APScheduler"""
    
    # Rutas posibles de la base de datos del scheduler
    db_paths = [
        'scheduler_jobs.db',
        'backend/scheduler_jobs.db',
        os.path.join(os.path.dirname(__file__), 'scheduler_jobs.db'),
        os.path.join(os.path.dirname(__file__), 'backend', 'scheduler_jobs.db')
    ]
    
    cleared = False
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                print(f"Encontrada base de datos del scheduler: {db_path}")
                
                # Conectar y limpiar
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Obtener lista de jobs antes de limpiar
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                job_count = 0
                for table in tables:
                    table_name = table[0]
                    if 'job' in table_name.lower():
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        job_count += count
                        
                        # Limpiar tabla de jobs
                        cursor.execute(f"DELETE FROM {table_name}")
                        print(f"Limpiados {count} registros de tabla {table_name}")
                
                conn.commit()
                conn.close()
                
                print(f"Base de datos limpiada: {job_count} jobs eliminados")
                cleared = True
                
            except Exception as e:
                print(f"Error limpiando {db_path}: {e}")
    
    if not cleared:
        print("No se encontraron bases de datos del scheduler para limpiar")
    
    return cleared

if __name__ == "__main__":
    print("Limpiando base de datos del scheduler APScheduler...")
    success = clear_scheduler_database()
    
    if success:
        print("\nLimpieza completada. Ahora puedes reiniciar el backend:")
        print("   python backend/run.py")
    else:
        print("\nNo se pudo limpiar la base de datos del scheduler")
    
    sys.exit(0 if success else 1)
