#!/usr/bin/env python3
"""
Park&Ride Data Collector

Collects parking availability data from Transport NSW GraphQL API
and stores it in SQLite database.

Usage:
    python run_collector.py                        # Query Narrabeen once
    python run_collector.py --loop                 # Query continuously (60s interval)
    python run_collector.py --loop --chart         # With live chart
    python run_collector.py --carpark Narrabeen    # Specify car park
    python run_collector.py --all                  # Show all car parks
    python run_collector.py --visualize --hours 24 # View historical chart

First time setup:
    pip install -r requirements.txt
"""

import time
import argparse
import signal
import sys
import os
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parkride.storage import ParkingDatabase
from parkride.collector import (
    fetch_parking_data, fetch_with_retry, filter_carpark,
    display_availability, log, send_notification
)

DEFAULT_INTERVAL = 60  # seconds
DEFAULT_DB_PATH = "parking_data.db"

# Global flag for graceful shutdown
running = True


def check_and_notify(
    carpark_name: str,
    threshold: int = 1,
    notify: bool = True,
    db: Optional[ParkingDatabase] = None
) -> Optional[int]:
    """
    Check parking availability and send notification if spaces available.
    """
    data = fetch_with_retry()
    if data is None:
        return None

    if db:
        db.insert_readings(data)

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
            #send_notification("Parking Available!", message)

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
    """Run continuous monitoring loop."""
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

    chart = None
    if show_chart and carpark_name:
        try:
            from parkride.visualize import LiveChart
            import matplotlib
            matplotlib.use('TkAgg')
            import matplotlib.pyplot as plt

            chart = LiveChart(db, carpark_name, hours_to_show=2, update_interval=interval * 1000)
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

            if chart:
                try:
                    chart._update(iteration)
                    chart.fig.canvas.draw()
                    chart.fig.canvas.flush_events()
                except Exception:
                    pass

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
        from parkride.visualize import plot_availability, plot_daily_pattern

        if pattern:
            plot_daily_pattern(db, carpark, days=hours // 24 or 7, output=output)
        else:
            plot_availability(db, carpark, hours=hours, output=output)
    except ImportError as e:
        log(f"Visualization requires matplotlib: {e}")
        log("Install with: pip install matplotlib")


def main():
    parser = argparse.ArgumentParser(
        description="Park&Ride Data Collector - Fetch and store parking availability"
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

    db = ParkingDatabase(args.db)

    try:
        if args.visualize:
            show_visualization(db, args.carpark, args.hours, args.output, args.pattern)

        elif args.export:
            output_file = args.output or f"parking_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            db.export_to_csv(output_file, carpark=args.carpark, hours=args.hours)
            log(f"Data exported to {output_file}")

        elif args.loop:
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
