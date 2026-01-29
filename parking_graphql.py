#!/usr/bin/env python3
"""
Transport NSW Park&Ride Parking Availability Checker (GraphQL Version)

This script uses the Transport NSW GraphQL API to query real-time
parking availability at Park&Ride car parks. Much faster and lighter
than the Playwright-based approach.

Usage:
    python3 parking_graphql.py                           # Query Narrabeen once
    python3 parking_graphql.py --loop                    # Query continuously (15s interval)
    python3 parking_graphql.py --loop --chart            # With live chart
    python3 parking_graphql.py --carpark Narrabeen       # Specify car park
    python3 parking_graphql.py --all                     # Show all car parks
    python3 parking_graphql.py --visualize --hours 24    # View historical chart

First time setup:
    pip install requests matplotlib pandas
"""

import time
import argparse
import os
import signal
import sys
from datetime import datetime
from typing import Optional

import requests

from parking_storage import ParkingDatabase

# GraphQL API configuration
GRAPHQL_ENDPOINT = "https://transportnsw.info/api/graphql"
GRAPHQL_QUERY = """query getLocations {
    result: widgets {
        pnrLocations {
            name
            spots
            occupancy
        }
    }
}"""

DEFAULT_INTERVAL = 15  # seconds
DEFAULT_DB_PATH = "parking_data.db"

# Global flag for graceful shutdown
running = True


def log(message: str):
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def send_notification(title: str, message: str):
    """Send macOS system notification."""
    try:
        os.system(f"""osascript -e 'display notification "{message}" with title "{title}"'""")
    except Exception:
        pass  # Silently fail on non-macOS systems


def fetch_parking_data(timeout: int = 30) -> list[dict]:
    """
    Fetch parking data from Transport NSW GraphQL API.

    Args:
        timeout: Request timeout in seconds

    Returns:
        List of dicts with keys: name, spots, occupancy, available, timestamp
    """
    payload = {
        "operationName": "getLocations",
        "query": GRAPHQL_QUERY,
        "variables": {}
    }

    response = requests.post(
        GRAPHQL_ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout
    )
    response.raise_for_status()

    data = response.json()
    locations = data["data"]["result"]["pnrLocations"]
    timestamp = datetime.now()

    return [
        {
            "name": loc["name"].replace("Park&Ride - ", ""),
            "spots": loc["spots"],
            "occupancy": loc["occupancy"],
            "available": loc["spots"] - loc["occupancy"],
            "timestamp": timestamp
        }
        for loc in locations
    ]


def fetch_with_retry(max_retries: int = 3) -> Optional[list[dict]]:
    """
    Fetch parking data with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        List of parking data dicts, or None if all retries fail
    """
    retry_delays = [5, 15, 30]

    for attempt in range(max_retries):
        try:
            return fetch_parking_data()
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                log(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                log(f"All {max_retries} attempts failed: {e}")
                return None


def filter_carpark(data: list[dict], carpark_name: str) -> list[dict]:
    """Filter parking data by carpark name (partial match)."""
    return [d for d in data if carpark_name.lower() in d["name"].lower()]


def display_availability(data: list[dict]):
    """Display parking availability in a formatted way."""
    if not data:
        log("No car parks found.")
        return

    print("=" * 50)
    print("Park&Ride Parking Availability")
    print("=" * 50)

    for item in sorted(data, key=lambda x: x["name"]):
        spaces = item["available"]
        if spaces == 0:
            status = "FULL"
        elif spaces < 0:
            status = "Unavailable"
        elif spaces < 20:
            status = f"{spaces} spaces (low)"
        else:
            status = f"{spaces} spaces"

        print(f"  {item['name']}: {status}")

    print("=" * 50)


def check_and_notify(
    carpark_name: str,
    threshold: int = 1,
    notify: bool = True,
    db: Optional[ParkingDatabase] = None
) -> Optional[int]:
    """
    Check parking availability and send notification if spaces available.

    Args:
        carpark_name: Name of car park to check
        threshold: Minimum spaces to trigger notification
        notify: Whether to send system notification
        db: Optional database for storing reading

    Returns:
        Number of available spaces, or None if not found
    """
    data = fetch_with_retry()
    if data is None:
        return None

    # Store all readings if database provided
    if db:
        db.insert_readings(data)

    # Filter to specific carpark
    filtered = filter_carpark(data, carpark_name)

    if not filtered:
        log(f"Could not find car park: {carpark_name}")
        return None

    for item in filtered:
        spaces = item["available"]
        log(f"{item['name']}: {spaces} available (total: {item['spots']}, occupied: {item['occupancy']})")

        if notify and spaces >= threshold:
            message = f"{item['name']} has {spaces} available spaces!"
            log(f">>> {message}")
            send_notification("Parking Available!", message)

        return spaces

    return None


def run_continuous_monitor(
    carpark_name: Optional[str],
    interval: int,
    threshold: int,
    notify: bool,
    show_all: bool,
    db: ParkingDatabase,
    show_chart: bool = False
):
    """
    Run continuous monitoring loop.

    Args:
        carpark_name: Carpark to monitor (or None for all)
        interval: Polling interval in seconds
        threshold: Notification threshold
        notify: Whether to send notifications
        show_all: Whether to display all carparks
        db: Database for storing readings
        show_chart: Whether to show live chart
    """
    global running

    def signal_handler(sig, frame):
        global running
        log("Shutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log(f"Starting continuous monitoring (interval: {interval}s)")
    if carpark_name:
        log(f"Tracking: {carpark_name}")
    else:
        log("Tracking: All carparks")

    # Start live chart if requested
    chart = None
    if show_chart and carpark_name:
        try:
            from parking_visualize import LiveChart
            import matplotlib
            matplotlib.use('TkAgg')  # Use interactive backend
            import matplotlib.pyplot as plt

            chart = LiveChart(db, carpark_name, hours_to_show=2, update_interval=interval * 1000)

            # Run chart in non-blocking mode
            plt.ion()
            chart.fig.show()
        except Exception as e:
            log(f"Could not start live chart: {e}")
            chart = None

    iteration = 0
    while running:
        try:
            iteration += 1

            if show_all:
                data = fetch_with_retry()
                if data:
                    db.insert_readings(data)
                    display_availability(data)
            else:
                check_and_notify(carpark_name, threshold, notify, db)

            # Update chart
            if chart:
                try:
                    chart._update(iteration)
                    chart.fig.canvas.draw()
                    chart.fig.canvas.flush_events()
                except Exception:
                    pass

            # Sleep in small increments for responsive shutdown
            for _ in range(interval * 10):
                if not running:
                    break
                time.sleep(0.1)

        except Exception as e:
            log(f"Error: {e}")
            time.sleep(interval)

    log("Monitoring stopped.")
    log(f"Total readings stored: {db.get_reading_count()}")


def show_visualization(
    db: ParkingDatabase,
    carpark: str,
    hours: int,
    output: Optional[str],
    pattern: bool = False
):
    """Show historical visualization."""
    try:
        from parking_visualize import plot_availability, plot_daily_pattern

        if pattern:
            plot_daily_pattern(db, carpark, days=hours // 24 or 7, output=output)
        else:
            plot_availability(db, carpark, hours=hours, output=output)
    except ImportError as e:
        log(f"Visualization requires matplotlib: {e}")
        log("Install with: pip install matplotlib")


def main():
    parser = argparse.ArgumentParser(
        description="Check Park&Ride parking availability (GraphQL version)"
    )
    parser.add_argument(
        "--carpark", "-c", type=str, default="Narrabeen",
        help="Car park name to check (default: Narrabeen)"
    )
    parser.add_argument(
        "--loop", "-l", action="store_true",
        help="Run continuously with specified interval"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=DEFAULT_INTERVAL,
        help=f"Polling interval in seconds (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--all", "-a", action="store_true",
        help="Show all car parks"
    )
    parser.add_argument(
        "--threshold", "-t", type=int, default=1,
        help="Minimum spaces to trigger notification (default: 1)"
    )
    parser.add_argument(
        "--no-notify", action="store_true",
        help="Disable system notifications"
    )
    parser.add_argument(
        "--chart", action="store_true",
        help="Show live chart (requires --loop)"
    )
    parser.add_argument(
        "--visualize", "-v", action="store_true",
        help="Show historical chart from stored data"
    )
    parser.add_argument(
        "--hours", type=int, default=24,
        help="Hours of data to visualize (default: 24)"
    )
    parser.add_argument(
        "--pattern", action="store_true",
        help="Show daily pattern overlay chart"
    )
    parser.add_argument(
        "--export", "-e", action="store_true",
        help="Export data to CSV"
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Output file for visualization or export"
    )
    parser.add_argument(
        "--db", type=str, default=DEFAULT_DB_PATH,
        help=f"Database file path (default: {DEFAULT_DB_PATH})"
    )

    args = parser.parse_args()

    # Initialize database
    db = ParkingDatabase(args.db)

    try:
        if args.visualize:
            # Show historical visualization
            show_visualization(db, args.carpark, args.hours, args.output, args.pattern)

        elif args.export:
            # Export to CSV
            output_file = args.output or f"parking_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            db.export_to_csv(output_file, carpark=args.carpark, hours=args.hours)
            log(f"Data exported to {output_file}")

        elif args.loop:
            # Continuous monitoring
            run_continuous_monitor(
                carpark_name=None if args.all else args.carpark,
                interval=args.interval,
                threshold=args.threshold,
                notify=not args.no_notify,
                show_all=args.all,
                db=db,
                show_chart=args.chart
            )

        else:
            # Single query
            log("Checking parking availability...")
            if args.all:
                data = fetch_with_retry()
                if data:
                    db.insert_readings(data)
                    display_availability(data)
            else:
                check_and_notify(args.carpark, args.threshold, not args.no_notify, db)

    finally:
        db.close()


if __name__ == "__main__":
    main()
