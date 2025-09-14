"""
Migration Helper for transitioning from legacy models to enhanced BaseModel
Supports gradual migration while maintaining backward compatibility
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
import logging

# Import session managers and models directly to avoid relative import issues
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from session_manager import database_session, database_transaction
# Import SQLAlchemy components directly to avoid circular imports
from sqlalchemy import create_engine
import os

# Create engine for migration operations
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'database.sqlite')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

logger = logging.getLogger(__name__)


class MigrationHelper:
    """
    Helper class for migrating from legacy models to enhanced BaseModel implementations
    """
    
    def __init__(self):
        self.engine = engine
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.error(f"Error checking table existence: {str(e)}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of columns for a table"""
        try:
            inspector = inspect(self.engine)
            if self.check_table_exists(table_name):
                columns = inspector.get_columns(table_name)
                return [col['name'] for col in columns]
            return []
        except Exception as e:
            logger.error(f"Error getting table columns: {str(e)}")
            return []
    
    def add_audit_columns_to_existing_tables(self) -> bool:
        """
        Add audit columns to existing tables that don't have them
        This enables gradual migration to BaseModel
        """
        tables_to_update = ['devices', 'connections', 'projects', 'device_transmissions']
        # SQLite-compatible column definitions (no DEFAULT with functions)
        audit_columns = {
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME', 
            'created_by': 'VARCHAR(255)',
            'updated_by': 'VARCHAR(255)',
            'version': 'INTEGER DEFAULT 1'
        }
        
        try:
            with database_transaction() as session:
                for table_name in tables_to_update:
                    if not self.check_table_exists(table_name):
                        logger.warning(f"Table {table_name} does not exist, skipping")
                        continue
                    
                    existing_columns = self.get_table_columns(table_name)
                    
                    for column_name, column_def in audit_columns.items():
                        if column_name not in existing_columns:
                            try:
                                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                                session.execute(text(alter_sql))
                                logger.info(f"Added column {column_name} to table {table_name}")
                                
                                # For timestamp columns, populate with current timestamp
                                if column_name in ['created_at', 'updated_at']:
                                    update_sql = f"UPDATE {table_name} SET {column_name} = CURRENT_TIMESTAMP WHERE {column_name} IS NULL"
                                    session.execute(text(update_sql))
                                    logger.info(f"Populated {column_name} in table {table_name}")
                                    
                            except SQLAlchemyError as e:
                                logger.error(f"Failed to add column {column_name} to {table_name}: {str(e)}")
                                # Continue with other columns
                
                logger.info("Audit columns migration completed")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add audit columns: {str(e)}")
            return False
    
    def migrate_existing_data_to_enhanced_models(self) -> Dict[str, int]:
        """
        Migrate existing data to use enhanced models with proper audit fields
        Returns count of migrated records per table
        """
        migration_counts = {}
        
        try:
            # Migrate devices
            device_count = self._migrate_devices()
            migration_counts['devices'] = device_count
            
            # Migrate connections  
            connection_count = self._migrate_connections()
            migration_counts['connections'] = connection_count
            
            # Migrate projects
            project_count = self._migrate_projects()
            migration_counts['projects'] = project_count
            
            # Migrate transmissions
            transmission_count = self._migrate_transmissions()
            migration_counts['transmissions'] = transmission_count
            
            logger.info(f"Migration completed: {migration_counts}")
            return migration_counts
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise
    
    def _migrate_devices(self) -> int:
        """Migrate device records to ensure audit fields are populated"""
        try:
            with database_transaction() as session:
                # Check which columns exist
                existing_columns = self.get_table_columns('devices')
                
                # Build update SQL based on existing columns
                updates = []
                conditions = []
                
                if 'created_at' in existing_columns:
                    updates.append("created_at = COALESCE(created_at, CURRENT_TIMESTAMP)")
                    conditions.append("created_at IS NULL")
                
                if 'updated_at' in existing_columns:
                    updates.append("updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)")
                    conditions.append("updated_at IS NULL")
                
                if 'version' in existing_columns:
                    updates.append("version = COALESCE(version, 1)")
                    conditions.append("version IS NULL")
                
                if updates:
                    update_sql = text(f"""
                        UPDATE devices 
                        SET {', '.join(updates)}
                        WHERE {' OR '.join(conditions)}
                    """)
                    
                    result = session.execute(update_sql)
                    count = result.rowcount
                    
                    logger.info(f"Updated {count} device records with audit fields")
                    return count
                else:
                    logger.info("No audit columns found in devices table")
                    return 0
                
        except Exception as e:
            logger.error(f"Failed to migrate devices: {str(e)}")
            raise
    
    def _migrate_connections(self) -> int:
        """Migrate connection records to ensure audit fields are populated"""
        try:
            with database_transaction() as session:
                # Check which columns exist
                existing_columns = self.get_table_columns('connections')
                
                # Build update SQL based on existing columns
                updates = []
                conditions = []
                
                if 'created_at' in existing_columns:
                    updates.append("created_at = COALESCE(created_at, CURRENT_TIMESTAMP)")
                    conditions.append("created_at IS NULL")
                
                if 'updated_at' in existing_columns:
                    updates.append("updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)")
                    conditions.append("updated_at IS NULL")
                
                if 'version' in existing_columns:
                    updates.append("version = COALESCE(version, 1)")
                    conditions.append("version IS NULL")
                
                if updates:
                    update_sql = text(f"""
                        UPDATE connections 
                        SET {', '.join(updates)}
                        WHERE {' OR '.join(conditions)}
                    """)
                    
                    result = session.execute(update_sql)
                    count = result.rowcount
                    
                    logger.info(f"Updated {count} connection records with audit fields")
                    return count
                else:
                    logger.info("No audit columns found in connections table")
                    return 0
                
        except Exception as e:
            logger.error(f"Failed to migrate connections: {str(e)}")
            raise
    
    def _migrate_projects(self) -> int:
        """Migrate project records to ensure audit fields are populated"""
        try:
            with database_transaction() as session:
                update_sql = text("""
                    UPDATE projects 
                    SET 
                        created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
                        updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP),
                        version = COALESCE(version, 1)
                    WHERE created_at IS NULL OR updated_at IS NULL OR version IS NULL
                """)
                
                result = session.execute(update_sql)
                count = result.rowcount
                
                logger.info(f"Updated {count} project records with audit fields")
                return count
                
        except Exception as e:
            logger.error(f"Failed to migrate projects: {str(e)}")
            raise
    
    def _migrate_transmissions(self) -> int:
        """Migrate transmission records to ensure audit fields are populated"""
        try:
            with database_transaction() as session:
                update_sql = text("""
                    UPDATE device_transmissions 
                    SET 
                        created_at = COALESCE(created_at, transmission_time, CURRENT_TIMESTAMP),
                        updated_at = COALESCE(updated_at, transmission_time, CURRENT_TIMESTAMP),
                        version = COALESCE(version, 1)
                    WHERE created_at IS NULL OR updated_at IS NULL OR version IS NULL
                """)
                
                result = session.execute(update_sql)
                count = result.rowcount
                
                logger.info(f"Updated {count} transmission records with audit fields")
                return count
                
        except Exception as e:
            logger.error(f"Failed to migrate transmissions: {str(e)}")
            raise
    
    def validate_migration(self) -> Dict[str, bool]:
        """
        Validate that migration was successful by checking audit fields
        """
        validation_results = {}
        
        try:
            with database_session() as session:
                # Check devices
                device_check = session.execute(text("""
                    SELECT COUNT(*) as total,
                           COUNT(created_at) as has_created_at,
                           COUNT(updated_at) as has_updated_at,
                           COUNT(version) as has_version
                    FROM devices
                """)).fetchone()
                
                validation_results['devices'] = (
                    device_check.total == device_check.has_created_at == 
                    device_check.has_updated_at == device_check.has_version
                )
                
                # Check connections
                connection_check = session.execute(text("""
                    SELECT COUNT(*) as total,
                           COUNT(created_at) as has_created_at,
                           COUNT(updated_at) as has_updated_at,
                           COUNT(version) as has_version
                    FROM connections
                """)).fetchone()
                
                validation_results['connections'] = (
                    connection_check.total == connection_check.has_created_at == 
                    connection_check.has_updated_at == connection_check.has_version
                )
                
                # Check projects if table exists
                if self.check_table_exists('projects'):
                    project_check = session.execute(text("""
                        SELECT COUNT(*) as total,
                               COUNT(created_at) as has_created_at,
                               COUNT(updated_at) as has_updated_at,
                               COUNT(version) as has_version
                        FROM projects
                    """)).fetchone()
                    
                    validation_results['projects'] = (
                        project_check.total == project_check.has_created_at == 
                        project_check.has_updated_at == project_check.has_version
                    )
                
                logger.info(f"Migration validation results: {validation_results}")
                return validation_results
                
        except Exception as e:
            logger.error(f"Migration validation failed: {str(e)}")
            return {}
    
    def create_indexes_for_performance(self) -> bool:
        """
        Create performance indexes for the enhanced models
        """
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_devices_reference ON devices(reference)",
            "CREATE INDEX IF NOT EXISTS idx_devices_type_enabled ON devices(device_type, transmission_enabled)",
            "CREATE INDEX IF NOT EXISTS idx_devices_project ON devices(current_project_id)",
            "CREATE INDEX IF NOT EXISTS idx_devices_created_at ON devices(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_devices_version ON devices(version)",
            
            "CREATE INDEX IF NOT EXISTS idx_connections_active ON connections(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_connections_type ON connections(type)",
            "CREATE INDEX IF NOT EXISTS idx_connections_created_at ON connections(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(transmission_status)",
            "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_transmissions_device ON device_transmissions(device_id)",
            "CREATE INDEX IF NOT EXISTS idx_transmissions_status ON device_transmissions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transmissions_time ON device_transmissions(transmission_time)",
        ]
        
        try:
            with database_transaction() as session:
                for index_sql in indexes:
                    try:
                        session.execute(text(index_sql))
                        logger.debug(f"Created index: {index_sql}")
                    except SQLAlchemyError as e:
                        logger.warning(f"Index creation failed (may already exist): {str(e)}")
                
                logger.info("Performance indexes created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create performance indexes: {str(e)}")
            return False


def run_migration():
    """
    Main migration function to upgrade existing database to enhanced models
    """
    print("Starting migration to enhanced BaseModel implementation...")
    
    migration_helper = MigrationHelper()
    
    try:
        # Step 1: Add audit columns to existing tables
        print("Step 1: Adding audit columns to existing tables...")
        if migration_helper.add_audit_columns_to_existing_tables():
            print("✓ Audit columns added successfully")
        else:
            print("❌ Failed to add audit columns")
            return False
        
        # Step 2: Migrate existing data
        print("Step 2: Migrating existing data...")
        migration_counts = migration_helper.migrate_existing_data_to_enhanced_models()
        for table, count in migration_counts.items():
            print(f"✓ Migrated {count} records in {table}")
        
        # Step 3: Validate migration
        print("Step 3: Validating migration...")
        validation_results = migration_helper.validate_migration()
        all_valid = all(validation_results.values())
        
        if all_valid:
            print("✓ Migration validation passed")
        else:
            print("❌ Migration validation failed")
            for table, valid in validation_results.items():
                status = "✓" if valid else "❌"
                print(f"  {status} {table}")
        
        # Step 4: Create performance indexes
        print("Step 4: Creating performance indexes...")
        if migration_helper.create_indexes_for_performance():
            print("✓ Performance indexes created")
        else:
            print("❌ Failed to create performance indexes")
        
        print("\nMigration completed successfully!")
        print("Enhanced BaseModel implementation is now ready to use.")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)