"""
Enhanced Models using BaseModel and Repository Pattern
Example implementations showing how to use the new base infrastructure
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
import enum
import secrets
import string
import json
from datetime import datetime

from .base_models import BaseModel, SoftDeleteMixin
from .base_repository import BaseRepository


class DeviceType(enum.Enum):
    """Enumeration for device types"""
    WEBAPP = "WebApp"
    SENSOR = "Sensor"


class TransmissionStatus(enum.Enum):
    """Enumeration for transmission status"""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class EnhancedDeviceModel(BaseModel, SoftDeleteMixin):
    """
    Enhanced Device model using BaseModel with audit fields and optimistic locking
    Replaces the legacy Device class with modern SQLAlchemy patterns
    """
    __tablename__ = 'devices'
    
    # Device identification
    reference = Column(String(8), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Device configuration
    device_type = Column(Enum(DeviceType), default=DeviceType.WEBAPP, nullable=False)
    csv_data = Column(Text)  # JSON string containing CSV data
    
    # Transmission settings
    transmission_frequency = Column(Integer, default=3600)  # seconds
    transmission_enabled = Column(Boolean, default=False)
    current_row_index = Column(Integer, default=0)
    last_transmission = Column(DateTime)
    selected_connection_id = Column(Integer, ForeignKey('connections.id'))
    include_device_id_in_payload = Column(Boolean, default=False)
    
    # Project association
    current_project_id = Column(Integer, ForeignKey('projects.id'))
    
    # Relationships
    project = relationship("EnhancedProjectModel", back_populates="devices")
    transmissions = relationship("EnhancedTransmissionModel", back_populates="device")
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_device_type_enabled', 'device_type', 'transmission_enabled'),
        Index('idx_device_project', 'current_project_id'),
        Index('idx_device_reference', 'reference'),
    )
    
    @staticmethod
    def generate_reference():
        """Generate unique alphanumeric reference"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    def get_csv_data_parsed(self):
        """Return parsed CSV data as dictionary"""
        if not self.csv_data:
            return None
        try:
            return json.loads(self.csv_data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def update_csv_data(self, csv_data):
        """Update CSV data with JSON serialization"""
        if csv_data:
            self.csv_data = json.dumps(csv_data)
        else:
            self.csv_data = None
    
    def get_transmission_data(self):
        """Get formatted transmission data based on device type"""
        if self.device_type == DeviceType.WEBAPP:
            return self._get_full_csv_data()
        elif self.device_type == DeviceType.SENSOR:
            return self._get_next_row_data()
        return None
    
    def _get_full_csv_data(self):
        """Prepare payload for WebApp device (full CSV)"""
        csv_content = self.get_csv_data_parsed()
        if not csv_content:
            return None
        
        data_rows = csv_content.get('data') or csv_content.get('json_preview')
        if not data_rows:
            return None
        
        result_rows = []
        for row in data_rows:
            row_copy = dict(row)
            if self.include_device_id_in_payload:
                row_copy['device_id'] = self.reference
            result_rows.append(row_copy)
        
        return result_rows
    
    def _get_next_row_data(self):
        """Prepare payload for Sensor device (next row)"""
        csv_content = self.get_csv_data_parsed()
        if not csv_content:
            return None
        
        data_rows = csv_content.get('data') or csv_content.get('json_preview')
        if not data_rows or self.current_row_index >= len(data_rows):
            return None
        
        row = dict(data_rows[self.current_row_index])
        row['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        if self.include_device_id_in_payload:
            row['device_id'] = self.reference
        
        return row
    
    def advance_sensor_row(self):
        """Advance row index for sensor devices"""
        if self.device_type == DeviceType.SENSOR:
            self.current_row_index += 1
    
    def reset_sensor_position(self):
        """Reset sensor row position to beginning"""
        self.current_row_index = 0
    
    def update_last_transmission(self):
        """Update last transmission timestamp"""
        self.last_transmission = datetime.utcnow()
    
    def has_csv_data(self):
        """Check if device has CSV data loaded"""
        return bool(self.csv_data)
    
    def to_dict(self, include_audit=True):
        """Convert to dictionary with parsed CSV data"""
        result = super().to_dict(include_audit)
        
        # Replace raw CSV data with parsed version
        if 'csv_data' in result:
            result['csv_data'] = self.get_csv_data_parsed()
        
        # Convert enums to string values
        if 'device_type' in result and result['device_type']:
            result['device_type'] = result['device_type'].value if hasattr(result['device_type'], 'value') else str(result['device_type'])
        
        return result


class EnhancedConnectionModel(BaseModel):
    """Enhanced Connection model using BaseModel"""
    __tablename__ = 'connections'
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(10), nullable=False)  # 'MQTT' or 'HTTPS'
    host = Column(String(255), nullable=False)
    port = Column(Integer)
    endpoint = Column(String(500))
    auth_type = Column(String(20), nullable=False)  # 'NONE', 'USER_PASS', 'TOKEN', 'API_KEY'
    auth_config = Column(Text)  # JSON string with encrypted credentials
    connection_config = Column(Text)  # JSON string with connection settings
    is_active = Column(Boolean, default=True)
    
    # Relationships
    transmissions = relationship("EnhancedTransmissionModel", back_populates="connection")
    
    def get_auth_config_parsed(self):
        """Return parsed auth config as dictionary"""
        if not self.auth_config:
            return None
        try:
            return json.loads(self.auth_config)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def get_connection_config_parsed(self):
        """Return parsed connection config as dictionary"""
        if not self.connection_config:
            return None
        try:
            return json.loads(self.connection_config)
        except (json.JSONDecodeError, TypeError):
            return None


class EnhancedProjectModel(BaseModel):
    """Enhanced Project model using BaseModel"""
    __tablename__ = 'projects'
    
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    transmission_status = Column(Enum(TransmissionStatus), default=TransmissionStatus.INACTIVE)
    
    # Relationships
    devices = relationship("EnhancedDeviceModel", back_populates="project")
    
    def to_dict(self, include_audit=True):
        """Convert to dictionary with device count"""
        result = super().to_dict(include_audit)
        
        # Add device count
        result['devices_count'] = len(self.devices) if self.devices else 0
        
        # Convert enum to string
        if 'transmission_status' in result and result['transmission_status']:
            result['transmission_status'] = result['transmission_status'].value if hasattr(result['transmission_status'], 'value') else str(result['transmission_status'])
        
        return result


class EnhancedTransmissionModel(BaseModel):
    """Enhanced Transmission model using BaseModel"""
    __tablename__ = 'device_transmissions'
    
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    connection_id = Column(Integer, ForeignKey('connections.id'), nullable=False)
    transmission_type = Column(String(20), nullable=False)  # 'FULL_CSV', 'SINGLE_ROW'
    data_sent = Column(Text)
    row_index = Column(Integer)
    status = Column(String(20), nullable=False)  # 'SUCCESS', 'FAILED', 'PENDING'
    response_data = Column(Text)
    error_message = Column(Text)
    transmission_time = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    device = relationship("EnhancedDeviceModel", back_populates="transmissions")
    connection = relationship("EnhancedConnectionModel", back_populates="transmissions")


# Repository classes for enhanced models
class DeviceRepository(BaseRepository[EnhancedDeviceModel]):
    """Repository for Device operations with business logic"""
    
    def __init__(self, db_session=None):
        super().__init__(EnhancedDeviceModel, db_session)
    
    def create_with_reference(self, user_id=None, **kwargs):
        """Create device with auto-generated unique reference"""
        # Generate unique reference
        reference = EnhancedDeviceModel.generate_reference()
        while self.find_one_by(reference=reference):
            reference = EnhancedDeviceModel.generate_reference()
        
        kwargs['reference'] = reference
        return self.create(user_id=user_id, **kwargs)
    
    def get_by_reference(self, reference):
        """Get device by reference"""
        return self.find_one_by(reference=reference)
    
    def get_unassigned(self):
        """Get devices without project assignment"""
        return self.find_by(current_project_id=None)
    
    def get_by_project(self, project_id):
        """Get devices assigned to specific project"""
        return self.find_by(current_project_id=project_id)
    
    def get_transmission_enabled(self):
        """Get devices with transmission enabled"""
        return self.find_by(transmission_enabled=True)


class ConnectionRepository(BaseRepository[EnhancedConnectionModel]):
    """Repository for Connection operations"""
    
    def __init__(self, db_session=None):
        super().__init__(EnhancedConnectionModel, db_session)
    
    def get_active(self):
        """Get active connections"""
        return self.find_by(is_active=True)
    
    def get_by_type(self, connection_type):
        """Get connections by type (MQTT/HTTPS)"""
        return self.find_by(type=connection_type)


class ProjectRepository(BaseRepository[EnhancedProjectModel]):
    """Repository for Project operations"""
    
    def __init__(self, db_session=None):
        super().__init__(EnhancedProjectModel, db_session)
    
    def get_active(self):
        """Get active projects"""
        return self.find_by(is_active=True)
    
    def get_by_transmission_status(self, status):
        """Get projects by transmission status"""
        return self.find_by(transmission_status=status)


class TransmissionRepository(BaseRepository[EnhancedTransmissionModel]):
    """Repository for Transmission operations"""
    
    def __init__(self, db_session=None):
        super().__init__(EnhancedTransmissionModel, db_session)
    
    def get_by_device(self, device_id, limit=None):
        """Get transmissions for specific device"""
        results = self.find_by(device_id=device_id)
        if limit:
            return results[:limit]
        return results
    
    def get_by_status(self, status):
        """Get transmissions by status"""
        return self.find_by(status=status)
    
    def get_recent(self, limit=100):
        """Get recent transmissions"""
        return self.get_all(limit=limit, order_by='transmission_time', desc_order=True)