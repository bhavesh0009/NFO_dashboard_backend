#!/usr/bin/env python3
"""
Database Utility Script

Comprehensive database utility for DuckDB management.
Operations include: truncate, backup, restore, and status check.

Usage:
    # Check database status (default if no arguments provided)
    python utils/db_utility.py status
    python utils/db_utility.py
    
    # Truncate tables (with confirmation prompt)
    python utils/db_utility.py truncate
    
    # Truncate tables (skip confirmation)
    python utils/db_utility.py truncate --no-confirm
    
    # Create a backup
    python utils/db_utility.py backup
    
    # Create a labeled backup
    python utils/db_utility.py backup --label pre_release
    
    # Restore from latest backup (with confirmation)
    python utils/db_utility.py restore
    
    # Restore from specific backup file
    python utils/db_utility.py restore --file db_backups/db_backup_20250309_160000.duckdb
    
    # Restore without confirmation (use with caution)
    python utils/db_utility.py restore --no-confirm
"""

import os
import sys
import argparse
import shutil
from datetime import datetime
from logzero import logger

# Add the parent directory to the path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.db_manager import DBManager
from src.config_manager import config

def get_backup_dir():
    """Get or create backup directory"""
    backup_dir = os.path.join(parent_dir, 'db_backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir

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
        
        # Truncate tables
        result = db_manager.truncate_tables()
        
        # Close the connection
        db_manager.close()
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in truncate operation: {str(e)}")
        return False

def backup_database(label=None):
    """
    Create a backup of the database.
    
    Args:
        label: Optional label for the backup
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get database path from config
        db_path = config.get('database', 'default_path')
        if not os.path.exists(db_path):
            logger.error(f"❌ Database file does not exist: {db_path}")
            return False
            
        # Get backup directory
        backup_dir = get_backup_dir()
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        label_suffix = f"_{label}" if label else ""
        backup_filename = f"db_backup_{timestamp}{label_suffix}.duckdb"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create the backup
        logger.info(f"Creating backup of {db_path} to {backup_path}...")
        
        # Ensure the database is not locked before backup
        db_manager = DBManager()
        db_manager.close()
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        logger.info(f"✅ Database backup created: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating backup: {str(e)}")
        return False

def restore_database(backup_file=None, confirm=True):
    """
    Restore the database from a backup.
    
    Args:
        backup_file: Path to backup file or None for latest
        confirm: Whether to require confirmation
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get database path from config
        db_path = config.get('database', 'default_path')
        
        # Get backup directory
        backup_dir = get_backup_dir()
        
        # Find the backup file to restore
        if backup_file is None:
            # Get the latest backup
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.duckdb')]
            if not backups:
                logger.error("❌ No backups found to restore")
                return False
                
            backups.sort(reverse=True)  # Latest first
            backup_file = os.path.join(backup_dir, backups[0])
        else:
            if not os.path.exists(backup_file):
                logger.error(f"❌ Specified backup file not found: {backup_file}")
                return False
        
        # Confirm restore
        if confirm:
            response = input(f"⚠️ WARNING: This will overwrite the current database with {backup_file}. Continue? (y/N): ")
            if response.lower() not in ["y", "yes"]:
                logger.warning("❌ Restore cancelled by user")
                return False
        
        # Ensure the database is not locked before restore
        try:
            db_manager = DBManager()
            db_manager.close()
        except:
            pass
            
        # Create a backup of the current database before restore
        if os.path.exists(db_path):
            backup_database(label="pre_restore")
        
        # Restore the database
        logger.info(f"Restoring database from {backup_file}...")
        shutil.copy2(backup_file, db_path)
        
        logger.info(f"✅ Database restored from {backup_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error restoring database: {str(e)}")
        return False

def check_status():
    """
    Check database status.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get database path from config
        db_path = config.get('database', 'default_path')
        
        # Check if database file exists
        file_exists = os.path.exists(db_path)
        file_size = os.path.getsize(db_path) if file_exists else 0
        
        logger.info("\n=== Database Status ===")
        logger.info(f"Database file: {db_path}")
        logger.info(f"File exists: {'Yes' if file_exists else 'No'}")
        logger.info(f"File size: {file_size/1024:.2f} KB")
        
        if file_exists:
            # Connect to database and get status
            db_manager = DBManager()
            
            # Get token count
            token_count = db_manager.conn.execute("SELECT COUNT(*) FROM token_master").fetchone()[0]
            
            # Get latest update time
            latest_update = db_manager.get_latest_token_update_time()
            latest_update_str = latest_update.strftime("%Y-%m-%d %H:%M:%S") if latest_update else "Never"
            
            logger.info(f"Token count: {token_count}")
            logger.info(f"Latest update: {latest_update_str}")
            
            # Get backup status
            backup_dir = get_backup_dir()
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.duckdb')]
            logger.info(f"Available backups: {len(backups)}")
            if backups:
                backups.sort(reverse=True)  # Latest first
                latest_backup = backups[0]
                backup_path = os.path.join(backup_dir, latest_backup)
                backup_size = os.path.getsize(backup_path)
                logger.info(f"Latest backup: {latest_backup} ({backup_size/1024:.2f} KB)")
            
            db_manager.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking database status: {str(e)}")
        return False

def main():
    """Parse arguments and run operations"""
    parser = argparse.ArgumentParser(description="Database utility for DuckDB management")
    
    # Create subparsers for different operations
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")
    
    # Truncate command
    truncate_parser = subparsers.add_parser("truncate", help="Truncate database tables")
    truncate_parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")
    truncate_parser.add_argument("--force", action="store_true", help="Force truncation without safety checks")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("--label", type=str, help="Label for the backup")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("--file", type=str, help="Specific backup file to restore")
    restore_parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")
    
    # Status command
    subparsers.add_parser("status", help="Check database status")
    
    args = parser.parse_args()
    
    # Default to status if no operation specified
    if not args.operation:
        check_status()
        return
    
    # Run the specified operation
    if args.operation == "truncate":
        truncate_tables(confirm=not args.no_confirm, force=args.force)
    elif args.operation == "backup":
        backup_database(label=args.label)
    elif args.operation == "restore":
        restore_database(backup_file=args.file, confirm=not args.no_confirm)
    elif args.operation == "status":
        check_status()

if __name__ == "__main__":
    main() 