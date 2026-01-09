"""
Century Tracker - Flask application entry point.
Web interface for habit tracking with rolling 100-day window.
"""
from flask import Flask, render_template, request, redirect, url_for
from datetime import date
from database import init_db
from models import (
    get_habit_stats_all,
    create_habit,
    mark_habit_complete,
    mark_habit_incomplete,
    get_habit_date_status,
    delete_habit,
    get_habit_100day_history
)


app = Flask(__name__)


# Initialize database on startup
with app.app_context():
    init_db()


@app.route('/')
def index():
    """Home page - display all habits with their 100-day counts."""
    stats = get_habit_stats_all()
    today = date.today()

    # For each habit, check if it's already marked complete today and get daily history
    for stat in stats:
        stat['completed_today'] = get_habit_date_status(stat['habit_id'], today)
        stat['history'] = get_habit_100day_history(stat['habit_id'], today)

    return render_template('index.html', habits=stats)


@app.route('/add-habit', methods=['GET', 'POST'])
def add_habit():
    """Add new habit form."""
    if request.method == 'POST':
        habit_name = request.form.get('habit_name')
        if habit_name:
            create_habit(habit_name)
            return redirect(url_for('index'))
    return render_template('add_habit.html')


@app.route('/toggle-habit/<int:habit_id>', methods=['POST'])
def toggle_habit(habit_id):
    """Toggle habit completion for today."""
    today = date.today()
    is_complete = get_habit_date_status(habit_id, today)

    if is_complete:
        mark_habit_incomplete(habit_id)
    else:
        mark_habit_complete(habit_id)

    return redirect(url_for('index'))


@app.route('/habit/<int:habit_id>')
def habit_detail(habit_id):
    """Display habit detail page."""
    stats = get_habit_stats_all()
    habit = next((h for h in stats if h['habit_id'] == habit_id), None)

    if not habit:
        return redirect(url_for('index'))

    today = date.today()
    habit['completed_today'] = get_habit_date_status(habit_id, today)
    habit['history'] = get_habit_100day_history(habit_id, today)

    return render_template('habit_detail.html', habit=habit)


@app.route('/delete-habit/<int:habit_id>', methods=['POST'])
def delete_habit_route(habit_id):
    """Delete a habit after confirmation."""
    delete_habit(habit_id)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=5001, debug=True)
