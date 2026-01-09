"""
Century Tracker - Flask application entry point.
Web interface for habit tracking with rolling 100-day window.
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import date
from database import init_db
from models import (
    get_habit_stats_all,
    create_habit,
    mark_habit_complete,
    mark_habit_incomplete,
    get_habit_date_status,
    delete_habit,
    get_habit_100day_history,
    get_habit_trend_data,
    rename_habit,
    update_habit_order
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

    # Check if there's a redirect URL in the form data
    next_url = request.form.get('next')
    if next_url:
        return redirect(next_url)

    return redirect(url_for('index'))


@app.route('/habit/<int:habit_id>')
def habit_detail(habit_id):
    """Display habit detail page."""
    stats = get_habit_stats_all()
    habit = next((h for h in stats if h['habit_id'] == habit_id), None)

    if not habit:
        return redirect(url_for('index'))

    # Get trend period from query parameter (default 100)
    period = request.args.get('period', 100, type=int)
    # Limit period to valid options
    if period not in [100, 200, 300, 365, 400, 500]:
        period = 100

    today = date.today()
    habit['completed_today'] = get_habit_date_status(habit_id, today)
    habit['history'] = get_habit_100day_history(habit_id, today)
    habit['trend'] = get_habit_trend_data(habit_id, today, period)
    habit['trend_period'] = period

    return render_template('habit_detail.html', habit=habit)


@app.route('/rename-habit/<int:habit_id>', methods=['POST'])
def rename_habit_route(habit_id):
    """Rename a habit."""
    new_name = request.form.get('habit_name')
    if new_name:
        rename_habit(habit_id, new_name)
    return redirect(url_for('habit_detail', habit_id=habit_id))


@app.route('/delete-habit/<int:habit_id>', methods=['POST'])
def delete_habit_route(habit_id):
    """Delete a habit after confirmation."""
    delete_habit(habit_id)
    return redirect(url_for('index'))


@app.route('/reorder-habits', methods=['POST'])
def reorder_habits():
    """Update the display order of habits."""
    data = request.get_json()
    habit_ids = data.get('habit_ids', [])

    if not habit_ids:
        return jsonify({'error': 'No habit IDs provided'}), 400

    # Convert string IDs to integers
    try:
        habit_ids = [int(id) for id in habit_ids]
    except ValueError:
        return jsonify({'error': 'Invalid habit IDs'}), 400

    success = update_habit_order(habit_ids)

    if success:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Failed to update order'}), 500


if __name__ == '__main__':
    app.run(port=5001, debug=True)
