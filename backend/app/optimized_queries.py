"""
Optimized Database Queries
Task 10.3.2 - Replace SELECT * with specific field selections
"""

from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func, and_, or_
# Use SQLAlchemy ORM models for optimized queries
from .sqlalchemy_models import (
    DeviceORM as Device,
    ConnectionORM as Connection,
    ProjectORM as Project,
    DeviceTransmissionORM as DeviceTransmission,
)
from .database import get_db_session
import logging

logger = logging.getLogger(__name__)

class OptimizedQueries:
    """
    Collection of optimized database queries for better performance
    """
    
    @staticmethod
    def get_devices_summary(page=1, per_page=20, search=None, device_type=None):
        """
        Get devices summary with only essential fields for listing
        Replaces SELECT * with specific fields
        """
        session = get_db_session()
        
        try:
            query = session.query(
                Device.id,
                Device.name,
                Device.reference,
                Device.device_type,
                Device.transmission_enabled,
                Device.current_row_index,
                Device.csv_data.isnot(None).label('has_csv_data'),
                Device.created_at,
                Device.current_project_id
            )
            
            # Apply filters
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        Device.name.ilike(search_filter),
                        Device.reference.ilike(search_filter)
                    )
                )
            
            if device_type:
                query = query.filter(Device.device_type == device_type)
            
            # Apply pagination
            total = query.count()
            devices = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                'items': [
                    {
                        'id': d.id,
                        'name': d.name,
                        'reference': d.reference,
                        'device_type': d.device_type,
                        'transmission_enabled': d.transmission_enabled,
                        'current_row_index': d.current_row_index,
                        'has_csv_data': d.has_csv_data,
                        'created_at': d.created_at.isoformat() if d.created_at else None,
                        'current_project_id': d.current_project_id
                    } for d in devices
                ],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
            
        finally:
            session.close()
    
    @staticmethod
    def get_connections_summary(page=1, per_page=20, search=None, connection_type=None, active=None):
        """
        Get connections summary with only essential fields
        """
        session = get_db_session()
        
        try:
            query = session.query(
                Connection.id,
                Connection.name,
                Connection.type,
                Connection.host,
                Connection.port,
                Connection.is_active,
                Connection.created_at,
                Connection.updated_at,
            )
            
            # Apply filters
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        Connection.name.ilike(search_filter),
                        Connection.host.ilike(search_filter)
                    )
                )
            
            if connection_type:
                query = query.filter(Connection.type == connection_type)
                
            if active is not None:
                query = query.filter(Connection.is_active == active)
            
            # Apply pagination
            total = query.count()
            connections = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                'items': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'type': c.type,
                        'host': c.host,
                        'port': c.port,
                        'is_active': c.is_active,
                        'created_at': c.created_at.isoformat() if c.created_at else None,
                        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                    } for c in connections
                ],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
            
        finally:
            session.close()
    
    @staticmethod
    def get_projects_summary(page=1, per_page=20, search=None, active=None, transmission_status=None):
        """
        Get projects summary with device count and transmission stats
        """
        session = get_db_session()
        
        try:
            # Subquery to count devices per project
            device_count_subq = session.query(
                Device.current_project_id,
                func.count(Device.id).label('device_count')
            ).filter(
                Device.current_project_id.isnot(None)
            ).group_by(Device.current_project_id).subquery()
            
            # Main query with optimized fields
            query = session.query(
                Project.id,
                Project.name,
                Project.description,
                Project.is_active,
                Project.transmission_status,
                Project.created_at,
                func.coalesce(device_count_subq.c.device_count, 0).label('devices_count')
            ).outerjoin(
                device_count_subq,
                Project.id == device_count_subq.c.current_project_id
            )
            
            # Apply filters
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        Project.name.ilike(search_filter),
                        Project.description.ilike(search_filter)
                    )
                )
            
            if active is not None:
                query = query.filter(Project.is_active == active)
                
            if transmission_status:
                query = query.filter(Project.transmission_status == transmission_status)
            
            # Apply pagination
            total = query.count()
            projects = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                'items': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'description': p.description,
                        'is_active': p.is_active,
                        'transmission_status': p.transmission_status,
                        'created_at': p.created_at.isoformat() if p.created_at else None,
                        'devices_count': p.devices_count or 0
                    } for p in projects
                ],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
            
        finally:
            session.close()
    
    @staticmethod
    def get_device_transmission_history(device_id, limit=20, offset=0):
        """
        Get transmission history with optimized fields
        """
        session = get_db_session()
        
        try:
            query = session.query(
                DeviceTransmission.id,
                DeviceTransmission.device_id,
                DeviceTransmission.connection_id,
                DeviceTransmission.status,
                DeviceTransmission.transmission_time,
                DeviceTransmission.response_time,
                DeviceTransmission.error_message,
                DeviceTransmission.data_sent
            ).filter(
                DeviceTransmission.device_id == device_id
            ).order_by(
                DeviceTransmission.transmission_time.desc()
            )
            
            total = query.count()
            transmissions = query.offset(offset).limit(limit).all()
            
            return {
                'items': [
                    {
                        'id': t.id,
                        'device_id': t.device_id,
                        'connection_id': t.connection_id,
                        'status': t.status,
                        'transmission_time': t.transmission_time.isoformat() if t.transmission_time else None,
                        'response_time': t.response_time,
                        'error_message': t.error_message,
                        'data_sent': t.data_sent
                    } for t in transmissions
                ],
                'total': total
            }
            
        finally:
            session.close()
    
    @staticmethod
    def get_active_connections_for_selector():
        """
        Get minimal connection data for dropdowns/selectors
        """
        session = get_db_session()
        
        try:
            connections = session.query(
                Connection.id,
                Connection.name,
                Connection.type,
                Connection.host,
                Connection.port
            ).filter(
                Connection.is_active == True
            ).order_by(Connection.name).all()
            
            return [
                {
                    'id': c.id,
                    'name': c.name,
                    'type': c.type,
                    'host': c.host,
                    'port': c.port
                } for c in connections
            ]
            
        finally:
            session.close()
    
    @staticmethod
    def get_project_with_devices(project_id):
        """
        Get project with eager-loaded devices to avoid N+1 queries
        Task 10.3.3 implementation
        """
        session = get_db_session()
        
        try:
            project = session.query(Project).options(
                selectinload(Project.devices).load_only(
                    Device.id,
                    Device.name,
                    Device.reference,
                    Device.device_type,
                    Device.transmission_enabled,
                    Device.csv_data
                )
            ).filter(Project.id == project_id).first()
            
            if not project:
                return None
            
            return {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'is_active': project.is_active,
                'transmission_status': project.transmission_status,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'last_transmission': project.last_transmission.isoformat() if project.last_transmission else None,
                'devices': [
                    {
                        'id': d.id,
                        'name': d.name,
                        'reference': d.reference,
                        'device_type': d.device_type,
                        'transmission_enabled': d.transmission_enabled,
                        'has_csv_data': d.csv_data is not None
                    } for d in project.devices
                ]
            }
            
        finally:
            session.close()
    
    @staticmethod
    def get_unassigned_devices_summary():
        """
        Get devices not assigned to any project (optimized)
        """
        session = get_db_session()
        
        try:
            devices = session.query(
                Device.id,
                Device.name,
                Device.reference,
                Device.device_type,
                Device.csv_data.isnot(None).label('has_csv_data')
            ).filter(
                Device.current_project_id.is_(None)
            ).order_by(Device.name).all()
            
            return [
                {
                    'id': d.id,
                    'name': d.name,
                    'reference': d.reference,
                    'device_type': d.device_type,
                    'has_csv_data': d.has_csv_data
                } for d in devices
            ]
            
        finally:
            session.close()
