#!/usr/bin/env python3
"""
One-time migration runner for production deployment
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run database migration"""
    try:
        # Check if we're on Fly.io (production)
        if os.getenv('FLY_APP_NAME'):
            logger.info("Running database migration on Fly.io...")
            
            # Import and run migration
            from database.migrate_to_postgres import DataMigration
            
            migration = DataMigration()
            migration.run_migration()
            
            logger.info("✅ Migration completed successfully!")
            return 0
        else:
            logger.info("Not running on Fly.io, skipping migration")
            return 0
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Don't crash the app if migration fails
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)