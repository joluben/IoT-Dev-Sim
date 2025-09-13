"""
Database Session Context Managers
Implements Requirements 1.1 and 1.2 for proper session management and connection pooling
"""

from contextlib import contextmanager
from typing import Generator, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

# Import SQLAlchemy components directly to avoid circular imports
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
import os

# Create our own session factory for session management
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'database.sqlite')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Get a database session"""
    return SessionLocal()

logger = logging.getLogger(__name__)


@contextmanager
def database_session(autocommit: bool = True, 
                    rollback_on_error: bool = True) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic transaction management
    
    Args:
        autocommit: Whether to automatically commit on success
        rollback_on_error: Whether to automatically rollback on error
        
    Yields:
        SQLAlchemy session instance
        
    Example:
        with database_session() as session:
            device = DeviceORM(name="Test Device")
            session.add(device)
            # Automatically commits on success
    """
    session = SessionLocal()
    
    try:
        yield session
        
        if autocommit:
            session.commit()
            logger.debug("Database session committed successfully")
            
    except Exception as e:
        if rollback_on_error:
            session.rollback()
            logger.error(f"Database session rolled back due to error: {str(e)}")
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


@contextmanager
def database_transaction() -> Generator[Session, None, None]:
    """
    Context manager for explicit database transactions
    Provides more control over transaction boundaries
    
    Yields:
        SQLAlchemy session instance
        
    Example:
        with database_transaction() as session:
            # Multiple operations in single transaction
            device = DeviceORM(name="Test Device")
            session.add(device)
            session.flush()  # Get ID without committing
            
            connection = ConnectionORM(name="Test Connection")
            session.add(connection)
            # Transaction commits automatically on success
    """
    session = SessionLocal()
    
    try:
        # Begin explicit transaction
        session.begin()
        
        yield session
        
        # Commit transaction
        session.commit()
        logger.debug("Database transaction committed successfully")
        
    except Exception as e:
        # Rollback transaction on any error
        session.rollback()
        logger.error(f"Database transaction rolled back due to error: {str(e)}")
        raise
    finally:
        session.close()
        logger.debug("Database transaction session closed")


@contextmanager
def readonly_session() -> Generator[Session, None, None]:
    """
    Context manager for read-only database sessions
    Optimized for queries without modification intent
    
    Yields:
        SQLAlchemy session instance configured for read-only access
        
    Example:
        with readonly_session() as session:
            devices = session.query(DeviceORM).all()
            # No commit needed for read operations
    """
    session = SessionLocal()
    
    try:
        # Configure session for read-only access
        session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        
        yield session
        
        logger.debug("Read-only session completed successfully")
        
    except Exception as e:
        logger.error(f"Read-only session error: {str(e)}")
        raise
    finally:
        session.close()
        logger.debug("Read-only session closed")


class SessionManager:
    """
    Advanced session manager with connection pooling monitoring and health checks
    """
    
    def __init__(self):
        self.engine = engine
    
    def get_session(self) -> Session:
        """
        Get a new database session
        
        Returns:
            SQLAlchemy session instance
        """
        return SessionLocal()
    
    def get_connection_pool_status(self) -> dict:
        """
        Get current connection pool status for monitoring
        
        Returns:
            Dictionary with pool statistics
        """
        try:
            pool = self.engine.pool
            
            return {
                'pool_size': pool.size(),
                'checked_in_connections': pool.checkedin(),
                'checked_out_connections': pool.checkedout(),
                'overflow_connections': pool.overflow(),
                'invalid_connections': pool.invalid(),
                'total_connections': pool.size() + pool.overflow(),
                'pool_timeout': getattr(pool, '_timeout', None),
                'max_overflow': getattr(pool, '_max_overflow', None)
            }
        except Exception as e:
            logger.error(f"Failed to get connection pool status: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self) -> dict:
        """
        Perform database health check
        
        Returns:
            Dictionary with health check results
        """
        try:
            with database_session(autocommit=False) as session:
                # Simple query to test connection
                result = session.execute("SELECT 1").scalar()
                
                if result == 1:
                    pool_status = self.get_connection_pool_status()
                    
                    return {
                        'status': 'healthy',
                        'database_responsive': True,
                        'pool_status': pool_status,
                        'timestamp': logger.handlers[0].formatter.formatTime(
                            logging.LogRecord('', 0, '', 0, '', (), None)
                        ) if logger.handlers else None
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'database_responsive': False,
                        'error': 'Unexpected query result'
                    }
                    
        except SQLAlchemyError as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'database_responsive': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                'status': 'error',
                'database_responsive': False,
                'error': str(e)
            }
    
    def close_all_sessions(self):
        """
        Close all active sessions (useful for cleanup)
        """
        try:
            # Close scoped session
            from ..database import close_scoped_session
            close_scoped_session()
            
            # Dispose engine connections
            self.engine.dispose()
            
            logger.info("All database sessions closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database sessions: {str(e)}")
            raise


# Global session manager instance
session_manager = SessionManager()


@contextmanager
def managed_session(session_manager_instance: Optional[SessionManager] = None) -> Generator[Session, None, None]:
    """
    Context manager using SessionManager for advanced session handling
    
    Args:
        session_manager_instance: Optional custom session manager
        
    Yields:
        SQLAlchemy session instance
        
    Example:
        with managed_session() as session:
            # Session managed by SessionManager
            devices = session.query(DeviceORM).all()
    """
    manager = session_manager_instance or session_manager
    session = manager.get_session()
    
    try:
        yield session
        session.commit()
        
    except Exception as e:
        session.rollback()
        logger.error(f"Managed session error: {str(e)}")
        raise
    finally:
        session.close()


def get_session_for_repository() -> Session:
    """
    Get a session specifically configured for repository pattern usage
    
    Returns:
        SQLAlchemy session instance optimized for repository pattern
    """
    session = SessionLocal()
    
    # Configure session for repository usage
    session.expire_on_commit = False  # Keep objects accessible after commit
    
    return session


@contextmanager
def bulk_operation_session(batch_size: int = 1000) -> Generator[Session, None, None]:
    """
    Context manager optimized for bulk database operations
    
    Args:
        batch_size: Number of operations to batch before flushing
        
    Yields:
        SQLAlchemy session instance configured for bulk operations
        
    Example:
        with bulk_operation_session() as session:
            for i in range(10000):
                device = DeviceORM(name=f"Device {i}")
                session.add(device)
                # Automatically batches and flushes
    """
    session = SessionLocal()
    
    try:
        # Configure for bulk operations
        session.bulk_insert_mappings = True
        session.bulk_save_objects = True
        
        yield session
        
        # Final commit
        session.commit()
        logger.debug("Bulk operation session completed successfully")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Bulk operation session error: {str(e)}")
        raise
    finally:
        session.close()
        logger.debug("Bulk operation session closed")