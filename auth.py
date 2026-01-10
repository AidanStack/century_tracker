"""
User authentication module for Century Tracker.
Handles user registration, login, and password management.
"""
from typing import Optional
from datetime import datetime
import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection


class User(UserMixin):
    """
    User model for Flask-Login authentication.
    Inherits UserMixin to provide default implementations for:
    - is_authenticated, is_active, is_anonymous, get_id
    """
    def __init__(self, user_id: int, username: str, password_hash: str, date_created: datetime):
        self.id = user_id  # Flask-Login requires 'id' attribute
        self.username = username
        self.password_hash = password_hash
        self.date_created = date_created


def create_user(username: str, password: str) -> Optional[int]:
    """
    Create a new user with hashed password.

    Args:
        username: Unique username (3+ characters)
        password: Plain text password (8+ characters, will be hashed)

    Returns:
        user_id of the created user, or None if creation failed
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Hash password using pbkdf2:sha256
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        cursor.execute("""
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
        """, (username, password_hash))

        user_id = cursor.lastrowid
        conn.commit()
        print(f"Created user '{username}' with ID {user_id}")
        return user_id

    except sqlite3.IntegrityError as e:
        print(f"Error creating user (username may already exist): {e}")
        conn.rollback()
        return None

    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return None

    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[User]:
    """
    Retrieve a user by username for login authentication.

    Args:
        username: Username to look up

    Returns:
        User object if found, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT user_id, username, password_hash, date_created
            FROM users
            WHERE username = ?
        """, (username,))

        row = cursor.fetchone()
        if row:
            return User(
                user_id=row['user_id'],
                username=row['username'],
                password_hash=row['password_hash'],
                date_created=row['date_created']
            )
        return None

    except sqlite3.Error as e:
        print(f"Error fetching user by username: {e}")
        return None

    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    """
    Retrieve a user by ID for Flask-Login user_loader.

    Args:
        user_id: User ID to look up

    Returns:
        User object if found, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT user_id, username, password_hash, date_created
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        if row:
            return User(
                user_id=row['user_id'],
                username=row['username'],
                password_hash=row['password_hash'],
                date_created=row['date_created']
            )
        return None

    except sqlite3.Error as e:
        print(f"Error fetching user by ID: {e}")
        return None

    finally:
        conn.close()


def verify_password(user: User, password: str) -> bool:
    """
    Verify a password against the stored hash.

    Args:
        user: User object with password_hash attribute
        password: Plain text password to verify

    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(user.password_hash, password)
