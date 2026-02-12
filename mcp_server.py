#!/usr/bin/env python3
"""
Park&Ride MCP Server - Exposes parking data to LLM agents.

Provides tools for querying parking availability, historical readings,
AI-generated insights, and live data from Transport NSW.

Usage:
    python mcp_server.py                    # Start via stdio
    MCP Inspector: npx @modelcontextprotocol/inspector python mcp_server.py
"""

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from parkride.storage import ParkingDatabase
from parkride.insights import InsightsGenerator


# --- Lifespan & Context ---

@dataclass
class AppContext:
    db: ParkingDatabase
    insights: InsightsGenerator


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    db_path = os.environ.get("PARKRIDE_DB_PATH", "parking_data.db")
    db = ParkingDatabase(db_path)
    insights = InsightsGenerator(db)
    try:
        yield AppContext(db=db, insights=insights)
    finally:
        db.close()


mcp = FastMCP(
    "Park&Ride",
    instructions="Real-time and historical parking availability for Transport NSW Park&Ride car parks.",
    lifespan=app_lifespan,
)


# --- Helpers ---

def _get_ctx(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


def _handle_error(e: Exception) -> str:
    return f"Error: {type(e).__name__}: {e}"


def _format_readings(readings: list[dict], fmt: str = "markdown") -> str:
    if not readings:
        return "No readings found."
    if fmt == "json":
        return json.dumps(readings, indent=2, default=str)
    lines = [f"| Timestamp | Carpark | Total | Occupied | Available |", "| --- | --- | ---: | ---: | ---: |"]
    for r in readings:
        lines.append(
            f"| {r['timestamp']} | {r['carpark_name']} | {r['total_spots']} | {r['occupancy']} | {r['available']} |"
        )
    return "\n".join(lines)


# --- Tools ---

@mcp.tool(annotations=ToolAnnotations(title="List Carparks", read_only_hint=True))
def parkride_list_carparks(ctx: Context) -> str:
    """List all carpark names in the database."""
    try:
        app = _get_ctx(ctx)
        carparks = app.db.get_available_carparks()
        if not carparks:
            return "No carparks found in the database."
        return "\n".join(f"- {name}" for name in carparks)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Latest Readings", read_only_hint=True))
def parkride_get_latest(
    carparks: list[str],
    response_format: str = "markdown",
    ctx: Context = None,
) -> str:
    """Get the latest reading for each specified carpark.

    Args:
        carparks: List of carpark names (partial match supported).
        response_format: "markdown" (default) or "json".
    """
    try:
        app = _get_ctx(ctx)
        results = []
        for name in carparks:
            reading = app.db.get_latest_reading(name)
            if reading:
                results.append(reading)

        if not results:
            return "No readings found for the specified carparks."

        if response_format == "json":
            return json.dumps(results, indent=2, default=str)

        lines = ["| Carpark | Available | Occupied | Total | Last Updated |", "| --- | ---: | ---: | ---: | --- |"]
        for r in results:
            lines.append(
                f"| {r['carpark_name']} | {r['available']} | {r['occupancy']} | {r['total_spots']} | {r['timestamp']} |"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Historical Readings", read_only_hint=True))
def parkride_get_readings(
    carpark: str,
    hours: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    response_format: str = "markdown",
    ctx: Context = None,
) -> str:
    """Get historical readings for a carpark with time filters.

    Args:
        carpark: Carpark name (partial match supported).
        hours: Get last N hours of data.
        start: Start datetime (ISO format, e.g. "2025-01-15 08:00:00").
        end: End datetime (ISO format).
        limit: Maximum number of readings to return.
        response_format: "markdown" (default) or "json".
    """
    try:
        app = _get_ctx(ctx)
        start_time = datetime.fromisoformat(start) if start else None
        end_time = datetime.fromisoformat(end) if end else None

        readings = app.db.get_readings(
            carpark=carpark,
            start_time=start_time,
            end_time=end_time,
            hours=hours,
            limit=limit,
        )
        return _format_readings(readings, response_format)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Insights", read_only_hint=True))
def parkride_get_insights(
    limit: int = 10,
    offset: int = 0,
    response_format: str = "markdown",
    ctx: Context = None,
) -> str:
    """Get paginated list of AI-generated insights.

    Args:
        limit: Maximum number of insights (default 10).
        offset: Number of insights to skip (default 0).
        response_format: "markdown" (default) or "json".
    """
    try:
        app = _get_ctx(ctx)
        insights = app.db.get_insights(limit=limit, offset=offset)
        total = app.db.get_insights_count()

        if not insights:
            return "No insights available."

        if response_format == "json":
            return json.dumps({"insights": insights, "total": total, "hasMore": offset + len(insights) < total}, indent=2, default=str)

        lines = [f"**{total} total insights** (showing {offset + 1}-{offset + len(insights)})\n"]
        for ins in insights:
            lines.append(f"### {ins['title']}")
            lines.append(f"*{ins['insight_type']}* | {ins['created_at']}\n")
            lines.append(ins["content"])
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Latest Insight", read_only_hint=True))
def parkride_get_latest_insight(
    response_format: str = "markdown",
    ctx: Context = None,
) -> str:
    """Get the most recent AI-generated insight.

    Args:
        response_format: "markdown" (default) or "json".
    """
    try:
        app = _get_ctx(ctx)
        insight = app.db.get_latest_insight()

        if not insight:
            return "No insights available yet."

        if response_format == "json":
            return json.dumps(insight, indent=2, default=str)

        lines = [
            f"## {insight['title']}",
            f"*{insight['insight_type']}* | {insight['created_at']}\n",
            insight["content"],
        ]
        if insight.get("metadata"):
            meta = insight["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)
            if meta.get("confidence"):
                lines.append(f"\n**Confidence:** {meta['confidence']} ({meta.get('days_of_data', '?')} days of data)")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Generate Insight", read_only_hint=False))
def parkride_generate_insight(
    type: str = "morning_recommendation",
    hours: int = 168,
    carpark: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Generate a new AI insight using LLM (Ark -> Anthropic fallback). Saves to database.

    Args:
        type: Insight type - "morning_recommendation" (day-specific arrival times) or "commuter_patterns" (rush hour analysis).
        hours: Hours of historical data to analyze (default 168 = 7 days).
        carpark: Specific carpark name, or omit for all carparks.
    """
    try:
        app = _get_ctx(ctx)
        insight = app.insights.generate_insight(
            insight_type=type, hours=hours, carpark=carpark
        )
        insight_id = app.insights.save_insight(insight)

        lines = [
            f"## {insight['title']}",
            f"*{insight['insight_type']}* | Saved as insight #{insight_id}\n",
            insight["content"],
        ]
        meta = insight.get("metadata", {})
        if meta.get("confidence"):
            lines.append(f"\n**Confidence:** {meta['confidence']} ({meta.get('days_of_data', '?')} days of data)")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Fetch Live Data", read_only_hint=True, open_world_hint=True))
def parkride_fetch_live(
    carpark: Optional[str] = None,
    response_format: str = "markdown",
) -> str:
    """Fetch live parking data from Transport NSW GraphQL API.

    Args:
        carpark: Filter by carpark name (partial match), or omit for all carparks.
        response_format: "markdown" (default) or "json".
    """
    try:
        from parkride.collector import fetch_with_retry, filter_carpark

        data = fetch_with_retry()
        if data is None:
            return "Failed to fetch live data from Transport NSW API after 3 retries."

        if carpark:
            data = filter_carpark(data, carpark)

        if not data:
            return "No carparks matched the filter." if carpark else "No data returned from API."

        if response_format == "json":
            return json.dumps(data, indent=2, default=str)

        lines = [
            f"**Live Data** ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n",
            "| Carpark | Available | Occupied | Total |",
            "| --- | ---: | ---: | ---: |",
        ]
        for d in sorted(data, key=lambda x: x["name"]):
            lines.append(f"| {d['name']} | {d['available']} | {d['occupancy']} | {d['spots']} |")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# --- Entry point ---

if __name__ == "__main__":
    mcp.run(transport="stdio")
