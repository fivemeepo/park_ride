#!/usr/bin/env python3
"""
Park&Ride MCP Server - Exposes parking data to LLM agents via HTTP API.

Connects to the Park&Ride dashboard REST API, allowing remote usage
without direct database access.

Usage:
    python mcp_server.py                    # Start via stdio
    MCP Inspector: npx @modelcontextprotocol/inspector python mcp_server.py

Environment:
    PARKRIDE_API_URL: Dashboard base URL (default: http://localhost:8080)
"""

import json
import os
from datetime import datetime
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


API_URL = os.environ.get("PARKRIDE_API_URL", "http://localhost:8080")

# Transport NSW GraphQL API (for live fetch, called directly)
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


mcp = FastMCP(
    "Park&Ride",
    instructions="Real-time and historical parking availability for Transport NSW Park&Ride car parks.",
)


# --- Helpers ---

def _api(path: str, **params) -> dict:
    """GET request to dashboard API."""
    resp = httpx.get(f"{API_URL}/api{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, data: dict) -> dict:
    """POST request to dashboard API."""
    resp = httpx.post(f"{API_URL}/api{path}", json=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _handle_error(e: Exception) -> str:
    return f"Error: {type(e).__name__}: {e}"


# --- Tools ---

@mcp.tool(annotations=ToolAnnotations(title="List Carparks", read_only_hint=True))
def parkride_list_carparks() -> str:
    """List all carpark names in the database."""
    try:
        data = _api("/carparks")
        carparks = data.get("carparks", [])
        if not carparks:
            return json.dumps({"carparks": []})
        return json.dumps({"carparks": carparks}, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Latest Readings", read_only_hint=True))
def parkride_get_latest(
    carparks: list[str],
    response_format: str = "json",
) -> str:
    """Get the latest reading for each specified carpark.

    Args:
        carparks: List of carpark names (partial match supported).
        response_format: "markdown" (default) or "json".
    """
    try:
        data = _api("/latest", carpark=",".join(carparks))
        latest = data.get("latest", {})

        if not latest:
            return json.dumps({"readings": []})

        if response_format != "json":
            lines = ["| Carpark | Available | Occupied | Total | Last Updated |", "| --- | ---: | ---: | ---: | --- |"]
            for name, r in latest.items():
                lines.append(
                    f"| {name} | {r['available']} | {r['occupancy']} | {r['total_spots']} | {r['timestamp']} |"
                )
            return "\n".join(lines)

        return json.dumps(latest, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Historical Readings", read_only_hint=True))
def parkride_get_readings(
    carpark: str,
    hours: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    response_format: str = "json",
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
        params = {"carpark": carpark}
        if hours is not None:
            params["hours"] = hours
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        data = _api("/readings", **params)
        readings_by_carpark = data.get("readings", {})

        # Flatten readings from all matched carparks
        all_readings = []
        for cp_name, readings in readings_by_carpark.items():
            for r in readings:
                all_readings.append({**r, "carpark_name": cp_name})

        if limit:
            all_readings = all_readings[:limit]

        if not all_readings:
            return json.dumps({"readings": []})

        if response_format != "json":
            lines = ["| Timestamp | Carpark | Total | Occupied | Available |", "| --- | --- | ---: | ---: | ---: |"]
            for r in all_readings:
                lines.append(
                    f"| {r['timestamp']} | {r['carpark_name']} | {r['total_spots']} | {r['occupancy']} | {r['available']} |"
                )
            return "\n".join(lines)

        return json.dumps(all_readings, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Insights", read_only_hint=True))
def parkride_get_insights(
    limit: int = 10,
    offset: int = 0,
    response_format: str = "json",
) -> str:
    """Get paginated list of AI-generated insights.

    Args:
        limit: Maximum number of insights (default 10).
        offset: Number of insights to skip (default 0).
        response_format: "markdown" (default) or "json".
    """
    try:
        data = _api("/insights", limit=limit, offset=offset)
        insights = data.get("insights", [])
        total = data.get("total", 0)

        if not insights:
            return json.dumps({"insights": [], "total": 0})

        if response_format != "json":
            lines = [f"**{total} total insights** (showing {offset + 1}-{offset + len(insights)})\n"]
            for ins in insights:
                lines.append(f"### {ins['title']}")
                lines.append(f"*{ins['insight_type']}* | {ins['created_at']}\n")
                lines.append(ins["content"])
                lines.append("")
            return "\n".join(lines)

        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Get Latest Insight", read_only_hint=True))
def parkride_get_latest_insight(
    response_format: str = "json",
) -> str:
    """Get the most recent AI-generated insight.

    Args:
        response_format: "markdown" (default) or "json".
    """
    try:
        data = _api("/insights/latest")
        insight = data.get("insight")

        if not insight:
            return json.dumps({"insight": None})

        if response_format != "json":
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

        return json.dumps(insight, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Generate Insight", read_only_hint=False))
def parkride_generate_insight(
    type: str = "morning_recommendation",
    hours: int = 168,
    carpark: Optional[str] = None,
) -> str:
    """Generate a new AI insight using LLM (Ark -> Anthropic fallback). Saves to database.

    Args:
        type: Insight type - "morning_recommendation" (day-specific arrival times) or "commuter_patterns" (rush hour analysis).
        hours: Hours of historical data to analyze (default 168 = 7 days).
        carpark: Specific carpark name, or omit for all carparks.
    """
    try:
        payload = {"type": type, "hours": hours}
        if carpark:
            payload["carpark"] = carpark

        data = _api_post("/insights/generate", payload)

        if "error" in data:
            return f"Error: {data['error']}"

        insight = data["insight"]
        insight_id = data.get("id", "?")

        return json.dumps({"id": insight_id, "insight": insight}, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(annotations=ToolAnnotations(title="Fetch Live Data", read_only_hint=True, open_world_hint=True))
def parkride_fetch_live(
    carpark: Optional[str] = None,
    response_format: str = "json",
) -> str:
    """Fetch live parking data from Transport NSW GraphQL API.

    Args:
        carpark: Filter by carpark name (partial match), or omit for all carparks.
        response_format: "markdown" (default) or "json".
    """
    try:
        resp = httpx.post(
            GRAPHQL_ENDPOINT,
            json={"operationName": "getLocations", "query": GRAPHQL_QUERY, "variables": {}},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()

        locations = resp.json()["data"]["result"]["pnrLocations"]
        data = [
            {
                "name": loc["name"].replace("Park&Ride - ", ""),
                "spots": loc["spots"],
                "occupancy": loc["occupancy"],
                "available": loc["spots"] - loc["occupancy"],
            }
            for loc in locations
        ]

        if carpark:
            data = [d for d in data if carpark.lower() in d["name"].lower()]

        if not data:
            return json.dumps({"locations": [], "filter": carpark})

        if response_format != "json":
            lines = [
                f"**Live Data** ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n",
                "| Carpark | Available | Occupied | Total |",
                "| --- | ---: | ---: | ---: |",
            ]
            for d in sorted(data, key=lambda x: x["name"]):
                lines.append(f"| {d['name']} | {d['available']} | {d['occupancy']} | {d['spots']} |")
            return "\n".join(lines)

        return json.dumps({"timestamp": datetime.now().isoformat(), "locations": data}, indent=2, default=str)
    except Exception as e:
        return _handle_error(e)


# --- Entry point ---

if __name__ == "__main__":
    mcp.run(transport="stdio")
