"""
REST API endpoints for the dashboard.
"""

import os
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from parkride.storage import ParkingDatabase
from parkride.insights import InsightsGenerator
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
        start: ISO format start datetime (optional, for custom range)
        end: ISO format end datetime (optional, for custom range)
    """
    carparks_param = request.args.get('carpark', '')
    carparks = [c.strip() for c in carparks_param.split(',') if c.strip()]
    hours = int(request.args.get('hours', 24))
    start = request.args.get('start')
    end = request.args.get('end')

    if not carparks:
        return jsonify({'error': 'No carparks specified'}), 400

    db = get_db()
    try:
        result = {}
        for carpark in carparks:
            if start and end:
                start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
                readings = db.get_readings(carpark=carpark, start_time=start_time, end_time=end_time)
            else:
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


@api_bp.route('/insights/latest')
def get_latest_insight():
    """Get the most recent insight."""
    db = get_db()
    try:
        insight = db.get_latest_insight()
        return jsonify({'insight': insight})
    finally:
        db.close()


@api_bp.route('/insights')
def get_insights():
    """
    Get paginated list of insights.

    Query params:
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip (default: 0)
    """
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))

    db = get_db()
    try:
        insights = db.get_insights(limit=limit, offset=offset)
        total = db.get_insights_count()
        return jsonify({
            'insights': insights,
            'total': total,
            'hasMore': offset + len(insights) < total
        })
    finally:
        db.close()


@api_bp.route('/insights/generate', methods=['POST'])
def generate_insight():
    """Generate a new insight using LLM."""
    data = request.get_json() or {}
    insight_type = data.get('type', 'daily_summary')
    hours = data.get('hours', 24)

    db = get_db()
    try:
        generator = InsightsGenerator(db, api_key=os.environ.get('ANTHROPIC_API_KEY'))
        insight = generator.generate_insight(insight_type, hours)
        insight_id = generator.save_insight(insight)

        return jsonify({'insight': insight, 'id': insight_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
