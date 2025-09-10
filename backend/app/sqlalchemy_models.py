"""
SQLAlchemy ORM Models for Phase 10 Database Optimization
Maintains compatibility with existing legacy models while providing optimized database access
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import secrets
import string
import json

from .database import Base, get_db_session


class DeviceORM(Base):
    """SQLAlchemy ORM model for devices table"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(8), unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    csv_data = Column(Text)
    created_at = Column(DateTime, default=func.now())
    device_type = Column(String, nullable=False, default='WebApp')
    transmission_frequency = Column(Integer, default=3600)
    transmission_enabled = Column(Boolean, default=False)
    current_row_index = Column(Integer, default=0)
    last_transmission = Column(DateTime)
    selected_connection_id = Column(Integer)
    include_device_id_in_payload = Column(Boolean, default=False)
    current_project_id = Column(Integer, ForeignKey('projects.id'))
    
    # Relationships
    project = relationship("ProjectORM", back_populates="devices")
    transmissions = relationship("DeviceTransmissionORM", back_populates="device")
    
    @staticmethod
    def generate_reference():
        """Generate unique alphanumeric reference"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'reference': self.reference,
            'name': self.name,
            'description': self.description,
            'csv_data': self.csv_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'device_type': self.device_type,
            'transmission_frequency': self.transmission_frequency,
            'transmission_enabled': self.transmission_enabled,
            'current_row_index': self.current_row_index,
            'last_transmission': self.last_transmission.isoformat() if self.last_transmission else None,
            'selected_connection_id': self.selected_connection_id,
            'include_device_id_in_payload': self.include_device_id_in_payload,
            'current_project_id': self.current_project_id
        }


class ConnectionORM(Base):
    """SQLAlchemy ORM model for connections table"""
    __tablename__ = 'connections'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String, nullable=False)  # 'MQTT' or 'HTTPS'
    host = Column(String, nullable=False)
    port = Column(Integer)
    endpoint = Column(String)
    auth_type = Column(String, nullable=False)  # 'NONE', 'USER_PASS', 'TOKEN', 'API_KEY'
    auth_config = Column(Text)
    connection_config = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    tests = relationship("ConnectionTestORM", back_populates="connection")
    transmissions = relationship("DeviceTransmissionORM", back_populates="connection")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'endpoint': self.endpoint,
            'auth_type': self.auth_type,
            'auth_config': json.loads(self.auth_config) if self.auth_config else None,
            'connection_config': json.loads(self.connection_config) if self.connection_config else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectORM(Base):
    """SQLAlchemy ORM model for projects table"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    transmission_status = Column(String, default='INACTIVE')  # 'INACTIVE', 'ACTIVE', 'PAUSED'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    devices = relationship("DeviceORM", back_populates="project")
    project_devices = relationship("ProjectDeviceORM", back_populates="project")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'transmission_status': self.transmission_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'devices_count': len(self.devices) if self.devices else 0
        }


class ProjectDeviceORM(Base):
    """SQLAlchemy ORM model for project_devices table"""
    __tablename__ = 'project_devices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    assigned_at = Column(DateTime, default=func.now())
    
    # Relationships
    project = relationship("ProjectORM", back_populates="project_devices")
    device = relationship("DeviceORM")


class DeviceTransmissionORM(Base):
    """SQLAlchemy ORM model for device_transmissions table"""
    __tablename__ = 'device_transmissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    connection_id = Column(Integer, ForeignKey('connections.id'), nullable=False)
    transmission_type = Column(String, nullable=False)  # 'FULL_CSV', 'SINGLE_ROW'
    data_sent = Column(Text)
    row_index = Column(Integer)
    status = Column(String, nullable=False)  # 'SUCCESS', 'FAILED', 'PENDING'
    response_data = Column(Text)
    error_message = Column(Text)
    transmission_time = Column(DateTime, default=func.now())
    
    # Relationships
    device = relationship("DeviceORM", back_populates="transmissions")
    connection = relationship("ConnectionORM", back_populates="transmissions")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'connection_id': self.connection_id,
            'transmission_type': self.transmission_type,
            'data_sent': self.data_sent,
            'row_index': self.row_index,
            'status': self.status,
            'response_data': self.response_data,
            'error_message': self.error_message,
            'transmission_time': self.transmission_time.isoformat() if self.transmission_time else None
        }


class ConnectionTestORM(Base):
    """SQLAlchemy ORM model for connection_tests table"""
    __tablename__ = 'connection_tests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(Integer, ForeignKey('connections.id'), nullable=False)
    test_result = Column(String, nullable=False)  # 'SUCCESS', 'FAILED'
    response_time = Column(Integer)
    error_message = Column(Text)
    tested_at = Column(DateTime, default=func.now())
    
    # Relationships
    connection = relationship("ConnectionORM", back_populates="tests")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'test_result': self.test_result,
            'response_time': self.response_time,
            'error_message': self.error_message,
            'tested_at': self.tested_at.isoformat() if self.tested_at else None
        }


class ScheduledTransmissionORM(Base):
    """SQLAlchemy ORM model for scheduled_transmissions table"""
    __tablename__ = 'scheduled_transmissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    connection_id = Column(Integer, ForeignKey('connections.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    next_execution = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'connection_id': self.connection_id,
            'is_active': self.is_active,
            'next_execution': self.next_execution.isoformat() if self.next_execution else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
