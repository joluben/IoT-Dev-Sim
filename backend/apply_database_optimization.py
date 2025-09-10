#!/usr/bin/env python3
"""
Database Optimization Migration Script
Task 10.3 - Apply database indexes and optimizations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database_indexes import create_performance_indexes
from app.database import get_db_session
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Check if database connection is working"""
    try:
        session = get_db_session()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_existing_indexes():
    """Check which indexes already exist"""
    session = get_db_session()
    
    try:
        # Query to check existing indexes (SQLite specific)
        result = session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """))
        
        existing_indexes = [row[0] for row in result.fetchall()]
        
        if existing_indexes:
            logger.info("📋 Existing performance indexes:")
            for idx in existing_indexes:
                logger.info(f"  - {idx}")
        else:
            logger.info("📋 No performance indexes found")
            
        return existing_indexes
        
    except Exception as e:
        logger.error(f"Error checking existing indexes: {e}")
        return []
    finally:
        session.close()

def verify_indexes_created():
    """Verify that indexes were created successfully"""
    expected_indexes = [
        'idx_devices_type',
        'idx_devices_transmission_enabled',
        'idx_transmissions_device_time',
        'idx_connections_active',
        'idx_projects_active',
        'idx_projects_transmission_status',
        'idx_devices_reference',
        'idx_connections_type',
        'idx_devices_project',
        'idx_devices_created_at',
        'idx_connections_created_at',
        'idx_projects_created_at'
    ]
    
    existing_indexes = check_existing_indexes()
    
    created_count = 0
    missing_indexes = []
    
    for expected_idx in expected_indexes:
        if expected_idx in existing_indexes:
            created_count += 1
            logger.info(f"✅ {expected_idx} - Created")
        else:
            missing_indexes.append(expected_idx)
            logger.warning(f"❌ {expected_idx} - Missing")
    
    logger.info(f"📊 Index Summary: {created_count}/{len(expected_indexes)} indexes created")
    
    if missing_indexes:
        logger.warning(f"⚠️  Missing indexes: {', '.join(missing_indexes)}")
        return False
    else:
        logger.info("🎉 All performance indexes created successfully!")
        return True

def main():
    """Main migration function"""
    logger.info("🚀 Starting Database Optimization Migration (Task 10.3)")
    logger.info("=" * 60)
    
    # Step 1: Check database connection
    logger.info("Step 1: Checking database connection...")
    if not check_database_connection():
        logger.error("❌ Migration failed: Cannot connect to database")
        return False
    
    # Step 2: Check existing indexes
    logger.info("\nStep 2: Checking existing indexes...")
    existing_indexes = check_existing_indexes()
    
    # Step 3: Create performance indexes
    logger.info("\nStep 3: Creating performance indexes...")
    success = create_performance_indexes()
    
    if not success:
        logger.error("❌ Migration failed: Could not create indexes")
        return False
    
    # Step 4: Verify indexes were created
    logger.info("\nStep 4: Verifying indexes...")
    verification_success = verify_indexes_created()
    
    if verification_success:
        logger.info("\n🎉 Database Optimization Migration completed successfully!")
        logger.info("📈 Performance improvements applied:")
        logger.info("  - Faster device filtering by type and transmission status")
        logger.info("  - Improved connection queries by status and type")
        logger.info("  - Optimized project queries with transmission status")
        logger.info("  - Enhanced transmission history performance")
        logger.info("  - Better chronological queries with created_at indexes")
        return True
    else:
        logger.error("❌ Migration completed with warnings - some indexes may be missing")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
