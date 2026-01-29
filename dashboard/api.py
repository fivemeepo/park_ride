"""
REST API endpoints for the dashboard.
"""

from flask import Blueprint, jsonify, request, current_app
from parkride.storage import ParkingDatabase
from dashboard.config import DashboardConfig

api_bp = Blueprint('api', __name__)


def get_db():
    """Get database instance."""
    return ParkingDatabase(current_app.config['DB_PATH'])


def get_config():
    """Get config instance."""
    return DashboardConfig(current_app.config['CONFIG_PATH'])


@api_bp.route('/carparks')
def get_carparks():
    """List all available carparks."""
    db = get_db()
    try:
        carparks = db.get_available_carparks()
        return jsonify({'carparks': carparks})
    finally:
        db.close()


@api_bp.route('/readings')
def get_readings():
    """
    Get historical readings for specified carparks.

    Query params:
        carpark: Comma-separated list of carpark names
        hours: Number of hours of history (default: 24)
    """
    carparks_param = request.args.get('carpark', '')
    carparks = [c.strip() for c in carparks_param.split(',') if c.strip()]
    hours = int(request.args.get('hours', 24))

    if not carparks:
        return jsonify({'error': 'No carparks specified'}), 400

    db = get_db()
    try:
        result = {}
        for carpark in carparks:
            readings = db.get_readings(carpark=carpark, hours=hours)
            result[carpark] = [
                {
                    'timestamp': r['timestamp'],
                    'available': r['available'],
                    'total_spots': r['total_spots'],
                    'occupancy': r['occupancy']
                }
                for r in readings
            ]
        return jsonify({'readings': result})
    finally:
        db.close()


@api_bp.route('/latest')
def get_latest():
    """
    Get latest reading for specified carparks.

    Query params:
        carpark: Comma-separated list of carpark names
    """
    carparks_param = request.args.get('carpark', '')
    carparks = [c.strip() for c in carparks_param.split(',') if c.strip()]

    if not carparks:
        return jsonify({'error': 'No carparks specified'}), 400

    db = get_db()
    try:
        result = {}
        for carpark in carparks:
            reading = db.get_latest_reading(carpark)
            if reading:
                result[carpark] = {
                    'timestamp': reading['timestamp'],
                    'available': reading['available'],
                    'total_spots': reading['total_spots'],
                    'occupancy': reading['occupancy']
                }
        return jsonify({'latest': result})
    finally:
        db.close()


@api_bp.route('/config', methods=['GET'])
def get_dashboard_config():
    """Get dashboard configuration."""
    config = get_config()
    return jsonify(config.load())


@api_bp.route('/config', methods=['POST'])
def save_dashboard_config():
    """Save dashboard configuration."""
    config = get_config()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if config.save(data):
        return jsonify({'success': True, 'message': 'Configuration saved'})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500
