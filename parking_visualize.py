#!/usr/bin/env python3
"""
Visualization module for parking availability data.

Provides live-updating charts and static historical analysis plots.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
from typing import Optional, Callable
import threading

from parking_storage import ParkingDatabase


class LiveChart:
    """Auto-refreshing matplotlib chart for real-time parking availability."""

    def __init__(
        self,
        db: ParkingDatabase,
        carpark: str,
        hours_to_show: int = 2,
        update_interval: int = 15000  # milliseconds
    ):
        """
        Initialize live chart.

        Args:
            db: ParkingDatabase instance
            carpark: Carpark name to track
            hours_to_show: Number of hours of data to display
            update_interval: Chart refresh interval in milliseconds
        """
        self.db = db
        self.carpark = carpark
        self.hours_to_show = hours_to_show
        self.update_interval = update_interval

        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.line, = self.ax.plot([], [], linewidth=2, color='#2196F3', marker='o', markersize=3)
        self.fill = None

        self._setup_axes()
        self.ani = None

    def _setup_axes(self):
        """Configure chart axes and styling."""
        self.ax.set_xlabel('Time', fontsize=11)
        self.ax.set_ylabel('Available Spots', fontsize=11)
        self.ax.set_title(f'{self.carpark} - Parking Availability (Live)', fontsize=13, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.tight_layout()

    def _update(self, frame):
        """Update chart with latest data."""
        readings = self.db.get_readings(carpark=self.carpark, hours=self.hours_to_show)

        if not readings:
            return self.line,

        times = [datetime.fromisoformat(r['timestamp']) if isinstance(r['timestamp'], str)
                 else r['timestamp'] for r in readings]
        available = [r['available'] for r in readings]

        self.line.set_data(times, available)

        # Update fill
        if self.fill:
            self.fill.remove()
        self.fill = self.ax.fill_between(times, available, alpha=0.2, color='#2196F3')

        # Adjust axes
        if times:
            self.ax.set_xlim(min(times) - timedelta(minutes=5), max(times) + timedelta(minutes=5))
            y_min = max(0, min(available) - 5)
            y_max = max(available) + 5
            self.ax.set_ylim(y_min, y_max)

        # Update title with latest value
        if available:
            self.ax.set_title(
                f'{self.carpark} - Available: {available[-1]} spots (Live)',
                fontsize=13, fontweight='bold'
            )

        self.fig.canvas.draw_idle()
        return self.line,

    def start(self):
        """Start the live chart animation."""
        self.ani = FuncAnimation(
            self.fig,
            self._update,
            interval=self.update_interval,
            blit=False,
            cache_frame_data=False
        )
        plt.show()

    def stop(self):
        """Stop the animation."""
        if self.ani:
            self.ani.event_source.stop()


def plot_availability(
    db: ParkingDatabase,
    carpark: str,
    hours: int = 24,
    output: Optional[str] = None,
    show: bool = True
):
    """
    Generate static line chart of parking availability.

    Args:
        db: ParkingDatabase instance
        carpark: Carpark name
        hours: Number of hours of data to display
        output: Optional file path to save chart
        show: Whether to display the chart
    """
    readings = db.get_readings(carpark=carpark, hours=hours)

    if not readings:
        print(f"No data found for {carpark} in the last {hours} hours")
        return

    times = [datetime.fromisoformat(r['timestamp']) if isinstance(r['timestamp'], str)
             else r['timestamp'] for r in readings]
    available = [r['available'] for r in readings]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(times, available, linewidth=1.5, color='#2196F3', marker='o', markersize=2)
    ax.fill_between(times, available, alpha=0.2, color='#2196F3')

    ax.set_xlabel('Time', fontsize=11)
    ax.set_ylabel('Available Spots', fontsize=11)
    ax.set_title(f'{carpark} - Parking Availability (Last {hours} hours)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Format x-axis based on time range
    if hours <= 6:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif hours <= 48:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)

    # Add statistics
    if available:
        stats_text = f"Min: {min(available)}  Max: {max(available)}  Avg: {sum(available)//len(available)}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, bbox_inches='tight')
        print(f"Chart saved to {output}")

    if show:
        plt.show()

    plt.close()


def plot_daily_pattern(
    db: ParkingDatabase,
    carpark: str,
    days: int = 7,
    output: Optional[str] = None,
    show: bool = True
):
    """
    Plot overlaid daily patterns to identify typical usage.

    Args:
        db: ParkingDatabase instance
        carpark: Carpark name
        days: Number of days to include
        output: Optional file path to save chart
        show: Whether to display the chart
    """
    readings = db.get_readings(carpark=carpark, hours=days * 24)

    if not readings:
        print(f"No data found for {carpark}")
        return

    # Group by date
    daily_data = {}
    for r in readings:
        ts = datetime.fromisoformat(r['timestamp']) if isinstance(r['timestamp'], str) else r['timestamp']
        date_key = ts.strftime('%Y-%m-%d')
        time_of_day = ts.hour + ts.minute / 60

        if date_key not in daily_data:
            daily_data[date_key] = {'times': [], 'available': []}
        daily_data[date_key]['times'].append(time_of_day)
        daily_data[date_key]['available'].append(r['available'])

    if not daily_data:
        print("No daily data to plot")
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    colors = plt.cm.viridis(range(0, 256, 256 // max(len(daily_data), 1)))

    for i, (date, data) in enumerate(sorted(daily_data.items())):
        ax.plot(data['times'], data['available'],
                linewidth=1, alpha=0.7, color=colors[i % len(colors)], label=date)

    ax.set_xlabel('Hour of Day', fontsize=11)
    ax.set_ylabel('Available Spots', fontsize=11)
    ax.set_title(f'{carpark} - Daily Patterns (Last {days} days)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.legend(loc='upper right', fontsize=8)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, bbox_inches='tight')
        print(f"Chart saved to {output}")

    if show:
        plt.show()

    plt.close()


def plot_comparison(
    db: ParkingDatabase,
    carparks: list[str],
    hours: int = 24,
    output: Optional[str] = None,
    show: bool = True
):
    """
    Compare multiple carparks on the same chart.

    Args:
        db: ParkingDatabase instance
        carparks: List of carpark names to compare
        hours: Number of hours of data to display
        output: Optional file path to save chart
        show: Whether to display the chart
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    colors = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0']

    for i, carpark in enumerate(carparks):
        readings = db.get_readings(carpark=carpark, hours=hours)
        if readings:
            times = [datetime.fromisoformat(r['timestamp']) if isinstance(r['timestamp'], str)
                     else r['timestamp'] for r in readings]
            available = [r['available'] for r in readings]
            ax.plot(times, available, linewidth=1.5, color=colors[i % len(colors)],
                    label=readings[0]['carpark_name'])

    ax.set_xlabel('Time', fontsize=11)
    ax.set_ylabel('Available Spots', fontsize=11)
    ax.set_title(f'Parking Availability Comparison (Last {hours} hours)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, bbox_inches='tight')
        print(f"Chart saved to {output}")

    if show:
        plt.show()

    plt.close()
