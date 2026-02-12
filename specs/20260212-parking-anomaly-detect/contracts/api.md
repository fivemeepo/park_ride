# API Contract: Anomaly Detection

**Feature**: `20260212-parking-anomaly-detect`
**Date**: 2026-02-12

## REST API

### POST /api/insights/generate

**Existing endpoint - no changes to interface, just accepts new `type` value.**

#### Request

```json
{
  "type": "anomaly_detection",
  "hours": 720,
  "carpark": "Narrabeen"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | - | Insight type: `anomaly_detection` (new), `morning_recommendation`, `commuter_patterns` |
| `hours` | integer | No | 720 | Hours of historical data to analyze (default 30 days) |
| `carpark` | string | No | null | Specific carpark name, or null for all carparks |

#### Response (Success)

```json
{
  "id": 42,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "3 Anomalies Detected at Narrabeen",
    "content": "Analysis of parking data from Jan 13 to Feb 12 reveals...",
    "thinking": "The LLM's reasoning process...",
    "data_range_start": "2026-01-13 00:00:00",
    "data_range_end": "2026-02-12 23:59:59",
    "metadata": {
      "hours": 720,
      "carpark_filter": "Narrabeen",
      "confidence": "moderate",
      "days_of_data": 25,
      "anomaly_count": 3,
      "anomalies_by_type": {
        "occupancy_rate": 2,
        "sudden_spike": 1
      },
      "anomalies_by_severity": {
        "low": 1,
        "medium": 1,
        "high": 1
      }
    }
  }
}
```

#### Response (No Anomalies)

```json
{
  "id": 43,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "No Anomalies Detected",
    "content": "Analysis of parking data shows consistent patterns...",
    "thinking": null,
    "data_range_start": "2026-01-13 00:00:00",
    "data_range_end": "2026-02-12 23:59:59",
    "metadata": {
      "hours": 720,
      "carpark_filter": "Narrabeen",
      "confidence": "high",
      "days_of_data": 30,
      "anomaly_count": 0
    }
  }
}
```

#### Response (Insufficient Data)

```json
{
  "id": 44,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "Limited Analysis Available",
    "content": "Insufficient historical data for statistical analysis...",
    "thinking": null,
    "data_range_start": "2026-02-08 00:00:00",
    "data_range_end": "2026-02-12 23:59:59",
    "metadata": {
      "hours": 720,
      "carpark_filter": "Narrabeen",
      "confidence": "very limited",
      "days_of_data": 4,
      "note": "Minimum 7 days required for baseline calculation"
    }
  }
}
```

---

## MCP Tool Interface

### parkride_generate_insight

**Updated docstring to include new type.**

```python
@mcp.tool(annotations=ToolAnnotations(title="Generate Insight", read_only_hint=False))
def parkride_generate_insight(
    type: str = "morning_recommendation",
    hours: int = 168,
    carpark: Optional[str] = None,
) -> str:
    """Generate a new AI insight using LLM (Ark -> Anthropic fallback). Saves to database.

    Args:
        type: Insight type - "morning_recommendation" (day-specific arrival times),
              "commuter_patterns" (rush hour analysis), or
              "anomaly_detection" (detect abnormal patterns in past 30 days).
        hours: Hours of historical data to analyze (default 168 = 7 days for morning/commuter,
               use 720 = 30 days for anomaly_detection).
        carpark: Specific carpark name, or omit for all carparks.
    """
```

#### MCP Response Format

```json
{
  "id": 42,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "3 Anomalies Detected at Narrabeen",
    "content": "Analysis reveals 3 unusual patterns...",
    "metadata": {
      "confidence": "moderate",
      "anomaly_count": 3,
      "anomalies_by_type": {"occupancy_rate": 2, "sudden_spike": 1}
    }
  }
}
```

---

## Internal Python Interface

### InsightsGenerator.generate_insight()

**No signature changes - existing interface handles new type.**

```python
def generate_insight(
    self,
    insight_type: str = "morning_recommendation",
    hours: int = 24,
    carpark: Optional[str] = None
) -> dict:
    """Generate an insight using the LLM.

    Args:
        insight_type: Type of insight - "morning_recommendation", "commuter_patterns",
                      or "anomaly_detection" (new)
        hours: Hours of data to analyze (use 720 for anomaly_detection)
        carpark: Specific carpark to analyze, or None for all carparks

    Returns:
        Dict containing the generated insight
    """
```

### New Method: prepare_anomaly_summary()

```python
def prepare_anomaly_summary(
    self,
    hours: int = 720,
    carpark: Optional[str] = None
) -> Optional[AnomalySummary]:
    """Prepare anomaly analysis summary for a carpark.

    Args:
        hours: Number of hours of data to analyze (default 720 = 30 days)
        carpark: Specific carpark to analyze (required for single-carpark mode)

    Returns:
        AnomalySummary with detected anomalies and statistics,
        or None if carpark not specified
    """
```

### New Method: prepare_cross_carpark_analysis()

```python
def prepare_cross_carpark_analysis(
    self,
    hours: int = 720
) -> CrossCarparkAnalysis:
    """Prepare cross-carpark anomaly correlation analysis.

    Args:
        hours: Number of hours of data to analyze (default 720 = 30 days)

    Returns:
        CrossCarparkAnalysis with per-carpark summaries and correlated events
    """
```
