"""
Enhanced Base Models with Audit Fields and Optimistic Locking
Implements Requirements 1.1 and 1.2 for Database Architecture Standardization
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates
from datetime import datetime
# Import Base from SQLAlchemy directly to avoid circular imports
from sqlalchemy.ext.declarative import declarative_base

# Use the same Base that's used in the main database.py module
Base = declarative_base()


class BaseModel(Base):
    """
    Enhanced base model with audit fields and optimistic locking support.
    
    Features:
    - Automatic audit fields (created_at, updated_at, created_by, updated_by)
    - Optimistic locking with version field
    - Consistent primary key pattern
    - Automatic timestamp management
    """
    __abstract__ = True
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name if not explicitly set"""
        return cls.__name__.lower().replace('model', 's')
    
    def update_audit_fields(self, user_id=None):
        """Update audit fields for tracking changes"""
        self.updated_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id
    
    def increment_version(self):
        """Increment version for optimistic locking"""
        self.version += 1
    
    @validates('version')
    def validate_version(self, key, version):
        """Ensure version is always positive"""
        if version < 1:
            raise ValueError("Version must be positive")
        return version
    
    def to_dict(self, include_audit=True):
        """
        Convert model to dictionary for API responses
        
        Args:
            include_audit (bool): Whether to include audit fields
            
        Returns:
            dict: Model data as dictionary
        """
        result = {}
        
        # Get all columns
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Convert datetime objects to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        # Optionally exclude audit fields for cleaner API responses
        if not include_audit:
            audit_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'version']
            for field in audit_fields:
                result.pop(field, None)
        
        return result
    
    def __repr__(self):
        """String representation for debugging"""
        return f"<{self.__class__.__name__}(id={self.id}, version={self.version})>"


class AuditMixin:
    """
    Mixin for models that need enhanced audit capabilities
    Can be used in addition to BaseModel for extra audit features
    """
    
    def get_audit_info(self):
        """Get audit information as a dictionary"""
        return {
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'version': self.version
        }
    
    def has_been_modified_since(self, timestamp):
        """Check if model has been modified since given timestamp"""
        if not self.updated_at or not timestamp:
            return False
        return self.updated_at > timestamp
    
    def is_newer_version(self, other_version):
        """Check if current version is newer than provided version"""
        return self.version > other_version


class SoftDeleteMixin:
    """
    Mixin for models that support soft deletion
    """
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(255), nullable=True)
    
    def soft_delete(self, user_id=None):
        """Mark record as deleted without removing from database"""
        self.deleted_at = datetime.utcnow()
        if user_id:
            self.deleted_by = user_id
    
    def restore(self):
        """Restore soft-deleted record"""
        self.deleted_at = None
        self.deleted_by = None
    
    @property
    def is_deleted(self):
        """Check if record is soft-deleted"""
        return self.deleted_at is not None