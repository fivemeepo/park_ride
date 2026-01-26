#!/usr/bin/env python3
"""
Transport NSW Park&Ride Parking Availability Checker

This script uses Playwright to query the Transport NSW website for real-time
parking availability at Park&Ride car parks.

Usage:
    python3 parking_query.py                    # Query Narrabeen once
    python3 parking_query.py --loop             # Query continuously
    python3 parking_query.py --carpark Narrabeen  # Specify car park
    python3 parking_query.py --all              # Show all car parks

First time setup:
    pip install playwright
    playwright install chromium
"""

import time
import argparse
import os
import re
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Please install playwright: pip install playwright && playwright install chromium")
    exit(1)

# URL for Park&Ride page
PARKRIDE_URL = "https://transportnsw.info/travel-info/ways-to-get-around/drive/parking/transport-parkride-car-parks"


def log(message: str):
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def send_notification(title: str, message: str):
    """Send macOS system notification."""
    os.system(f"""osascript -e 'display notification "{message}" with title "{title}"'""")


def get_parking_availability(playwright_browser=None, carpark_name: str = None) -> dict:
    """
    Fetch parking availability from Transport NSW website using Playwright.

    Args:
        playwright_browser: Optional existing browser instance
        carpark_name: Optional name of specific car park to filter (e.g., "Narrabeen")

    Returns:
        Dictionary with car park names as keys and availability info as values
    """
    carparks = {}

    def extract_from_page(page):
        # Wait for the car park list to load
        page.wait_for_selector("button:has-text('Park&Ride -')", timeout=30000)

        # Get all car park buttons
        buttons = page.query_selector_all("button")

        for button in buttons:
            try:
                text = button.inner_text()
                if "Park&Ride -" in text:
                    # Parse: "Park&Ride - Narrabeen\n21 spaces" or "Park&Ride - Cherrybrook\nFULL"
                    lines = text.strip().split('\n')
                    if len(lines) >= 2:
                        name = lines[0].replace("Park&Ride -", "").strip()
                        availability = lines[1].strip()

                        # Parse number of spaces
                        if "spaces" in availability:
                            match = re.search(r'(\d+)', availability)
                            spaces = int(match.group(1)) if match else -1
                        elif availability == "FULL":
                            spaces = 0
                        else:
                            spaces = -1  # Unavailable

                        carparks[name] = {
                            "name": name,
                            "availability": availability,
                            "spaces": spaces
                        }
            except Exception:
                continue

    try:
        if playwright_browser:
            page = playwright_browser.new_page()
            page.goto(PARKRIDE_URL, timeout=60000)
            extract_from_page(page)
            page.close()
        else:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(PARKRIDE_URL, timeout=60000)
                extract_from_page(page)
                browser.close()

        # Filter by specific car park if requested
        if carpark_name:
            filtered = {k: v for k, v in carparks.items()
                       if carpark_name.lower() in k.lower()}
            return filtered

        return carparks

    except Exception as e:
        log(f"Error fetching parking data: {e}")
        return {}


def display_availability(carparks: dict):
    """Display parking availability in a formatted way."""
    if not carparks:
        log("No car parks found.")
        return

    print("=" * 50)
    print("Park&Ride Parking Availability")
    print("=" * 50)

    for name, info in sorted(carparks.items()):
        spaces = info["spaces"]
        if spaces == 0:
            status = "FULL"
        elif spaces < 0:
            status = "Unavailable"
        elif spaces < 20:
            status = f"{spaces} spaces (low)"
        else:
            status = f"{spaces} spaces"

        print(f"  {name}: {status}")

    print("=" * 50)


def check_and_notify(carpark_name: str, threshold: int = 1, notify: bool = True, browser=None):
    """
    Check parking availability and send notification if spaces available.

    Args:
        carpark_name: Name of car park to check
        threshold: Minimum spaces to trigger notification
        notify: Whether to send system notification
        browser: Optional playwright browser instance for reuse
    """
    carparks = get_parking_availability(browser, carpark_name)

    if not carparks:
        log(f"Could not find car park: {carpark_name}")
        return None

    for name, info in carparks.items():
        spaces = info["spaces"]
        log(f"{name}: {info['availability']}")

        if notify and spaces >= threshold:
            message = f"{name} has {spaces} available spaces!"
            log(f">>> {message}")
            try:
                send_notification("Parking Available!", message)
            except Exception as e:
                log(f"Notification error: {e}")

        return spaces

    return None


def main():
    parser = argparse.ArgumentParser(description="Check Park&Ride parking availability")
    parser.add_argument("--carpark", "-c", type=str, default="Narrabeen",
                       help="Car park name to check (default: Narrabeen)")
    parser.add_argument("--loop", "-l", action="store_true",
                       help="Run continuously with 30-second interval")
    parser.add_argument("--interval", "-i", type=int, default=30,
                       help="Polling interval in seconds (default: 30)")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Show all car parks")
    parser.add_argument("--threshold", "-t", type=int, default=1,
                       help="Minimum spaces to trigger notification (default: 1)")
    parser.add_argument("--no-notify", action="store_true",
                       help="Disable system notifications")

    args = parser.parse_args()

    log("Checking parking availability...")

    if args.loop:
        log(f"Running in loop mode (interval: {args.interval}s)")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                while True:
                    try:
                        if args.all:
                            carparks = get_parking_availability(browser)
                            display_availability(carparks)
                        else:
                            check_and_notify(args.carpark, args.threshold, not args.no_notify, browser)

                        time.sleep(args.interval)
                    except KeyboardInterrupt:
                        log("Stopped by user.")
                        break
                    except Exception as e:
                        log(f"Error: {e}")
                        time.sleep(args.interval)
            finally:
                browser.close()
    else:
        if args.all:
            carparks = get_parking_availability()
            display_availability(carparks)
        else:
            check_and_notify(args.carpark, args.threshold, not args.no_notify)


if __name__ == "__main__":
    main()
