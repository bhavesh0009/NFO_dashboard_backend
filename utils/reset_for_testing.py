#!/usr/bin/env python3
"""
Reset Database for Testing

This script safely resets the database for testing purposes.
It creates a backup before truncating all tables.

Usage:
    python utils/reset_for_testing.py
"""

import os
import sys
from logzero import logger

# Add the parent directory to the path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.db_utility import backup_database, truncate_tables

def reset_database():
    """
    Reset the database for testing.
    1. Create a backup
    2. Truncate all tables
    """
    logger.info("=== Resetting Database for Testing ===")
    
    # Create a backup first
    logger.info("Creating backup before reset...")
    if not backup_database(label="pre_reset"):
        logger.error("❌ Backup failed, aborting reset operation")
        return False
    
    # Truncate all tables
    logger.info("Truncating all tables...")
    if not truncate_tables(confirm=False):
        logger.error("❌ Truncate operation failed")
        return False
    
    logger.info("✅ Database reset completed successfully")
    return True

if __name__ == "__main__":
    reset_database() 