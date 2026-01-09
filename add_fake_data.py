"""
Script to populate the database with fake historical data for testing.
Adds 2 years of random habit completion data.
"""
from datetime import date, timedelta
import random
from database import get_db_connection
from models import get_all_habits

def add_fake_historical_data(days_back=730):
    """
    Add fake completion data for all habits going back N days with dramatic variance.

    Args:
        days_back: Number of days of history to generate (default 730 = ~2 years)
    """
    habits = get_all_habits()

    if not habits:
        print("No habits found in database")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    today = date.today()
    events_added = 0

    print(f"Adding {days_back} days of fake data for {len(habits)} habits...")

    for habit in habits:
        habit_id = habit['habit_id']
        habit_name = habit['habit_name']

        # Start with a random completion rate
        base_rate = random.uniform(0.4, 0.8)
        current_rate = base_rate

        print(f"  Habit '{habit_name}' (ID {habit_id}): Starting at {base_rate*100:.0f}% completion rate with high variance")

        # Generate events for each day with dramatic swings
        for days_ago in range(days_back, 0, -1):
            log_date = today - timedelta(days=days_ago)
            log_date_str = log_date.strftime('%Y-%m-%d')

            # Add dramatic variance - rate can swing by up to 30% each period
            if days_ago % 30 == 0:  # Every 30 days, make a significant change
                change = random.uniform(-0.3, 0.3)
                current_rate = max(0.1, min(0.95, current_rate + change))

            # Daily small variations
            daily_variation = random.uniform(-0.05, 0.05)
            daily_rate = max(0.0, min(1.0, current_rate + daily_variation))

            # Randomly decide if this day was completed
            is_completed = random.random() < daily_rate

            event_type = 'mark_complete' if is_completed else 'mark_incomplete'

            try:
                cursor.execute("""
                    INSERT INTO habit_events (habit_id, log_date, event_type)
                    VALUES (?, ?, ?)
                """, (habit_id, log_date_str, event_type))
                events_added += 1

            except Exception as e:
                print(f"    Error adding event for {log_date_str}: {e}")

        conn.commit()

    conn.close()

    print(f"\nSuccessfully added {events_added} events!")
    print(f"Total days per habit: {days_back}")
    print(f"Total habits: {len(habits)}")

if __name__ == '__main__':
    # Clear existing events first (optional - comment out if you want to keep existing data)
    print("Clearing existing habit events...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habit_events WHERE event_type IN ('mark_complete', 'mark_incomplete')")
    conn.commit()
    conn.close()
    print("Existing events cleared.\n")

    # Add 2 years of fake data
    add_fake_historical_data(days_back=730)
