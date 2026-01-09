"""
Century Tracker - Flask application entry point.
Minimal setup for V1, ready for future UI routes.
"""
from flask import Flask
from database import init_db


app = Flask(__name__)


# Initialize database on startup
with app.app_context():
    init_db()


@app.route('/')
def index():
    """Basic endpoint to confirm API is running."""
    return "Century Tracker API - Ready"


if __name__ == '__main__':
    app.run(debug=True)
