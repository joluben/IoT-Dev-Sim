from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from .models import Device, Connection
from .transmission import TransmissionManager
from .database import execute_query
import logging
import atexit
import os

# Configurar logging para APScheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

"""
Scheduler de transmisiones automáticas.

Nota importante sobre serialización de jobs:
  Con SQLAlchemyJobStore, APScheduler serializa la función del job. Las funciones
  enlazadas a instancia (p.ej. self._execute_transmission) pueden fallar al
  serializar/pickle debido a referencias al objeto Flask app. Para evitar 500s
  al añadir jobs, usamos una función a nivel de módulo `execute_transmission_job`.
"""

# Referencia global a la app Flask para uso dentro del job
flask_app_ref = None

def execute_transmission_job(device_id, connection_id):
    """Función de job serializable para ejecutar una transmisión programada.
    Usa la referencia global de la app para abrir app_context.
    """
    import logging
    global flask_app_ref
    app = flask_app_ref
    if app is None:
        logging.error("Flask app reference not initialized for scheduler job")
        return
    
    logging.info(f"🔄 Executing transmission job for device {device_id}, connection {connection_id}")
    
    with app.app_context():
        try:
            device = Device.get_by_id(device_id)
            connection = Connection.get_by_id(connection_id)
            
            logging.info(f"Device found: {device is not None}, Connection found: {connection is not None}")

            if not device or not connection:
                logging.warning(f"Dispositivo {device_id} o conexión {connection_id} no encontrados")
                return

            if not device.transmission_enabled:
                logging.info(f"Transmisión deshabilitada para dispositivo {device_id}")
                # Detener job si se deshabilita
                try:
                    sched = app.scheduler
                    if sched:
                        sched.stop_transmission(device_id, connection_id)
                except Exception:
                    pass
                return

            # Manejo de Sensor: reinicio de posición si llega al final
            if device.device_type == 'Sensor':
                csv_content = device.get_csv_data_parsed()
                if not csv_content:
                    logging.warning(f"No hay datos CSV para el sensor {device_id}")
                    return
                data_rows = csv_content.get('data') or csv_content.get('json_preview', [])
                if device.current_row_index >= len(data_rows):
                    logging.info(f"Sensor {device_id} ha completado todas las filas. Reiniciando posición.")
                    device.reset_sensor_position()

            tm = TransmissionManager()
            success = tm.transmit_device_data(device, connection)
            if success:
                logging.info(f"Transmisión exitosa para dispositivo {device_id}")
            else:
                logging.warning(f"Transmisión fallida para dispositivo {device_id}")
        except Exception as e:
            logging.error(f"Error en transmisión programada para dispositivo {device_id}: {e}")


class TransmissionScheduler:
    """Sistema de tareas programadas con APScheduler para transmisiones automáticas."""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self.transmission_manager = TransmissionManager()
        if app:
            self.setup_scheduler()
    
    def setup_scheduler(self):
        """Configurar APScheduler con persistencia en BD"""
        # Intentar usar persistencia en BD, fallback a memoria si falla
        try:
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
            os.makedirs(data_dir, exist_ok=True)
            default_db_path = os.path.join(data_dir, 'scheduler_jobs.db')
            # En Windows, SQLAlchemy necesita barras normales en la URL
            default_db_path_url = default_db_path.replace('\\', '/')
            database_url = os.getenv('DATABASE_URL', f'sqlite:///{default_db_path_url}')
            logging.info(f"Scheduler database URL: {database_url}")
            
            jobstores = {
                'default': SQLAlchemyJobStore(url=database_url)
            }
        except Exception as e:
            logging.warning(f"Could not setup persistent jobstore, using memory: {e}")
            # Fallback a jobstore en memoria (no persiste entre reinicios)
            jobstores = {}
        
        executors = {
            'default': ThreadPoolExecutor(20)  # Máximo 20 threads concurrentes
        }
        job_defaults = {
            'coalesce': False,  # No agrupar ejecuciones perdidas
            'max_instances': 1  # Una instancia por job
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
    
    def start(self):
        """Iniciar el scheduler"""
        if self.scheduler and not self.scheduler.running:
            try:
                self.scheduler.start()
                # Cargar transmisiones programadas existentes al iniciar
                self._load_existing_schedules()
            except Exception as e:
                logging.error(f"Failed to start scheduler with persistent storage: {e}")
                logging.info("Recreating scheduler with in-memory storage...")
                # Recrear scheduler sin persistencia
                self.scheduler = BackgroundScheduler(
                    executors={'default': ThreadPoolExecutor(20)},
                    job_defaults={'coalesce': False, 'max_instances': 1}
                )
                self.scheduler.start()
                logging.info("Scheduler started successfully with in-memory storage")
    
    def shutdown(self):
        """Detener el scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logging.info("Scheduler cerrado correctamente")
    
    def schedule_transmission(self, device_id, connection_id, frequency_seconds):
        """Programar transmisión automática usando función de módulo serializable"""
        try:
            def _debug_path():
                # Ruta al directorio data en el proyecto
                return os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scheduler_debug.log')

            if not self.scheduler:
                logging.error("Scheduler not initialized")
                # Log a archivo accesible
                try:
                    with open(_debug_path(), 'a', encoding='utf-8') as f:
                        f.write(f"schedule_transmission early-exit: scheduler not initialized for device {device_id}, connection {connection_id}, freq {frequency_seconds}\n")
                except Exception:
                    pass
                return None
                
            if frequency_seconds <= 0:
                logging.error(f"Invalid frequency: {frequency_seconds}")
                try:
                    with open(_debug_path(), 'a', encoding='utf-8') as f:
                        f.write(f"schedule_transmission early-exit: invalid frequency {frequency_seconds} for device {device_id}, connection {connection_id}\n")
                except Exception:
                    pass
                return None
                
            job_id = f"transmission_{device_id}_{connection_id}"

            self.scheduler.add_job(
                func=execute_transmission_job,
                trigger='interval',
                seconds=frequency_seconds,
                args=[device_id, connection_id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=30
            )
            
            logging.info(f"Job {job_id} scheduled with frequency {frequency_seconds}s")
            return job_id
        except Exception as e:
            logging.error(f"Error scheduling transmission job: {e}")
            # Escribir detalle en archivo de depuración accesible desde el host
            try:
                debug_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scheduler_debug.log')
                with open(debug_path, 'a', encoding='utf-8') as f:
                    f.write(f"schedule_transmission error for device {device_id}, connection {connection_id}, freq {frequency_seconds}: {e}\n")
            except Exception:
                pass
            return None
    
    def pause_transmission(self, device_id, connection_id):
        """Pausar transmisión sin eliminar la programación"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.pause_job(job_id)
            return True
        except:
            return False
    
    def resume_transmission(self, device_id, connection_id):
        """Reanudar transmisión pausada"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.resume_job(job_id)
            return True
        except:
            return False
    
    def stop_transmission(self, device_id, connection_id):
        """Detener y eliminar transmisión programada"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            self.scheduler.remove_job(job_id)
            return True
        except:
            return False
    
    # Método anterior de ejecución eliminado en favor de execute_transmission_job
    
    def get_job_status(self, device_id, connection_id):
        """Obtener estado del job programado"""
        job_id = f"transmission_{device_id}_{connection_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    'exists': True,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
        except:
            pass
        
        return {'exists': False}
    
    def _log_transmission_result(self, device_id, connection_id, result):
        """Log resultado de transmisión"""
        if result.get('success'):
            logging.info(f"Transmisión exitosa para dispositivo {device_id}")
        else:
            logging.warning(f"Transmisión fallida para dispositivo {device_id}")
    
    def _log_transmission_error(self, device_id, connection_id, error):
        """Log error de transmisión"""
        logging.error(f"Error en transmisión programada para dispositivo {device_id}: {error}")
    
    def _load_existing_schedules(self):
        """Carga las transmisiones programadas existentes desde la base de datos."""
        try:
            # Limpiar jobs huérfanos primero
            self._cleanup_orphaned_jobs()
            
            # Obtener dispositivos con transmisión habilitada
            devices_query = """
                SELECT d.*, c.id as connection_id 
                FROM devices d 
                JOIN connections c ON c.is_active = 1
                WHERE d.transmission_enabled = 1
            """
            rows = execute_query(devices_query)
            
            for row in rows:
                device = Device._from_row(row)
                connection_id = row['connection_id']
                # Solo programar si no existe ya el job
                job_id = f"transmission_{device.id}_{connection_id}"
                existing_job = None
                try:
                    existing_job = self.scheduler.get_job(job_id)
                except:
                    pass
                    
                if not existing_job:
                    self.schedule_transmission(device.id, connection_id, device.transmission_frequency)
                    
        except Exception as e:
            logging.error(f"Error loading existing schedules: {e}")
    
    def _cleanup_orphaned_jobs(self):
        """Limpia jobs huérfanos que pueden causar conflictos"""
        try:
            if not self.scheduler:
                return
                
            # Obtener todos los jobs existentes
            existing_jobs = self.scheduler.get_jobs()
            
            for job in existing_jobs:
                if job.id.startswith('transmission_'):
                    # Extraer device_id y connection_id del job_id
                    try:
                        parts = job.id.split('_')
                        if len(parts) >= 3:
                            device_id = int(parts[1])
                            connection_id = int(parts[2])
                            
                            # Verificar si el dispositivo y conexión aún existen y están activos
                            device = Device.get_by_id(device_id)
                            connection = Connection.get_by_id(connection_id)
                            
                            if (not device or not device.transmission_enabled or 
                                not connection or not getattr(connection, 'is_active', False)):
                                # Remover job huérfano
                                self.scheduler.remove_job(job.id)
                                logging.info(f"Removed orphaned job: {job.id}")
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Could not parse job ID {job.id}: {e}")
                        
        except Exception as e:
            logging.error(f"Error cleaning up orphaned jobs: {e}")
    
    def get_scheduled_jobs(self):
        """Retorna información sobre los jobs programados."""
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': getattr(job, 'name', job.id),
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs

# Instancia global del scheduler
transmission_scheduler = None

def get_scheduler():
    """Retorna la instancia global del scheduler."""
    global transmission_scheduler
    return transmission_scheduler

def init_scheduler(app):
    """Inicializa el scheduler de transmisiones."""
    global transmission_scheduler
    global flask_app_ref
    transmission_scheduler = TransmissionScheduler(app)
    # Guardar referencia global de la app para el job
    flask_app_ref = app
    return transmission_scheduler

class SchedulerMonitor:
    def __init__(self, scheduler):
        self.scheduler = scheduler
    
    def get_active_jobs(self):
        """Obtener lista de jobs activos"""
        jobs = []
        if self.scheduler and self.scheduler.scheduler:
            for job in self.scheduler.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'function': job.func.__name__
                })
        return jobs
    
    def get_scheduler_stats(self):
        """Obtener estadísticas del scheduler"""
        if self.scheduler and self.scheduler.scheduler:
            return {
                'running': self.scheduler.scheduler.running,
                'total_jobs': len(self.scheduler.scheduler.get_jobs()),
                'executor_info': str(self.scheduler.scheduler.state)
            }
        return {
            'running': False,
            'total_jobs': 0,
            'executor_info': 'Not initialized'
        }
