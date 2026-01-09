"""
Core business logic for Century Tracker habit tracking.
Implements habit management, event logging, and statistics queries.
"""
from datetime import date, datetime
from typing import Optional, List, Dict
import sqlite3
from database import get_db_connection


# ==================== Habit Management ====================

def create_habit(name: str, display_order: Optional[int] = None) -> Optional[int]:
    """
    Create a new habit.

    Args:
        name: Name of the habit (e.g., "Exercise", "Read")
        display_order: Optional order for displaying on homepage

    Returns:
        habit_id of the created habit, or None if creation failed
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO habits (habit_name, display_order) VALUES (?, ?)",
            (name, display_order)
        )
        habit_id = cursor.lastrowid

        # Log habit creation event
        cursor.execute("""
            INSERT INTO habit_events (habit_id, log_date, event_type)
            VALUES (?, NULL, 'habit_created')
        """, (habit_id,))

        conn.commit()
        print(f"Created habit '{name}' with ID {habit_id}")
        return habit_id

    except sqlite3.Error as e:
        print(f"Error creating habit: {e}")
        conn.rollback()
        return None

    finally:
        conn.close()


def get_all_habits() -> List[Dict]:
    """
    Get all habits ordered by display_order.

    Returns:
        List of habit dictionaries with keys: habit_id, habit_name, date_created, display_order
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT habit_id, habit_name, date_created, display_order
            FROM habits
            ORDER BY display_order, habit_id
        """)
        rows = cursor.fetchall()
        habits = [dict(row) for row in rows]
        return habits

    except sqlite3.Error as e:
        print(f"Error fetching habits: {e}")
        return []

    finally:
        conn.close()


def get_habit_by_id(habit_id: int) -> Optional[Dict]:
    """
    Get a single habit by its ID.

    Args:
        habit_id: The ID of the habit to fetch

    Returns:
        Habit dictionary or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT habit_id, habit_name, date_created, display_order
            FROM habits
            WHERE habit_id = ?
        """, (habit_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    except sqlite3.Error as e:
        print(f"Error fetching habit: {e}")
        return None

    finally:
        conn.close()


def delete_habit(habit_id: int) -> bool:
    """
    Delete a habit and log deletion event. Historical event data is preserved.

    Args:
        habit_id: The ID of the habit to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Log deletion event BEFORE deleting habit
        cursor.execute("""
            INSERT INTO habit_events (habit_id, log_date, event_type)
            VALUES (?, NULL, 'habit_deleted')
        """, (habit_id,))

        # Delete habit from table
        cursor.execute("DELETE FROM habits WHERE habit_id = ?", (habit_id,))

        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            print(f"Deleted habit with ID {habit_id}")
        return deleted

    except sqlite3.Error as e:
        print(f"Error deleting habit: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


# ==================== Event Logging ====================

def mark_habit_complete(habit_id: int, log_date: Optional[date] = None) -> bool:
    """
    Mark a habit as complete for a given date.
    Inserts a 'mark_complete' event.

    Args:
        habit_id: The ID of the habit
        log_date: The date to mark (defaults to today)

    Returns:
        True if event logged successfully, False otherwise
    """
    if log_date is None:
        log_date = date.today()

    log_date_str = log_date.strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO habit_events (habit_id, log_date, event_type)
            VALUES (?, ?, 'mark_complete')
        """, (habit_id, log_date_str))
        conn.commit()
        print(f"Marked habit {habit_id} complete for {log_date_str}")
        return True

    except sqlite3.Error as e:
        print(f"Error logging completion: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def mark_habit_incomplete(habit_id: int, log_date: Optional[date] = None) -> bool:
    """
    Mark a habit as incomplete for a given date.
    Inserts a 'mark_incomplete' event (for toggling off).

    Args:
        habit_id: The ID of the habit
        log_date: The date to mark (defaults to today)

    Returns:
        True if event logged successfully, False otherwise
    """
    if log_date is None:
        log_date = date.today()

    log_date_str = log_date.strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO habit_events (habit_id, log_date, event_type)
            VALUES (?, ?, 'mark_incomplete')
        """, (habit_id, log_date_str))
        conn.commit()
        print(f"Marked habit {habit_id} incomplete for {log_date_str}")
        return True

    except sqlite3.Error as e:
        print(f"Error logging incompletion: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


# ==================== Statistics and Queries ====================

def get_habit_100day_count(habit_id: int, end_date: Optional[date] = None) -> int:
    """
    Get the count of completed days in the rolling 100-day window.
    Uses the event-based system to determine current state.

    Args:
        habit_id: The ID of the habit
        end_date: The end date of the window (defaults to today)

    Returns:
        Number of completed days (0-100)
    """
    if end_date is None:
        end_date = date.today()

    end_date_str = end_date.strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query using window function to get most recent event per date
        query = """
            WITH latest_events AS (
                SELECT
                    habit_id,
                    log_date,
                    event_type,
                    ROW_NUMBER() OVER (
                        PARTITION BY habit_id, log_date
                        ORDER BY event_id DESC
                    ) as rn
                FROM habit_events
                WHERE habit_id = ?
                  AND log_date >= date(?, '-99 days')
                  AND log_date <= ?
            )
            SELECT COUNT(*) as days_completed
            FROM latest_events
            WHERE rn = 1 AND event_type = 'mark_complete'
        """

        cursor.execute(query, (habit_id, end_date_str, end_date_str))
        result = cursor.fetchone()
        return result['days_completed'] if result else 0

    except sqlite3.Error as e:
        print(f"Error calculating 100-day count: {e}")
        return 0

    finally:
        conn.close()


def get_habit_stats_all() -> List[Dict]:
    """
    Get 100-day completion counts for all habits.
    Ordered by display_order for homepage display.

    Returns:
        List of dictionaries with keys: habit_id, habit_name, count, display_order
    """
    habits = get_all_habits()
    stats = []

    for habit in habits:
        habit_id = habit['habit_id']
        count = get_habit_100day_count(habit_id)
        stats.append({
            'habit_id': habit_id,
            'habit_name': habit['habit_name'],
            'count': count,
            'display_order': habit['display_order']
        })

    return stats


def get_habit_date_status(habit_id: int, log_date: date) -> bool:
    """
    Check if a habit was completed on a specific date.
    Queries the most recent event for that date.

    Args:
        habit_id: The ID of the habit
        log_date: The date to check

    Returns:
        True if completed, False otherwise
    """
    log_date_str = log_date.strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT event_type
            FROM habit_events
            WHERE habit_id = ? AND log_date = ?
            ORDER BY event_id DESC
            LIMIT 1
        """

        cursor.execute(query, (habit_id, log_date_str))
        result = cursor.fetchone()

        if result:
            return result['event_type'] == 'mark_complete'
        return False

    except sqlite3.Error as e:
        print(f"Error checking date status: {e}")
        return False

    finally:
        conn.close()


def get_habit_100day_history(habit_id: int, end_date: Optional[date] = None) -> List[bool]:
    """
    Get completion status for each of the last 100 days in reverse chronological order.
    Index 0 = today (or end_date), Index 1 = yesterday, etc.

    Args:
        habit_id: The ID of the habit
        end_date: The end date of the window (defaults to today)

    Returns:
        List of 100 booleans indicating completion status, newest first
    """
    if end_date is None:
        end_date = date.today()

    from datetime import timedelta

    history = []
    for days_ago in range(100):
        check_date = end_date - timedelta(days=days_ago)
        is_complete = get_habit_date_status(habit_id, check_date)
        history.append(is_complete)

    return history
