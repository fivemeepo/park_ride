#!/usr/bin/env python3
"""
GraphQL data collector for Transport NSW Park&Ride parking availability.

This module fetches real-time parking data from the Transport NSW GraphQL API.
"""

import time
import os
from datetime import datetime
from typing import Optional

import requests

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
