#!/usr/bin/env python3
"""
Run the Park&Ride Dashboard web server.

Usage:
    python run_dashboard.py                     # Run on localhost:5000
    python run_dashboard.py --port 8080         # Custom port
    python run_dashboard.py --host 0.0.0.0      # Allow external access
    python run_dashboard.py --debug             # Enable debug mode
"""

import argparse
import os
import sys

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard import create_app


def main():
    parser = argparse.ArgumentParser(description='Run Park&Ride Dashboard')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--db', default='parking_data.db',
                        help='Database file path (default: parking_data.db)')
    parser.add_argument('--config', default='dashboard_config.json',
                        help='Config file path (default: dashboard_config.json)')

    args = parser.parse_args()

    # Check if database exists
    if not os.path.exists(args.db):
        print(f"Warning: Database file '{args.db}' not found.")
        print("Run 'python parking_graphql.py' first to collect some data.")

    app = create_app({
        'db_path': args.db,
        'config_path': args.config
    })

    print(f"Starting Park&Ride Dashboard...")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Database: {args.db}")
    print(f"  Config: {args.config}")
    print()

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
