# my_tools/codebase_manager.py
#
# FINAL VERSION - 2025-08-06
#
# This is the single source of truth for all database interactions.
# It now supports separate, dedicated connections for safe read-only queries
# and for explicit write operations to prevent "readonly database" errors.

import os
import sqlite3
from typing import Dict, Any, Optional, List

class _CodebaseManager:
    _instance = None
    _db_filename = "project_context.db"
    
    # We now manage two separate connection objects to enforce safety.
    _read_conn = None
    _write_conn = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(_CodebaseManager, cls).__new__(cls)
        return cls._instance

    def _get_db_path(self) -> str:
        """(Internal) Helper to consistently construct the database path."""
        workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
        return os.path.abspath(os.path.join(workspace_dir, self.__class__._db_filename))

    def _get_read_connection(self):
        """(Internal) Gets a safe, read-only database connection for SELECT queries."""
        # Use the existing connection if available
        if self.__class__._read_conn:
            return self.__class__._read_conn

        db_path = self._get_db_path()
        if not os.path.exists(db_path):
            print(f"FATAL: [_CodebaseManager] Read-DB not found at '{db_path}'")
            return None
        
        try:
            # Connect using the specific read-only URI mode
            db_uri = f"file:{db_path}?mode=ro"
            connection = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            self.__class__._read_conn = connection
            return self.__class__._read_conn
        except sqlite3.Error as e:
            print(f"FATAL: [_CodebaseManager] Could not connect to Read-DB: {e}")
            return None

    def _get_write_connection(self):
        """(Internal) Gets a read-write database connection for INSERT/UPDATE/DELETE."""
        # Use the existing connection if available
        if self.__class__._write_conn:
            return self.__class__._write_conn

        db_path = self._get_db_path()
        if not os.path.exists(db_path):
            print(f"FATAL: [_CodebaseManager] Write-DB not found at '{db_path}'")
            return None
            
        try:
            # Connect in standard read-write mode
            connection = sqlite3.connect(db_path, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            self.__class__._write_conn = connection
            return self.__class__._write_conn
        except sqlite3.Error as e:
            print(f"FATAL: [_CodebaseManager] Could not connect to Write-DB: {e}")
            return None

    def _execute_read_query(self, query: str, params: tuple = ()):
        """
        (Internal) For SELECT queries. Uses a read-only connection.
        """
        connection = self._get_read_connection()
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print(f"Read query error: {e}")
            if self.__class__._read_conn:
                self.__class__._read_conn.close()
            self.__class__._read_conn = None # Force reconnect next time
            return None

    def _execute_write_query(self, query: str, params: tuple = ()):
        """
        (Internal) For INSERT, UPDATE, DELETE. Uses a read-write connection.
        """
        connection = self._get_write_connection()
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit() # CRITICAL: Commit the transaction to save changes
            return cursor
        except sqlite3.Error as e:
            print(f"Write query error: {e}")
            if self.__class__._write_conn:
                self.__class__._write_conn.close()
            self.__class__._write_conn = None # Force reconnect next time
            return None