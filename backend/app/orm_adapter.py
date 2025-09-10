"""
ORM Adapter for Phase 10 Database Optimization
Provides compatibility layer between legacy models and SQLAlchemy ORM
"""

from .database import get_db_session, execute_query, execute_insert
from .sqlalchemy_models import DeviceORM, ConnectionORM, ProjectORM, DeviceTransmissionORM
from sqlalchemy.orm import joinedload
from sqlalchemy import desc
import json


class DeviceORMAdapter:
    """Adapter to use SQLAlchemy ORM for Device operations while maintaining API compatibility"""
    
    @staticmethod
    def get_all():
        """Get all devices using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                devices = session.query(DeviceORM).all()
                return [device.to_dict() for device in devices]
        except Exception:
            # Fallback to legacy method
            return DeviceORMAdapter._legacy_get_all()
    
    @staticmethod
    def get_by_id(device_id):
        """Get device by ID using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                device = session.query(DeviceORM).filter(DeviceORM.id == device_id).first()
                return device.to_dict() if device else None
        except Exception:
            # Fallback to legacy method
            return DeviceORMAdapter._legacy_get_by_id(device_id)
    
    @staticmethod
    def create(name, description):
        """Create device using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                reference = DeviceORM.generate_reference()
                
                # Ensure unique reference
                while session.query(DeviceORM).filter(DeviceORM.reference == reference).first():
                    reference = DeviceORM.generate_reference()
                
                device = DeviceORM(
                    reference=reference,
                    name=name,
                    description=description
                )
                session.add(device)
                session.flush()  # Get the ID
                return device.to_dict()
        except Exception:
            # Fallback to legacy method
            return DeviceORMAdapter._legacy_create(name, description)
    
    @staticmethod
    def update(device_id, **kwargs):
        """Update device using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                device = session.query(DeviceORM).filter(DeviceORM.id == device_id).first()
                if not device:
                    return None
                
                for key, value in kwargs.items():
                    if hasattr(device, key):
                        setattr(device, key, value)
                
                return device.to_dict()
        except Exception:
            # Fallback to legacy method
            return DeviceORMAdapter._legacy_update(device_id, **kwargs)
    
    @staticmethod
    def delete(device_id):
        """Delete device using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                device = session.query(DeviceORM).filter(DeviceORM.id == device_id).first()
                if device:
                    session.delete(device)
                    return True
                return False
        except Exception:
            # Fallback to legacy method
            return DeviceORMAdapter._legacy_delete(device_id)
    
    # Legacy fallback methods
    @staticmethod
    def _legacy_get_all():
        rows = execute_query('SELECT * FROM devices ORDER BY created_at DESC')
        devices = []
        for row in rows:
            device_dict = dict(row)
            # Parse CSV data if it exists
            if device_dict.get('csv_data'):
                try:
                    import json
                    device_dict['csv_data'] = json.loads(device_dict['csv_data'])
                except:
                    pass
            devices.append(device_dict)
        return devices
    
    @staticmethod
    def _legacy_get_by_id(device_id):
        rows = execute_query('SELECT * FROM devices WHERE id = ?', [device_id])
        if rows:
            device_dict = dict(rows[0])
            # Parse CSV data if it exists
            if device_dict.get('csv_data'):
                try:
                    import json
                    device_dict['csv_data'] = json.loads(device_dict['csv_data'])
                except:
                    pass
            return device_dict
        return None
    
    @staticmethod
    def _legacy_create(name, description):
        from .models import Device
        device = Device.create(name, description)
        return device.__dict__ if device else None
    
    @staticmethod
    def _legacy_update(device_id, **kwargs):
        # Implementation for legacy update
        pass
    
    @staticmethod
    def _legacy_delete(device_id):
        # Implementation for legacy delete
        pass


class ConnectionORMAdapter:
    """Adapter to use SQLAlchemy ORM for Connection operations"""
    
    @staticmethod
    def get_all():
        """Get all connections using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                connections = session.query(ConnectionORM).all()
                return [conn.to_dict() for conn in connections]
        except Exception:
            return ConnectionORMAdapter._legacy_get_all()
    
    @staticmethod
    def get_by_id(connection_id):
        """Get connection by ID using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                connection = session.query(ConnectionORM).filter(ConnectionORM.id == connection_id).first()
                return connection.to_dict() if connection else None
        except Exception:
            return ConnectionORMAdapter._legacy_get_by_id(connection_id)
    
    @staticmethod
    def create(data):
        """Create connection using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                connection = ConnectionORM(
                    name=data.get('name'),
                    description=data.get('description'),
                    type=data.get('type'),
                    host=data.get('host'),
                    port=data.get('port'),
                    endpoint=data.get('endpoint'),
                    auth_type=data.get('auth_type'),
                    auth_config=json.dumps(data.get('auth_config', {})),
                    connection_config=json.dumps(data.get('connection_config', {})),
                    is_active=data.get('is_active', True)
                )
                session.add(connection)
                session.flush()
                return connection.to_dict()
        except Exception:
            return ConnectionORMAdapter._legacy_create(data)
    
    @staticmethod
    def update(connection_id, data):
        """Update connection using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                connection = session.query(ConnectionORM).filter(ConnectionORM.id == connection_id).first()
                if not connection:
                    return None
                
                for key, value in data.items():
                    if key in ['auth_config', 'connection_config'] and value:
                        setattr(connection, key, json.dumps(value))
                    elif hasattr(connection, key):
                        setattr(connection, key, value)
                
                return connection.to_dict()
        except Exception:
            return ConnectionORMAdapter._legacy_update(connection_id, data)
    
    # Legacy fallback methods
    @staticmethod
    def _legacy_get_all():
        rows = execute_query('SELECT * FROM connections ORDER BY created_at DESC')
        return [dict(row) for row in rows]
    
    @staticmethod
    def _legacy_get_by_id(connection_id):
        rows = execute_query('SELECT * FROM connections WHERE id = ?', [connection_id])
        return dict(rows[0]) if rows else None
    
    @staticmethod
    def _legacy_create(data):
        from .models import Connection
        connection = Connection.create(data)
        return connection.__dict__ if connection else None
    
    @staticmethod
    def _legacy_update(connection_id, data):
        # Implementation for legacy update
        pass


class ProjectORMAdapter:
    """Adapter to use SQLAlchemy ORM for Project operations"""
    
    @staticmethod
    def get_all():
        """Get all projects using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                projects = session.query(ProjectORM).options(joinedload(ProjectORM.devices)).all()
                return [project.to_dict() for project in projects]
        except Exception:
            return ProjectORMAdapter._legacy_get_all()
    
    @staticmethod
    def get_by_id(project_id):
        """Get project by ID using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                project = session.query(ProjectORM).options(joinedload(ProjectORM.devices)).filter(ProjectORM.id == project_id).first()
                return project.to_dict() if project else None
        except Exception:
            return ProjectORMAdapter._legacy_get_by_id(project_id)
    
    @staticmethod
    def create(data):
        """Create project using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                project = ProjectORM(
                    name=data.get('name'),
                    description=data.get('description'),
                    is_active=data.get('is_active', True)
                )
                session.add(project)
                session.flush()
                return project.to_dict()
        except Exception:
            return ProjectORMAdapter._legacy_create(data)
    
    # Legacy fallback methods
    @staticmethod
    def _legacy_get_all():
        rows = execute_query('SELECT * FROM projects ORDER BY created_at DESC')
        return [dict(row) for row in rows]
    
    @staticmethod
    def _legacy_get_by_id(project_id):
        rows = execute_query('SELECT * FROM projects WHERE id = ?', [project_id])
        return dict(rows[0]) if rows else None
    
    @staticmethod
    def _legacy_create(data):
        from .models import Project
        project = Project.create(data)
        return project.__dict__ if project else None


class TransmissionORMAdapter:
    """Adapter for transmission-related operations"""
    
    @staticmethod
    def get_device_history(device_id, limit=20):
        """Get device transmission history using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                transmissions = (session.query(DeviceTransmissionORM)
                               .filter(DeviceTransmissionORM.device_id == device_id)
                               .order_by(desc(DeviceTransmissionORM.transmission_time))
                               .limit(limit)
                               .all())
                return [transmission.to_dict() for transmission in transmissions]
        except Exception:
            return TransmissionORMAdapter._legacy_get_device_history(device_id, limit)
    
    @staticmethod
    def create_transmission_record(device_id, connection_id, transmission_type, data_sent, status, **kwargs):
        """Create transmission record using SQLAlchemy ORM"""
        try:
            with get_db_session() as session:
                transmission = DeviceTransmissionORM(
                    device_id=device_id,
                    connection_id=connection_id,
                    transmission_type=transmission_type,
                    data_sent=data_sent,
                    status=status,
                    row_index=kwargs.get('row_index'),
                    response_data=kwargs.get('response_data'),
                    error_message=kwargs.get('error_message')
                )
                session.add(transmission)
                session.flush()
                return transmission.to_dict()
        except Exception:
            return TransmissionORMAdapter._legacy_create_transmission_record(
                device_id, connection_id, transmission_type, data_sent, status, **kwargs
            )
    
    # Legacy fallback methods
    @staticmethod
    def _legacy_get_device_history(device_id, limit):
        rows = execute_query(
            'SELECT * FROM device_transmissions WHERE device_id = ? ORDER BY transmission_time DESC LIMIT ?',
            [device_id, limit]
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    def _legacy_create_transmission_record(device_id, connection_id, transmission_type, data_sent, status, **kwargs):
        # Implementation for legacy transmission record creation
        pass
