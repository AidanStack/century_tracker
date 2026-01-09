"""
Database connection and schema initialization for Century Tracker.
"""
import sqlite3
from typing import Optional


DATABASE_PATH = 'century_tracker.db'


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_db() -> None:
    """
    Initialize the database schema.
    Creates the habits and habit_events tables if they don't exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create habits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_name TEXT NOT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                display_order INTEGER
            )
        """)

        # Create habit_events table (event-based logging)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                log_date DATE NOT NULL,
                event_type TEXT NOT NULL,
                event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (habit_id) REFERENCES habits(habit_id)
            )
        """)

        conn.commit()
        print("Database initialized successfully")

    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        conn.rollback()

    finally:
        conn.close()


def close_db(conn: sqlite3.Connection) -> None:
    """
    Close the database connection.

    Args:
        conn: The database connection to close
    """
    if conn:
        conn.close()
