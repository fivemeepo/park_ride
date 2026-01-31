"""
Park&Ride Dashboard - Flask Web Application

A web dashboard for visualizing parking availability data.
"""

from flask import Flask
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env in the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars


def create_app(config=None):
    """Application factory for Flask app."""
    app = Flask(__name__)

    # Default configuration
    app.config['DB_PATH'] = 'parking_data.db'
    app.config['CONFIG_PATH'] = 'dashboard_config.json'

    # Override with provided config
    if config:
        app.config['DB_PATH'] = config.get('db_path', app.config['DB_PATH'])
        app.config['CONFIG_PATH'] = config.get('config_path', app.config['CONFIG_PATH'])

    # Register blueprints
    from dashboard.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register main routes
    from dashboard.app import main_bp
    app.register_blueprint(main_bp)

    return app
