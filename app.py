"""
Century Tracker - Flask application entry point.
Web interface for habit tracking with rolling 100-day window.
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import date
import os
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
    update_habit_order,
    verify_habit_ownership
)
from auth import User, create_user, get_user_by_username, get_user_by_id, verify_password


app = Flask(__name__)

# Secret key for session management (CRITICAL for production)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated

@login_manager.user_loader
def load_user(user_id):
    """Required by Flask-Login to reload user from session"""
    return get_user_by_id(int(user_id))

# Initialize database on startup
with app.app_context():
    init_db()


# ==================== Authentication Routes ====================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration page."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('signup.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return render_template('signup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('signup.html')

        if password != password_confirm:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')

        # Check if username exists
        existing_user = get_user_by_username(username)
        if existing_user:
            flash('Username already taken.', 'error')
            return render_template('signup.html')

        # Create user
        user_id = create_user(username, password)
        if user_id:
            # Auto-login after signup
            user = get_user_by_id(user_id)
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Error creating account. Please try again.', 'error')
            return render_template('signup.html')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        # Verify credentials
        user = get_user_by_username(username)
        if user and verify_password(user, password):
            login_user(user)

            # Redirect to 'next' page if provided, otherwise home
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Log out current user."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ==================== Habit Routes ====================

@app.route('/')
@login_required
def index():
    """Home page - display all habits with their 100-day counts."""
    stats = get_habit_stats_all(current_user.id)
    today = date.today()

    # For each habit, check if it's already marked complete today and get daily history
    for stat in stats:
        stat['completed_today'] = get_habit_date_status(stat['habit_id'], today)
        stat['history'] = get_habit_100day_history(stat['habit_id'], today)

    return render_template('index.html', habits=stats)


@app.route('/add-habit', methods=['GET', 'POST'])
@login_required
def add_habit():
    """Add new habit form."""
    if request.method == 'POST':
        habit_name = request.form.get('habit_name')
        if habit_name:
            create_habit(current_user.id, habit_name)
            return redirect(url_for('index'))
    return render_template('add_habit.html')


@app.route('/toggle-habit/<int:habit_id>', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    """Toggle habit completion for today."""
    # Verify user owns this habit
    if not verify_habit_ownership(habit_id, current_user.id):
        flash('You do not have access to that habit.', 'error')
        return redirect(url_for('index'))

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
@login_required
def habit_detail(habit_id):
    """Display habit detail page."""
    # Verify user owns this habit
    if not verify_habit_ownership(habit_id, current_user.id):
        flash('You do not have access to that habit.', 'error')
        return redirect(url_for('index'))

    stats = get_habit_stats_all(current_user.id)
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

    # Calculate month labels for x-axis (3-4 labels)
    from datetime import timedelta
    month_labels = []
    num_labels = 4
    step = period // (num_labels - 1)

    # Check if date range includes dates outside current year
    oldest_date = today - timedelta(days=period - 1)
    include_year = oldest_date.year != today.year

    # Add padding to prevent labels from appearing at edges
    padding = 40
    usable_width = 600 - (2 * padding)

    for i in range(num_labels):
        days_ago = period - 1 - (i * step)
        if days_ago < 0:
            days_ago = 0
        label_date = today - timedelta(days=days_ago)
        x_position = padding + (i * step) * (usable_width / (period - 1))

        # Format label with year if needed
        if include_year:
            label_text = label_date.strftime('%b %y')
        else:
            label_text = label_date.strftime('%b')

        month_labels.append({
            'label': label_text,
            'x': x_position
        })

    habit['month_labels'] = month_labels

    return render_template('habit_detail.html', habit=habit)


@app.route('/rename-habit/<int:habit_id>', methods=['POST'])
@login_required
def rename_habit_route(habit_id):
    """Rename a habit."""
    # Verify user owns this habit
    if not verify_habit_ownership(habit_id, current_user.id):
        flash('You do not have access to that habit.', 'error')
        return redirect(url_for('index'))

    new_name = request.form.get('habit_name')
    if new_name:
        rename_habit(habit_id, new_name)
    return redirect(url_for('habit_detail', habit_id=habit_id))


@app.route('/delete-habit/<int:habit_id>', methods=['POST'])
@login_required
def delete_habit_route(habit_id):
    """Delete a habit after confirmation."""
    # Verify user owns this habit
    if not verify_habit_ownership(habit_id, current_user.id):
        flash('You do not have access to that habit.', 'error')
        return redirect(url_for('index'))

    delete_habit(habit_id)
    return redirect(url_for('index'))


@app.route('/reorder-habits', methods=['POST'])
@login_required
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

    # Verify all habits belong to current user
    for habit_id in habit_ids:
        if not verify_habit_ownership(habit_id, current_user.id):
            return jsonify({'error': 'Unauthorized'}), 403

    success = update_habit_order(habit_ids)

    if success:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Failed to update order'}), 500


if __name__ == '__main__':
    app.run(port=5001, debug=True)
