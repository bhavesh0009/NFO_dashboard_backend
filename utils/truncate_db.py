#!/usr/bin/env python3
"""
Database Utility Script - Truncate Tables

This script safely truncates tables in the DuckDB database.
Use this instead of manual deletion to avoid database corruption.

Usage:
    # With confirmation prompt
    python utils/truncate_db.py
    
    # Skip confirmation prompt
    python utils/truncate_db.py --no-confirm
    
    # Force truncation without any safety checks
    python utils/truncate_db.py --force
"""

import os
import sys
import argparse
from logzero import logger

# Add the parent directory to the path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.db_manager import DBManager

def truncate_tables(confirm=False, force=False):
    """
    Truncate all database tables safely.
    
    Args:
        confirm: Require user confirmation before truncating
        force: Skip confirmation even in production environment
    
    Returns:
        bool: True if successful, False otherwise
    """
    if confirm and not force:
        # Ask for confirmation
        response = input("⚠️ WARNING: This will delete ALL data from the database. Are you sure? (y/N): ")
        if response.lower() not in ["y", "yes"]:
            logger.warning("❌ Operation cancelled by user")
            return False
    
    try:
        logger.info("Connecting to database...")
        db_manager = DBManager()
        
        # Truncate the token_master table
        logger.info("Truncating token_master table...")
        db_manager.conn.execute("TRUNCATE TABLE token_master")
        
        # Add any other tables that need truncating here as the application grows
        # db_manager.conn.execute("TRUNCATE TABLE other_table")
        
        # Get the database path for logging
        db_path = db_manager.db_path
        
        # Close the connection
        db_manager.close()
        
        logger.info(f"✅ Successfully truncated all tables in database: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error truncating database tables: {str(e)}")
        return False

def main():
    """Parse arguments and run truncation"""
    parser = argparse.ArgumentParser(description="Safely truncate database tables")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--force", action="store_true", help="Force truncation without safety checks")
    args = parser.parse_args()
    
    truncate_tables(confirm=not args.no_confirm, force=args.force)

if __name__ == "__main__":
    main() 