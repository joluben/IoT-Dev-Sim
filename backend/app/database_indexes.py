"""
Database Indexes for Performance Optimization
Task 10.3.1 - Create indexes to improve query performance
"""

from .database import get_db_session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def create_performance_indexes():
    """
    Create database indexes for improved query performance
    """
    session = get_db_session()
    
    indexes = [
        # Index on device_type for filtering devices by type
        "CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);",
        
        # Index on transmission_enabled for filtering active transmissions
        "CREATE INDEX IF NOT EXISTS idx_devices_transmission_enabled ON devices(transmission_enabled);",
        
        # Composite index for transmission history queries
        "CREATE INDEX IF NOT EXISTS idx_transmissions_device_time ON device_transmissions(device_id, transmission_time);",
        
        # Index on connection status for filtering active connections
        "CREATE INDEX IF NOT EXISTS idx_connections_active ON connections(is_active);",
        
        # Index on project status for filtering projects
        "CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);",
        
        # Index on project transmission status
        "CREATE INDEX IF NOT EXISTS idx_projects_transmission_status ON projects(transmission_status);",
        
        # Index on device reference for unique lookups
        "CREATE INDEX IF NOT EXISTS idx_devices_reference ON devices(reference);",
        
        # Index on connection type for filtering
        "CREATE INDEX IF NOT EXISTS idx_connections_type ON connections(type);",
        
        # Index on device current_project_id for project queries
        "CREATE INDEX IF NOT EXISTS idx_devices_project ON devices(current_project_id);",
        
        # Index on created_at for chronological queries
        "CREATE INDEX IF NOT EXISTS idx_devices_created_at ON devices(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_connections_created_at ON connections(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);"
    ]
    
    try:
        for index_sql in indexes:
            logger.info(f"Creating index: {index_sql}")
            session.execute(text(index_sql))
        
        session.commit()
        logger.info("All performance indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def drop_performance_indexes():
    """
    Drop performance indexes (for rollback purposes)
    """
    session = get_db_session()
    
    indexes_to_drop = [
        "DROP INDEX IF EXISTS idx_devices_type;",
        "DROP INDEX IF EXISTS idx_devices_transmission_enabled;",
        "DROP INDEX IF EXISTS idx_transmissions_device_time;",
        "DROP INDEX IF EXISTS idx_connections_active;",
        "DROP INDEX IF EXISTS idx_projects_active;",
        "DROP INDEX IF EXISTS idx_projects_transmission_status;",
        "DROP INDEX IF EXISTS idx_devices_reference;",
        "DROP INDEX IF EXISTS idx_connections_type;",
        "DROP INDEX IF EXISTS idx_devices_project;",
        "DROP INDEX IF EXISTS idx_devices_created_at;",
        "DROP INDEX IF EXISTS idx_connections_created_at;",
        "DROP INDEX IF EXISTS idx_projects_created_at;"
    ]
    
    try:
        for drop_sql in indexes_to_drop:
            logger.info(f"Dropping index: {drop_sql}")
            session.execute(text(drop_sql))
        
        session.commit()
        logger.info("All performance indexes dropped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error dropping indexes: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    # Run index creation when script is executed directly
    success = create_performance_indexes()
    if success:
        print("✅ Database indexes created successfully")
    else:
        print("❌ Failed to create database indexes")
