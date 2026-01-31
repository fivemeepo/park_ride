#!/usr/bin/env python3
"""
AI-powered insights generator for parking data analysis.

Uses an LLM to analyze parking trends and generate actionable insights.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from parkride.storage import ParkingDatabase

# Load .env file from project root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class InsightsGenerator:
    """Generates AI-powered insights from parking data."""

    # Default Ark API base URL (i18n region)
    DEFAULT_ARK_BASE_URL = "https://ark-ap-southeast.byteintl.net/api/v3"

    def __init__(self, db: ParkingDatabase, api_key: Optional[str] = None):
        """
        Initialize the insights generator.

        Configuration is loaded from .env file:
            ARK_API_KEY: ByteDance Ark API key
            ARK_MODEL_ID: Ark model/endpoint ID
            ANTHROPIC_API_KEY: Anthropic API key (fallback)

        Args:
            db: ParkingDatabase instance for data access
            api_key: Override for ANTHROPIC_API_KEY
        """
        self.db = db
        # Load from .env (already loaded at module level)
        self.ark_api_key = os.environ.get("ARK_API_KEY")
        self.ark_model = os.environ.get("ARK_MODEL_ID")
        self.ark_base_url = os.environ.get("ARK_BASE_URL", self.DEFAULT_ARK_BASE_URL)
        self.anthropic_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def prepare_data_summary(self, hours: int = 24, carpark: Optional[str] = None) -> dict:
        """
        Prepare a summary of parking data for analysis.

        Args:
            hours: Number of hours of data to analyze
            carpark: Specific carpark to analyze, or None for all carparks

        Returns:
            Dict containing aggregated stats per carpark
        """
        if carpark:
            carparks = [carpark]
        else:
            carparks = self.db.get_available_carparks()
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        summary = {
            "time_range": {
                "start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "hours": hours
            },
            "carpark_filter": carpark,
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

    def generate_insight(self, insight_type: str = "daily_summary", hours: int = 24, carpark: Optional[str] = None) -> dict:
        """
        Generate an insight using the LLM.

        Args:
            insight_type: Type of insight to generate
            hours: Hours of data to analyze
            carpark: Specific carpark to analyze, or None for all carparks

        Returns:
            Dict containing the generated insight
        """
        data_summary = self.prepare_data_summary(hours, carpark=carpark)

        if not data_summary["carparks"]:
            return {
                "insight_type": insight_type,
                "title": "No Data Available",
                "content": "There is no parking data available for the selected time range.",
                "data_range_start": data_summary["time_range"]["start"],
                "data_range_end": data_summary["time_range"]["end"],
                "metadata": {"hours": hours, "carpark_filter": carpark}
            }

        prompt = self._build_prompt(data_summary, insight_type)
        response, thinking = self._call_llm(prompt)

        # Parse the response
        title, content = self._parse_response(response)

        return {
            "insight_type": insight_type,
            "title": title,
            "content": content,
            "thinking": thinking,
            "data_range_start": data_summary["time_range"]["start"],
            "data_range_end": data_summary["time_range"]["end"],
            "metadata": {
                "hours": hours,
                "carparks_analyzed": len(data_summary["carparks"]),
                "carpark_filter": carpark,
                "model": self.ark_model if self.ark_api_key else "claude-sonnet-4-20250514"
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

        # Add context about which carparks are being analyzed
        carpark_filter = data_summary.get("carpark_filter")
        if carpark_filter:
            scope_text = f"Analysis Scope: Single carpark - {carpark_filter}"
        else:
            scope_text = f"Analysis Scope: All carparks ({len(data_summary['carparks'])} total)"

        return f"""Analyze the following parking data and provide insights.

Time Range: {time_range['start']} to {time_range['end']} ({time_range['hours']} hours)
{scope_text}

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

    def _call_llm(self, prompt: str) -> tuple[str, Optional[str]]:
        """Call LLM API to generate insights. Tries Ark first, then Anthropic.

        Returns:
            Tuple of (response_text, thinking_text). thinking_text may be None.
        """
        # Try ByteDance Ark (Doubao) first
        if self.ark_api_key:
            result = self._call_ark(prompt)
            if result[0]:
                return result

        # Fall back to Anthropic
        if self.anthropic_api_key:
            result = self._call_anthropic(prompt)
            if result[0]:
                return result

        return self._generate_fallback_response(), None

    def _call_ark(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        """Call ByteDance Ark API using OpenAI SDK.

        Returns:
            Tuple of (response_text, reasoning_text). reasoning_text may be None.
        """
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.ark_api_key,
                base_url=self.ark_base_url,
            )
            completion = client.chat.completions.create(
                model=self.ark_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
            )
            message = completion.choices[0].message
            response_text = message.content

            # Extract reasoning content if available
            reasoning_text = None
            if hasattr(message, 'reasoning_content') and message.reasoning_content:
                reasoning_text = message.reasoning_content

            return response_text, reasoning_text
        except ImportError:
            return None, None
        except Exception as e:
            return f"TITLE: Analysis Unavailable\nCONTENT: Unable to generate insights via Ark: {str(e)}", None

    def _call_anthropic(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        """Call Anthropic API with extended thinking enabled.

        Returns:
            Tuple of (response_text, thinking_text). thinking_text may be None.
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000
                },
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response and thinking from content blocks
            response_text = None
            thinking_text = None

            for block in message.content:
                if block.type == "thinking":
                    thinking_text = block.thinking
                elif block.type == "text":
                    response_text = block.text

            return response_text, thinking_text
        except ImportError:
            return None, None
        except Exception as e:
            return f"TITLE: Analysis Unavailable\nCONTENT: Unable to generate insights via Anthropic: {str(e)}", None

    def _generate_fallback_response(self) -> str:
        """Generate a basic response when no LLM is available."""
        return (
            "TITLE: Parking Data Summary\n"
            "CONTENT: AI-powered analysis is not available. "
            "Please set the ARK_API_KEY (for ByteDance Ark/Doubao) or ANTHROPIC_API_KEY environment variable to enable intelligent insights. "
            "The raw data has been collected and is ready for analysis once an API key is configured."
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
