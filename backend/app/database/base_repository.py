"""
Base Repository Pattern Implementation
Implements Requirements 1.1 and 1.2 for standardized data access patterns
"""

from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
try:
    from sqlalchemy.exc import StaleDataError
except ImportError:
    # StaleDataError might not be available in all SQLAlchemy versions
    class StaleDataError(SQLAlchemyError):
        pass
from sqlalchemy import and_, or_, desc, asc
from contextlib import contextmanager
import logging

from .base_models import BaseModel
# Import SQLAlchemy components directly to avoid circular imports
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
import os

# Create our own session factory for the repository pattern
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'database.sqlite')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Type variables for generic repository
ModelType = TypeVar('ModelType', bound=BaseModel)

logger = logging.getLogger(__name__)


class OptimisticLockError(Exception):
    """Raised when optimistic locking conflict occurs"""
    def __init__(self, message="Optimistic locking conflict detected"):
        self.message = message
        super().__init__(self.message)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing standard CRUD operations with optimistic locking
    
    Features:
    - Standard CRUD operations (Create, Read, Update, Delete)
    - Optimistic locking support
    - Transaction management
    - Error handling and logging
    - Flexible querying capabilities
    """
    
    def __init__(self, model_class: Type[ModelType], db_session: Optional[Session] = None):
        """
        Initialize repository with model class and optional session
        
        Args:
            model_class: SQLAlchemy model class
            db_session: Optional database session (will create new if not provided)
        """
        self.model_class = model_class
        self._session = db_session
    
    @property
    def session(self) -> Session:
        """Get database session, creating new one if needed"""
        if self._session is None:
            self._session = SessionLocal()
        return self._session
    
    def create(self, user_id: Optional[str] = None, **kwargs) -> ModelType:
        """
        Create new model instance
        
        Args:
            user_id: ID of user creating the record
            **kwargs: Model field values
            
        Returns:
            Created model instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Create instance
            instance = self.model_class(**kwargs)
            
            # Set audit fields
            if user_id and hasattr(instance, 'created_by'):
                instance.created_by = user_id
            
            # Add to session and commit
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            
            logger.info(f"Created {self.model_class.__name__} with ID {instance.id}")
            return instance
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to create {self.model_class.__name__}: {str(e)}")
            raise
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get model instance by ID
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        try:
            return self.session.query(self.model_class).get(id)
        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model_class.__name__} by ID {id}: {str(e)}")
            raise
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0, 
                order_by: Optional[str] = None, desc_order: bool = False) -> List[ModelType]:
        """
        Get all model instances with optional pagination and ordering
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by
            desc_order: Whether to use descending order
            
        Returns:
            List of model instances
        """
        try:
            query = self.session.query(self.model_class)
            
            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                order_field = getattr(self.model_class, order_by)
                if desc_order:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            # Apply pagination
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get all {self.model_class.__name__}: {str(e)}")
            raise
    
    def update(self, id: int, user_id: Optional[str] = None, 
               expected_version: Optional[int] = None, **kwargs) -> Optional[ModelType]:
        """
        Update model instance with optimistic locking support
        
        Args:
            id: Primary key value
            user_id: ID of user updating the record
            expected_version: Expected version for optimistic locking
            **kwargs: Field values to update
            
        Returns:
            Updated model instance or None if not found
            
        Raises:
            OptimisticLockError: If version conflict detected
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get current instance
            instance = self.get_by_id(id)
            if not instance:
                return None
            
            # Check optimistic locking if version provided
            if expected_version is not None and instance.version != expected_version:
                raise OptimisticLockError(
                    f"Version conflict: expected {expected_version}, got {instance.version}"
                )
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Update audit fields
            instance.update_audit_fields(user_id)
            instance.increment_version()
            
            # Commit changes
            self.session.commit()
            self.session.refresh(instance)
            
            logger.info(f"Updated {self.model_class.__name__} ID {id} to version {instance.version}")
            return instance
            
        except StaleDataError:
            self.session.rollback()
            raise OptimisticLockError("Concurrent modification detected")
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to update {self.model_class.__name__} ID {id}: {str(e)}")
            raise
    
    def delete(self, id: int, user_id: Optional[str] = None) -> bool:
        """
        Delete model instance
        
        Args:
            id: Primary key value
            user_id: ID of user deleting the record
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = self.get_by_id(id)
            if not instance:
                return False
            
            # Check if model supports soft delete
            if hasattr(instance, 'soft_delete'):
                instance.soft_delete(user_id)
                logger.info(f"Soft deleted {self.model_class.__name__} ID {id}")
            else:
                self.session.delete(instance)
                logger.info(f"Hard deleted {self.model_class.__name__} ID {id}")
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to delete {self.model_class.__name__} ID {id}: {str(e)}")
            raise
    
    def find_by(self, **criteria) -> List[ModelType]:
        """
        Find model instances by criteria
        
        Args:
            **criteria: Field name and value pairs
            
        Returns:
            List of matching model instances
        """
        try:
            query = self.session.query(self.model_class)
            
            # Apply filters
            for key, value in criteria.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.all()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find {self.model_class.__name__} by criteria: {str(e)}")
            raise
    
    def find_one_by(self, **criteria) -> Optional[ModelType]:
        """
        Find single model instance by criteria
        
        Args:
            **criteria: Field name and value pairs
            
        Returns:
            Model instance or None if not found
        """
        results = self.find_by(**criteria)
        return results[0] if results else None
    
    def count(self, **criteria) -> int:
        """
        Count model instances matching criteria
        
        Args:
            **criteria: Field name and value pairs
            
        Returns:
            Number of matching records
        """
        try:
            query = self.session.query(self.model_class)
            
            # Apply filters
            for key, value in criteria.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.count()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to count {self.model_class.__name__}: {str(e)}")
            raise
    
    def exists(self, id: int) -> bool:
        """
        Check if model instance exists by ID
        
        Args:
            id: Primary key value
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.session.query(self.model_class.id).filter(
                self.model_class.id == id
            ).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check existence of {self.model_class.__name__} ID {id}: {str(e)}")
            raise
    
    def bulk_create(self, instances_data: List[Dict[str, Any]], 
                   user_id: Optional[str] = None) -> List[ModelType]:
        """
        Create multiple model instances in a single transaction
        
        Args:
            instances_data: List of dictionaries with model field values
            user_id: ID of user creating the records
            
        Returns:
            List of created model instances
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instances = []
            
            for data in instances_data:
                instance = self.model_class(**data)
                if user_id and hasattr(instance, 'created_by'):
                    instance.created_by = user_id
                instances.append(instance)
            
            self.session.add_all(instances)
            self.session.commit()
            
            # Refresh all instances to get generated IDs
            for instance in instances:
                self.session.refresh(instance)
            
            logger.info(f"Bulk created {len(instances)} {self.model_class.__name__} instances")
            return instances
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to bulk create {self.model_class.__name__}: {str(e)}")
            raise
    
    def close(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None


@contextmanager
def repository_transaction(*repositories: BaseRepository):
    """
    Context manager for handling transactions across multiple repositories
    
    Args:
        *repositories: Repository instances to include in transaction
        
    Yields:
        Tuple of repository instances
        
    Example:
        with repository_transaction(device_repo, connection_repo) as (dev_repo, conn_repo):
            device = dev_repo.create(name="Test Device")
            connection = conn_repo.create(name="Test Connection")
    """
    session = SessionLocal()
    
    try:
        # Set same session for all repositories
        for repo in repositories:
            repo._session = session
        
        yield repositories
        
        # Commit transaction
        session.commit()
        
    except Exception as e:
        # Rollback on any error
        session.rollback()
        logger.error(f"Transaction failed: {str(e)}")
        raise
    finally:
        # Clean up
        session.close()
        for repo in repositories:
            repo._session = None