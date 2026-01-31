"""
Main routes for the dashboard.
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')
