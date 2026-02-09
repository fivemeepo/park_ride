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
from dataclasses import dataclass, field
from collections import defaultdict

# Load .env file from project root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

# Day names for display
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class DayPattern:
    """Statistics for a single day of the week."""
    day_of_week: int  # 0=Monday, 6=Sunday
    day_name: str
    readings_count: int
    avg_occupancy_rate: float  # 0.0-1.0
    peak_time: Optional[str]  # HH:MM format
    rush_start: Optional[str] = None  # Morning rush start
    rush_end: Optional[str] = None  # Morning rush end
    evening_rush_start: Optional[str] = None
    evening_rush_end: Optional[str] = None
    last_safe_arrival: Optional[str] = None  # Time before 90% full
    fill_time_variance: float = 0.0  # Variance in fill times (minutes)


@dataclass
class DataQuality:
    """Data sufficiency indicators."""
    total_days: int
    min_days_per_weekday: int
    confidence: str  # "high", "moderate", "limited", "very limited"
    gaps: list = field(default_factory=list)


@dataclass
class OverallPattern:
    """Cross-day aggregated patterns."""
    busiest_day: str
    quietest_day: str
    typical_work_hours: str
    weekday_avg_occupancy: float
    weekend_avg_occupancy: float


@dataclass
class DayOfWeekSummary:
    """Complete day-of-week analysis for a carpark."""
    carpark: str
    day_patterns: dict  # Keyed by day_of_week (0-6)
    overall: Optional[OverallPattern]
    data_quality: DataQuality


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

    def prepare_day_of_week_summary(self, hours: int = 168, carpark: Optional[str] = None) -> Optional[DayOfWeekSummary]:
        """
        Prepare day-of-week aggregated analysis for commuter insights.

        Args:
            hours: Number of hours of data to analyze (default 168 = 7 days)
            carpark: Specific carpark to analyze (required for commuter insights)

        Returns:
            DayOfWeekSummary with per-day patterns and data quality metrics
        """
        if not carpark:
            return None

        readings = self.db.get_readings(carpark=carpark, hours=hours)
        if not readings:
            # Return minimal structure with very limited confidence
            return DayOfWeekSummary(
                carpark=carpark,
                day_patterns={},
                overall=None,
                data_quality=DataQuality(
                    total_days=0,
                    min_days_per_weekday=0,
                    confidence="very limited",
                    gaps=["No data available"]
                )
            )

        # Group readings by day of week
        readings_by_day = defaultdict(list)
        distinct_dates = set()

        for r in readings:
            ts = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
            day_of_week = ts.weekday()  # 0=Monday, 6=Sunday
            readings_by_day[day_of_week].append({
                **r,
                "datetime": ts,
                "time": ts.strftime("%H:%M"),
                "date": ts.date()
            })
            distinct_dates.add(ts.date())

        # Calculate data quality
        data_quality = self._calculate_data_quality(readings_by_day, distinct_dates)

        # Build day patterns
        day_patterns = {}
        total_spots = readings[0]["total_spots"] if readings else 0

        for day_num in range(7):
            day_readings = readings_by_day.get(day_num, [])
            if not day_readings:
                continue

            # Calculate average occupancy rate
            occupancy_rates = []
            for r in day_readings:
                if total_spots > 0:
                    rate = r["occupancy"] / total_spots
                    occupancy_rates.append(rate)

            avg_rate = sum(occupancy_rates) / len(occupancy_rates) if occupancy_rates else 0.0

            # Find peak time
            peak_reading = max(day_readings, key=lambda r: r["occupancy"])
            peak_time = peak_reading["time"]

            # Detect rush hours for this day
            rush_info = self._detect_rush_hours(day_readings, total_spots)

            # Calculate last safe arrival time
            safe_arrival_info = self._calculate_safe_arrival(day_readings, total_spots)

            day_patterns[day_num] = DayPattern(
                day_of_week=day_num,
                day_name=DAY_NAMES[day_num],
                readings_count=len(day_readings),
                avg_occupancy_rate=round(avg_rate, 3),
                peak_time=peak_time,
                rush_start=rush_info.get("rush_start"),
                rush_end=rush_info.get("rush_end"),
                evening_rush_start=rush_info.get("evening_rush_start"),
                evening_rush_end=rush_info.get("evening_rush_end"),
                last_safe_arrival=safe_arrival_info.get("last_safe_arrival"),
                fill_time_variance=safe_arrival_info.get("variance", 0.0)
            )

        # Calculate overall patterns
        overall = self._calculate_overall_patterns(day_patterns)

        return DayOfWeekSummary(
            carpark=carpark,
            day_patterns=day_patterns,
            overall=overall,
            data_quality=data_quality
        )

    def _calculate_data_quality(self, readings_by_day: dict, distinct_dates: set) -> DataQuality:
        """Calculate data quality metrics and confidence level."""
        total_days = len(distinct_dates)

        # Count distinct dates per weekday
        days_per_weekday = {}
        for day_num, day_readings in readings_by_day.items():
            dates = set(r["date"] for r in day_readings)
            days_per_weekday[day_num] = len(dates)

        min_days = min(days_per_weekday.values()) if days_per_weekday else 0

        # Determine confidence level
        if total_days >= 28:
            confidence = "high"
        elif total_days >= 14:
            confidence = "moderate"
        elif total_days >= 7:
            confidence = "limited"
        else:
            confidence = "very limited"

        # Identify gaps (days with no data)
        gaps = []
        for day_num in range(7):
            if day_num not in readings_by_day or not readings_by_day[day_num]:
                gaps.append(f"No {DAY_NAMES[day_num]} data")

        return DataQuality(
            total_days=total_days,
            min_days_per_weekday=min_days,
            confidence=confidence,
            gaps=gaps
        )

    def _detect_rush_hours(self, day_readings: list, total_spots: int) -> dict:
        """
        Detect morning and evening rush hour boundaries.

        Algorithm (from D2 in research.md):
        - Morning rush start: when occupancy increases >5% in 15min (5:00-10:00)
        - Morning rush end: when occupancy stabilizes (<2% change) after peak
        - Evening rush start: when occupancy decreases >5% in 15min (15:00-20:00)
        - Evening rush end: when occupancy stabilizes or reaches low point

        Args:
            day_readings: List of readings for a single day
            total_spots: Total parking spots

        Returns:
            Dict with rush_start, rush_end, evening_rush_start, evening_rush_end
        """
        if not day_readings or total_spots == 0:
            return {}

        # Sort by time
        sorted_readings = sorted(day_readings, key=lambda r: r["time"])

        # Group readings into 15-minute windows for rate of change calculation
        def get_occupancy_rate(reading):
            return reading["occupancy"] / total_spots

        result = {
            "rush_start": None,
            "rush_end": None,
            "evening_rush_start": None,
            "evening_rush_end": None
        }

        # Morning rush detection (5:00-10:00)
        morning_readings = [r for r in sorted_readings if "05:00" <= r["time"] <= "10:00"]
        if len(morning_readings) >= 2:
            # Find when occupancy increases >5% over a short period
            for i in range(1, len(morning_readings)):
                prev_rate = get_occupancy_rate(morning_readings[i - 1])
                curr_rate = get_occupancy_rate(morning_readings[i])
                change = curr_rate - prev_rate

                if change > 0.05 and result["rush_start"] is None:
                    result["rush_start"] = morning_readings[i - 1]["time"]

            # Find morning rush end (when occupancy stabilizes after peak)
            if result["rush_start"]:
                peak_rate = 0
                peak_idx = 0
                for i, r in enumerate(morning_readings):
                    rate = get_occupancy_rate(r)
                    if rate > peak_rate:
                        peak_rate = rate
                        peak_idx = i

                # Look for stabilization after peak
                for i in range(peak_idx + 1, len(morning_readings)):
                    if i > 0:
                        prev_rate = get_occupancy_rate(morning_readings[i - 1])
                        curr_rate = get_occupancy_rate(morning_readings[i])
                        if abs(curr_rate - prev_rate) < 0.02:
                            result["rush_end"] = morning_readings[i]["time"]
                            break

                # Default to peak time if no stabilization found
                if result["rush_end"] is None:
                    result["rush_end"] = morning_readings[peak_idx]["time"]

        # Evening rush detection (15:00-20:00)
        evening_readings = [r for r in sorted_readings if "15:00" <= r["time"] <= "20:00"]
        if len(evening_readings) >= 2:
            # Find when occupancy decreases >5% over a short period
            for i in range(1, len(evening_readings)):
                prev_rate = get_occupancy_rate(evening_readings[i - 1])
                curr_rate = get_occupancy_rate(evening_readings[i])
                change = prev_rate - curr_rate  # Decrease is positive

                if change > 0.05 and result["evening_rush_start"] is None:
                    result["evening_rush_start"] = evening_readings[i - 1]["time"]

            # Find evening rush end (stabilization or low point)
            if result["evening_rush_start"]:
                min_rate = 1.0
                min_idx = len(evening_readings) - 1
                for i, r in enumerate(evening_readings):
                    rate = get_occupancy_rate(r)
                    if rate < min_rate:
                        min_rate = rate
                        min_idx = i

                # Look for stabilization
                start_idx = next(
                    (i for i, r in enumerate(evening_readings) if r["time"] == result["evening_rush_start"]),
                    0
                )
                for i in range(start_idx + 1, len(evening_readings)):
                    if i > 0:
                        prev_rate = get_occupancy_rate(evening_readings[i - 1])
                        curr_rate = get_occupancy_rate(evening_readings[i])
                        if abs(curr_rate - prev_rate) < 0.02:
                            result["evening_rush_end"] = evening_readings[i]["time"]
                            break

                # Default to min point if no stabilization found
                if result["evening_rush_end"] is None:
                    result["evening_rush_end"] = evening_readings[min_idx]["time"]

        return result

    def _calculate_safe_arrival(self, day_readings: list, total_spots: int) -> dict:
        """
        Calculate the last safe arrival time (before carpark reaches 90% full).

        Args:
            day_readings: List of readings for a single day
            total_spots: Total parking spots

        Returns:
            Dict with last_safe_arrival time and variance
        """
        if not day_readings or total_spots == 0:
            return {"last_safe_arrival": None, "variance": 0.0}

        # Focus on morning window (5:00-10:00)
        morning_readings = [r for r in day_readings if "05:00" <= r["time"] <= "10:00"]
        if not morning_readings:
            return {"last_safe_arrival": None, "variance": 0.0}

        # Sort by time
        sorted_readings = sorted(morning_readings, key=lambda r: r["time"])

        # Find when occupancy crosses 90%
        threshold = 0.90
        fill_times = []
        last_safe_time = None

        # Group by date to track fill times per day instance
        readings_by_date = defaultdict(list)
        for r in sorted_readings:
            readings_by_date[r["date"]].append(r)

        for date, date_readings in readings_by_date.items():
            date_readings = sorted(date_readings, key=lambda r: r["time"])
            for r in date_readings:
                rate = r["occupancy"] / total_spots
                if rate < threshold:
                    last_safe_time = r["time"]
                else:
                    if last_safe_time:
                        fill_times.append(last_safe_time)
                    break

        # Calculate variance in fill times
        variance = 0.0
        if len(fill_times) >= 2:
            # Convert times to minutes for variance calculation
            def time_to_minutes(t):
                h, m = map(int, t.split(":"))
                return h * 60 + m

            minutes = [time_to_minutes(t) for t in fill_times]
            avg = sum(minutes) / len(minutes)
            variance = sum((m - avg) ** 2 for m in minutes) / len(minutes)
            variance = variance ** 0.5  # Standard deviation in minutes

        # Return most common or latest safe time
        if fill_times:
            # Use latest observed safe time as the recommendation
            fill_times.sort()
            last_safe_arrival = fill_times[-1] if fill_times else None
        else:
            # Never crossed 90% - carpark doesn't fill
            last_safe_arrival = "09:30"  # Default: any time works

        return {"last_safe_arrival": last_safe_arrival, "variance": round(variance, 1)}

    def _calculate_overall_patterns(self, day_patterns: dict) -> Optional[OverallPattern]:
        """
        Calculate overall cross-day patterns.

        Args:
            day_patterns: Dict of DayPattern keyed by day_of_week

        Returns:
            OverallPattern with busiest/quietest day and work hours
        """
        if not day_patterns:
            return None

        # Find busiest and quietest days
        patterns_list = list(day_patterns.values())
        busiest = max(patterns_list, key=lambda p: p.avg_occupancy_rate)
        quietest = min(patterns_list, key=lambda p: p.avg_occupancy_rate)

        # Calculate weekday vs weekend averages
        weekday_rates = [p.avg_occupancy_rate for d, p in day_patterns.items() if d < 5]
        weekend_rates = [p.avg_occupancy_rate for d, p in day_patterns.items() if d >= 5]

        weekday_avg = sum(weekday_rates) / len(weekday_rates) if weekday_rates else 0.0
        weekend_avg = sum(weekend_rates) / len(weekend_rates) if weekend_rates else 0.0

        # Derive typical work hours from rush patterns
        morning_ends = [p.rush_end for p in patterns_list if p.rush_end and p.day_of_week < 5]
        evening_starts = [p.evening_rush_start for p in patterns_list if p.evening_rush_start and p.day_of_week < 5]

        if morning_ends and evening_starts:
            # Most common morning end and evening start
            morning_ends.sort()
            evening_starts.sort()
            work_start = morning_ends[len(morning_ends) // 2]  # Median
            work_end = evening_starts[len(evening_starts) // 2]  # Median
            typical_work_hours = f"{work_start} - {work_end}"
        else:
            typical_work_hours = "Unable to determine"

        return OverallPattern(
            busiest_day=busiest.day_name,
            quietest_day=quietest.day_name,
            typical_work_hours=typical_work_hours,
            weekday_avg_occupancy=round(weekday_avg, 3),
            weekend_avg_occupancy=round(weekend_avg, 3)
        )

    def generate_insight(self, insight_type: str = "morning_recommendation", hours: int = 24, carpark: Optional[str] = None) -> dict:
        """
        Generate an insight using the LLM.

        Args:
            insight_type: Type of insight to generate (morning_recommendation, commuter_patterns)
            hours: Hours of data to analyze
            carpark: Specific carpark to analyze, or None for all carparks

        Returns:
            Dict containing the generated insight
        """
        data_summary = self.prepare_data_summary(hours, carpark=carpark)

        # For commuter-focused insights, prepare day-of-week analysis
        day_of_week_summary = None
        if insight_type in ("morning_recommendation", "commuter_patterns"):
            day_of_week_summary = self.prepare_day_of_week_summary(hours=hours, carpark=carpark)

        # Even with no data, generate insight with appropriate confidence for commuter types
        if not data_summary["carparks"]:
            if insight_type in ("morning_recommendation", "commuter_patterns"):
                # Generate limited insight instead of error
                return self._generate_limited_data_insight(insight_type, hours, carpark, data_summary)
            else:
                return {
                    "insight_type": insight_type,
                    "title": "No Data Available",
                    "content": "There is no parking data available for the selected time range.",
                    "data_range_start": data_summary["time_range"]["start"],
                    "data_range_end": data_summary["time_range"]["end"],
                    "metadata": {"hours": hours, "carpark_filter": carpark}
                }

        prompt = self._build_prompt(data_summary, insight_type, day_of_week_summary)
        response, thinking = self._call_llm(prompt)

        # Parse the response
        title, content = self._parse_response(response)

        # Build metadata with confidence info for commuter insights
        metadata = {
            "hours": hours,
            "carparks_analyzed": len(data_summary["carparks"]),
            "carpark_filter": carpark,
            "model": self.ark_model if self.ark_api_key else "claude-sonnet-4-20250514"
        }

        # Add confidence info for commuter-focused insights
        if day_of_week_summary and day_of_week_summary.data_quality:
            metadata["confidence"] = day_of_week_summary.data_quality.confidence
            metadata["days_of_data"] = day_of_week_summary.data_quality.total_days
            if day_of_week_summary.data_quality.gaps:
                metadata["data_gaps"] = day_of_week_summary.data_quality.gaps

        return {
            "insight_type": insight_type,
            "title": title,
            "content": content,
            "thinking": thinking,
            "data_range_start": data_summary["time_range"]["start"],
            "data_range_end": data_summary["time_range"]["end"],
            "metadata": metadata
        }

    def _generate_limited_data_insight(self, insight_type: str, hours: int, carpark: Optional[str], data_summary: dict) -> dict:
        """
        Generate insight when data is very limited or unavailable.
        Never returns errors - always provides some guidance with appropriate confidence warnings.
        """
        if insight_type == "morning_recommendation":
            title = "Early Arrival Recommended (Limited Data)"
            content = (
                "Based on very limited available data, we cannot provide specific day-by-day recommendations. "
                "As a general guideline for commuters:\n\n"
                "- Weekdays: Arrive before 8:00am for the best chance of finding parking\n"
                "- Mondays and Fridays: May be busier; consider arriving before 7:45am\n"
                "- Weekends: Generally lower demand; standard hours should be fine\n\n"
                "Note: This recommendation has VERY LIMITED confidence due to insufficient historical data. "
                "More data will improve recommendation accuracy over time."
            )
        else:  # commuter_patterns
            title = "Commuter Patterns (Limited Data)"
            content = (
                "Based on very limited available data, detailed commuter pattern analysis is not yet possible. "
                "General expectations for a typical Park & Ride facility:\n\n"
                "- Morning rush: Typically 7:00am - 9:00am\n"
                "- Evening rush: Typically 5:00pm - 7:00pm\n"
                "- Typical work hours: 9:00am - 5:30pm\n\n"
                "Note: These are general estimates with VERY LIMITED confidence. "
                "As more data is collected, specific patterns for this carpark will become available."
            )

        return {
            "insight_type": insight_type,
            "title": title,
            "content": content,
            "thinking": None,
            "data_range_start": data_summary["time_range"]["start"],
            "data_range_end": data_summary["time_range"]["end"],
            "metadata": {
                "hours": hours,
                "carparks_analyzed": 0,
                "carpark_filter": carpark,
                "confidence": "very limited",
                "days_of_data": 0,
                "note": "More data will improve recommendation accuracy"
            }
        }

    def _build_prompt(self, data_summary: dict, insight_type: str, day_of_week_summary: Optional[DayOfWeekSummary] = None) -> str:
        """Build the prompt for the LLM based on insight type."""
        # Route to type-specific prompt builders
        if insight_type == "morning_recommendation":
            return self._build_morning_recommendation_prompt(data_summary, day_of_week_summary)
        elif insight_type == "commuter_patterns":
            return self._build_commuter_patterns_prompt(data_summary, day_of_week_summary)
        else:
            # Default to morning recommendation if invalid type
            return self._build_morning_recommendation_prompt(data_summary, day_of_week_summary)

    def _build_morning_recommendation_prompt(self, data_summary: dict, dow_summary: Optional[DayOfWeekSummary]) -> str:
        """Build prompt for morning_recommendation insight type."""
        time_range = data_summary["time_range"]
        carpark = data_summary.get("carpark_filter", "Unknown")

        # Build day-by-day summary
        day_summaries = []
        if dow_summary and dow_summary.day_patterns:
            for day_num in range(7):
                pattern = dow_summary.day_patterns.get(day_num)
                if pattern:
                    safe_arrival = pattern.last_safe_arrival or "N/A"
                    variance_note = ""
                    if pattern.fill_time_variance > 15:
                        variance_note = " (high variance)"
                    elif pattern.fill_time_variance > 5:
                        variance_note = " (moderate variance)"

                    day_summaries.append(
                        f"- {pattern.day_name}: {pattern.readings_count} readings, "
                        f"avg {pattern.avg_occupancy_rate * 100:.0f}% full, "
                        f"peak at {pattern.peak_time or 'N/A'}, "
                        f"fills up by {safe_arrival}{variance_note}"
                    )
                else:
                    day_summaries.append(f"- {DAY_NAMES[day_num]}: No data available")

        day_text = "\n".join(day_summaries) if day_summaries else "No day-of-week data available"

        # Confidence context
        confidence = "very limited"
        days_of_data = 0
        if dow_summary and dow_summary.data_quality:
            confidence = dow_summary.data_quality.confidence
            days_of_data = dow_summary.data_quality.total_days

        confidence_note = f"Data confidence: {confidence} ({days_of_data} days of data)"
        if confidence == "very limited":
            confidence_note += "\nNote: Recommendations are preliminary due to limited historical data."

        return f"""Analyze parking patterns to provide day-specific arrival recommendations for commuters.

Carpark: {carpark}
Analysis Period: {time_range['start']} to {time_range['end']}
Target Commute Window: 7:30am - 9:30am
{confidence_note}

Day-by-Day Patterns:
{day_text}

Please provide:
1. A short title (max 10 words) with the key recommendation
2. Day-specific arrival time recommendations covering:
   - Recommended arrival time for EACH day of the week (Monday through Sunday)
   - Risk level for each day (low/medium/high chance of not finding a spot)
   - Brief reasoning for each recommendation
   - Any days to avoid or special considerations

Consider:
- Days where the carpark fills before 7:30am (recommend earlier arrival)
- Days where the carpark never fills (note parking is generally available)
- High variance in fill times (provide wider time ranges)
- Missing data for specific days (skip with note)

Format your response as:
TITLE: [Your title here]
CONTENT: [Your analysis here]"""

    def _build_commuter_patterns_prompt(self, data_summary: dict, dow_summary: Optional[DayOfWeekSummary]) -> str:
        """Build prompt for commuter_patterns insight type."""
        time_range = data_summary["time_range"]
        carpark = data_summary.get("carpark_filter", "Unknown")

        # Build rush hour summary
        rush_summaries = []
        if dow_summary and dow_summary.day_patterns:
            for day_num in range(5):  # Weekdays only for rush analysis
                pattern = dow_summary.day_patterns.get(day_num)
                if pattern:
                    morning = f"{pattern.rush_start or 'N/A'} - {pattern.rush_end or 'N/A'}"
                    evening = f"{pattern.evening_rush_start or 'N/A'} - {pattern.evening_rush_end or 'N/A'}"
                    rush_summaries.append(
                        f"- {pattern.day_name}: Morning rush {morning}, Evening rush {evening}"
                    )

        rush_text = "\n".join(rush_summaries) if rush_summaries else "No rush hour data available"

        # Overall patterns
        overall_text = "Overall patterns not available"
        if dow_summary and dow_summary.overall:
            overall = dow_summary.overall
            overall_text = f"""Overall Patterns:
- Busiest day: {overall.busiest_day}
- Quietest day: {overall.quietest_day}
- Typical work hours: {overall.typical_work_hours}
- Weekday avg occupancy: {overall.weekday_avg_occupancy * 100:.0f}%
- Weekend avg occupancy: {overall.weekend_avg_occupancy * 100:.0f}%"""

        # Confidence context
        confidence = "very limited"
        days_of_data = 0
        if dow_summary and dow_summary.data_quality:
            confidence = dow_summary.data_quality.confidence
            days_of_data = dow_summary.data_quality.total_days

        confidence_note = f"Data confidence: {confidence} ({days_of_data} days of data)"

        return f"""Analyze commuter patterns to understand local work habits based on parking data.

Carpark: {carpark}
Analysis Period: {time_range['start']} to {time_range['end']}
{confidence_note}

Rush Hour Patterns (Weekdays):
{rush_text}

{overall_text}

Please provide:
1. A short title (max 10 words) summarizing commuter behavior
2. A narrative analysis covering:
   - Morning rush period (START and END times, with peak)
   - Evening rush period (START and END times)
   - Typical work hours for commuters using this carpark
   - Weekday vs weekend patterns comparison
   - Any notable day-specific variations

This is a SINGLE carpark analysis. Focus on patterns specific to this location.

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
