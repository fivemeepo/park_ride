#!/usr/bin/env python3
"""
AI-powered insights generator for parking data analysis.

Uses an LLM to analyze parking trends and generate actionable insights.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from parkride.storage import ParkingDatabase


class InsightsGenerator:
    """Generates AI-powered insights from parking data."""

    def __init__(self, db: ParkingDatabase, api_key: Optional[str] = None):
        """
        Initialize the insights generator.

        Args:
            db: ParkingDatabase instance for data access
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.db = db
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def prepare_data_summary(self, hours: int = 24) -> dict:
        """
        Prepare a summary of parking data for analysis.

        Args:
            hours: Number of hours of data to analyze

        Returns:
            Dict containing aggregated stats per carpark
        """
        carparks = self.db.get_available_carparks()
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        summary = {
            "time_range": {
                "start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "hours": hours
            },
            "carparks": {}
        }

        for carpark in carparks:
            readings = self.db.get_readings(carpark=carpark, hours=hours)
            if not readings:
                continue

            available_spots = [r["available"] for r in readings]
            total_spots = readings[0]["total_spots"] if readings else 0
            occupancies = [r["occupancy"] for r in readings]

            # Calculate occupancy rates
            occupancy_rates = []
            for r in readings:
                if r["total_spots"] > 0:
                    rate = (r["occupancy"] / r["total_spots"]) * 100
                    occupancy_rates.append(rate)

            # Find peak occupancy time
            peak_idx = occupancies.index(max(occupancies)) if occupancies else 0
            peak_time = readings[peak_idx]["timestamp"] if readings else None

            summary["carparks"][carpark] = {
                "total_spots": total_spots,
                "readings_count": len(readings),
                "available": {
                    "min": min(available_spots) if available_spots else 0,
                    "max": max(available_spots) if available_spots else 0,
                    "avg": round(sum(available_spots) / len(available_spots), 1) if available_spots else 0
                },
                "occupancy_rate": {
                    "min": round(min(occupancy_rates), 1) if occupancy_rates else 0,
                    "max": round(max(occupancy_rates), 1) if occupancy_rates else 0,
                    "avg": round(sum(occupancy_rates) / len(occupancy_rates), 1) if occupancy_rates else 0
                },
                "peak_occupancy_time": peak_time
            }

        return summary

    def generate_insight(self, insight_type: str = "daily_summary", hours: int = 24) -> dict:
        """
        Generate an insight using the LLM.

        Args:
            insight_type: Type of insight to generate
            hours: Hours of data to analyze

        Returns:
            Dict containing the generated insight
        """
        data_summary = self.prepare_data_summary(hours)

        if not data_summary["carparks"]:
            return {
                "insight_type": insight_type,
                "title": "No Data Available",
                "content": "There is no parking data available for the selected time range.",
                "data_range_start": data_summary["time_range"]["start"],
                "data_range_end": data_summary["time_range"]["end"],
                "metadata": {"hours": hours}
            }

        prompt = self._build_prompt(data_summary, insight_type)
        response = self._call_llm(prompt)

        # Parse the response
        title, content = self._parse_response(response)

        return {
            "insight_type": insight_type,
            "title": title,
            "content": content,
            "data_range_start": data_summary["time_range"]["start"],
            "data_range_end": data_summary["time_range"]["end"],
            "metadata": {
                "hours": hours,
                "carparks_analyzed": len(data_summary["carparks"])
            }
        }

    def _build_prompt(self, data_summary: dict, insight_type: str) -> str:
        """Build the prompt for the LLM."""
        carpark_details = []
        for name, stats in data_summary["carparks"].items():
            carpark_details.append(
                f"- {name}: {stats['total_spots']} total spots, "
                f"avg {stats['occupancy_rate']['avg']}% occupied "
                f"(range: {stats['occupancy_rate']['min']}%-{stats['occupancy_rate']['max']}%), "
                f"peak at {stats['peak_occupancy_time']}"
            )

        carpark_text = "\n".join(carpark_details)
        time_range = data_summary["time_range"]

        return f"""Analyze the following parking data and provide insights.

Time Range: {time_range['start']} to {time_range['end']} ({time_range['hours']} hours)

Carpark Statistics:
{carpark_text}

Please provide:
1. A short title (max 10 words) summarizing the key finding
2. A 2-3 paragraph analysis covering:
   - Overall parking trends and patterns
   - Which carparks are busiest/quietest
   - Best times to find parking
   - Any notable observations

Format your response as:
TITLE: [Your title here]
CONTENT: [Your analysis here]"""

    def _call_llm(self, prompt: str) -> str:
        """Call the Anthropic API to generate insights."""
        if not self.api_key:
            return self._generate_fallback_response(prompt)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except ImportError:
            return self._generate_fallback_response(prompt)
        except Exception as e:
            return f"TITLE: Analysis Unavailable\nCONTENT: Unable to generate insights due to an error: {str(e)}"

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a basic response when LLM is not available."""
        return (
            "TITLE: Parking Data Summary\n"
            "CONTENT: AI-powered analysis is not available. "
            "Please set the ANTHROPIC_API_KEY environment variable to enable intelligent insights. "
            "The raw data has been collected and is ready for analysis once the API key is configured."
        )

    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse the LLM response into title and content."""
        title = "Parking Insights"
        content = response

        if "TITLE:" in response and "CONTENT:" in response:
            parts = response.split("CONTENT:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            content_part = parts[1].strip() if len(parts) > 1 else ""

            if title_part:
                title = title_part
            if content_part:
                content = content_part

        return title, content

    def save_insight(self, insight: dict) -> int:
        """
        Save an insight to the database.

        Args:
            insight: The insight dict to save

        Returns:
            The ID of the saved insight
        """
        return self.db.insert_insight(insight)
