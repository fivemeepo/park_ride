#!/usr/bin/env python3
"""
SQLite storage module for parking availability data.

Provides persistent storage for historical parking readings with
efficient querying capabilities for analysis and visualization.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class ParkingDatabase:
    """SQLite database wrapper for parking availability data."""

    def __init__(self, db_path: str = "parking_data.db"):
        """
        Initialize database connection and create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._create_insights_table()

    def _create_tables(self):
        """Create database tables and indexes if they don't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS parking_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    carpark_name TEXT NOT NULL,
                    total_spots INTEGER NOT NULL,
                    occupancy INTEGER NOT NULL,
                    available INTEGER NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_carpark_timestamp
                ON parking_readings(carpark_name, timestamp)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON parking_readings(timestamp)
            """)

    def _create_insights_table(self):
        """Create insights table if it doesn't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME NOT NULL,
                    insight_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    data_range_start DATETIME,
                    data_range_end DATETIME,
                    metadata TEXT
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_insights_created_at
                ON insights(created_at DESC)
            """)

    def insert_readings(self, readings: list[dict]):
        """
        Bulk insert parking readings.

        Args:
            readings: List of dicts with keys: name, spots, occupancy, available, timestamp
        """
        if not readings:
            return

        with self.conn:
            self.conn.executemany(
                """INSERT INTO parking_readings
                   (timestamp, carpark_name, total_spots, occupancy, available)
                   VALUES (?, ?, ?, ?, ?)""",
                [(r["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r["timestamp"], 'strftime') else r["timestamp"],
                  r["name"], r["spots"], r["occupancy"], r["available"])
                 for r in readings]
            )

    def get_readings(
        self,
        carpark: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        hours: Optional[int] = None,
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Query parking readings with optional filters.

        Args:
            carpark: Filter by carpark name (partial match)
            start_time: Filter readings after this time
            end_time: Filter readings before this time
            hours: Shortcut to get last N hours of data
            limit: Maximum number of results

        Returns:
            List of reading dicts with timestamp, carpark_name, total_spots, occupancy, available
        """
        query = "SELECT * FROM parking_readings WHERE 1=1"
        params = []

        if carpark:
            query += " AND carpark_name LIKE ?"
            params.append(f"%{carpark}%")

        if hours:
            start_time = datetime.now() - timedelta(hours=hours)

        if start_time:
            query += " AND timestamp >= ?"
            # Use strftime for consistent format with SQLite storage
            params.append(start_time.strftime("%Y-%m-%d %H:%M:%S"))

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.strftime("%Y-%m-%d %H:%M:%S"))

        query += " ORDER BY timestamp ASC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_latest_reading(self, carpark: str) -> Optional[dict]:
        """Get the most recent reading for a carpark."""
        cursor = self.conn.execute(
            """SELECT * FROM parking_readings
               WHERE carpark_name LIKE ?
               ORDER BY timestamp DESC LIMIT 1""",
            (f"%{carpark}%",)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_available_carparks(self) -> list[str]:
        """Get list of all unique carpark names in the database."""
        cursor = self.conn.execute(
            "SELECT DISTINCT carpark_name FROM parking_readings ORDER BY carpark_name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_reading_count(self, carpark: Optional[str] = None) -> int:
        """Get total count of readings, optionally filtered by carpark."""
        if carpark:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM parking_readings WHERE carpark_name LIKE ?",
                (f"%{carpark}%",)
            )
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM parking_readings")
        return cursor.fetchone()[0]

    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Remove readings older than specified days.

        Args:
            days_to_keep: Number of days of data to retain
        """
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        with self.conn:
            self.conn.execute(
                "DELETE FROM parking_readings WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )

    def export_to_csv(self, output_path: str, carpark: Optional[str] = None, hours: Optional[int] = None):
        """
        Export readings to CSV file.

        Args:
            output_path: Path for output CSV file
            carpark: Filter by carpark name
            hours: Filter to last N hours
        """
        import csv

        readings = self.get_readings(carpark=carpark, hours=hours)

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'carpark_name', 'total_spots', 'occupancy', 'available'
            ])
            writer.writeheader()
            for r in readings:
                writer.writerow({
                    'timestamp': r['timestamp'],
                    'carpark_name': r['carpark_name'],
                    'total_spots': r['total_spots'],
                    'occupancy': r['occupancy'],
                    'available': r['available']
                })

    def insert_insight(self, insight: dict) -> int:
        """
        Insert a new insight into the database.

        Args:
            insight: Dict with keys: insight_type, title, content, data_range_start,
                     data_range_end, metadata (optional)

        Returns:
            The ID of the newly inserted insight
        """
        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO insights
                   (created_at, insight_type, title, content, data_range_start, data_range_end, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    insight["insight_type"],
                    insight["title"],
                    insight["content"],
                    insight.get("data_range_start"),
                    insight.get("data_range_end"),
                    json.dumps(insight.get("metadata")) if insight.get("metadata") else None
                )
            )
            return cursor.lastrowid

    def get_latest_insight(self) -> Optional[dict]:
        """Get the most recent insight."""
        cursor = self.conn.execute(
            """SELECT * FROM insights ORDER BY created_at DESC LIMIT 1"""
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            return result
        return None

    def get_insights(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """
        Get paginated list of insights.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of insight dicts
        """
        cursor = self.conn.execute(
            """SELECT * FROM insights ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            results.append(result)
        return results

    def get_insights_count(self) -> int:
        """Get total count of insights."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM insights")
        return cursor.fetchone()[0]

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
