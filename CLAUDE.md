# Century Tracker Project

## Overview
A minimal habit tracking app using a rolling 100-day window. Users log daily habit completion, and each habit displays a card showing how many days out of the last 100 (including today) the habit was completed. 

## User Context
- User is a data scientist with SQL and Python experience
- New to app development
- First time using Claude Code to build an app

## Tech Stack
- Python (primary language)
- SQLITE for backend (at first hosted locally)
- Future: Web interface and iphone app 

## Project Requirements
- **Initial version should be VERY SIMPLE**
- **Must work on iPhone**
- Focus on core functionality first, expand later
- Keep code clear and well-documented

## Development Approach
- Start with basic functionality
- Prioritize simplicity over complexity
- Build incrementally
- Test as we go

## Coding Preferences
- Clear, readable Python code
- Simple architecture suitable for beginners
- Focus on data scientist-friendly patterns
- Avoid over-engineering

## Important Notes
- This is a learning project for app development
- User has strong data/analytics background but limited app experience
- Mobile-first approach (iPhone compatibility required)

## V1 Features (Basic Functionality)

### Core Concept
- Track habits on a rolling 100-day basis (always including current date)
- Daily logging: mark which habits were completed each day
- Visual feedback: each habit shows a card displaying completion count (e.g., "45/100 days")

### Home Screen
- Button to add a habit
- Display cards for each habit showing their 100-day completion count

## Data Model (SQLite)

### Table: habits
Stores information about each habit being tracked.

```sql
CREATE TABLE habits (
    habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_name TEXT NOT NULL,
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_order INTEGER
);
```

### Table: habit_events (Event-Based System)
Stores every action as an immutable event log.

```sql
CREATE TABLE habit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    log_date DATE NOT NULL,              -- The day being marked/unmarked
    event_type TEXT NOT NULL,            -- 'mark_complete' or 'mark_incomplete'
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When action happened
    FOREIGN KEY (habit_id) REFERENCES habits(habit_id)
);
```

**Key Design Decisions:**
- **Event-based approach**: Every mark/unmark is stored as an event
- **Immutable log**: Events are never deleted, only appended
- **log_date vs event_timestamp**:
  - `log_date` = the day being tracked (e.g., marking yesterday as complete)
  - `event_timestamp` = when the user took the action (for audit trail)
- **Current state calculation**: Query most recent event for each (habit_id, log_date) pair
- **Benefits**:
  - Supports backdating (mark previous days as complete)
  - Full audit trail of all changes
  - Enables future features like history/calendar editing
  - Great for data analysis

**Example Query - Get 100-day count for a habit:**
```sql
-- Get current completion state for last 100 days
WITH latest_events AS (
    SELECT habit_id, log_date, event_type,
           ROW_NUMBER() OVER (PARTITION BY habit_id, log_date ORDER BY event_id DESC) as rn
    FROM habit_events
    WHERE habit_id = ?
      AND log_date >= date('now', '-99 days')
      AND log_date <= date('now')
)
SELECT COUNT(*) as days_completed
FROM latest_events
WHERE rn = 1 AND event_type = 'mark_complete';
```

## Future Features (Post-V1)

### Habit Initialization Options
- When adding a new habit, choose starting value: 0/100 or 100/100
- Rationale: New habits lack 99 days of historical data

### Historical Data Entry
- Calendar interface to manually add/edit habit completions for past days
- Allows backfilling data when starting to use the app

### Trend Visualization
- Trend line for each habit showing completion trajectory over time
- Visual indication of improvement or decline

### iPhone Quick Actions
- Long-press app icon to see quick action menu
- Display first 3 habits from homepage
- Tap to instantly log completion for that day (add +1)
