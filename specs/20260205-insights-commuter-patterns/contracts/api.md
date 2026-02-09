# API Contract: Insights Generation

**Feature**: `insights-commuter-patterns` | **Date**: 2026-02-05

## Endpoint

**No changes to existing endpoint** - New insight types are passed via the existing `type` parameter.

### POST /api/insights/generate

Generate an AI-powered insight for parking data.

#### Request

```http
POST /api/insights/generate
Content-Type: application/json
```

```json
{
    "type": "morning_recommendation",
    "hours": 168,
    "carpark": "Narrabeen"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | No | `"daily_summary"` | Insight type to generate |
| `hours` | integer | No | `24` | Hours of historical data to analyze |
| `carpark` | string | No | `null` | Filter to specific carpark (recommended for new types) |

**New insight types:**
- `"morning_recommendation"` - Day-specific arrival time recommendations (P1)
- `"commuter_patterns"` - Rush hour and work habit analysis (P2)

#### Response

```json
{
    "insight": {
        "id": 42,
        "insight_type": "morning_recommendation",
        "title": "Arrive by 7:45am on Mondays",
        "content": "Based on 4 weeks of data, Monday mornings...",
        "thinking": "...(optional LLM reasoning)...",
        "data_range_start": "2026-01-29 00:00:00",
        "data_range_end": "2026-02-05 23:59:59",
        "metadata": {
            "hours": 168,
            "carparks_analyzed": 1,
            "carpark_filter": "Narrabeen",
            "model": "ep-xxx",
            "confidence": "high",
            "days_of_data": 28
        }
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `insight.id` | integer | Database ID of saved insight |
| `insight.insight_type` | string | Echo of requested type |
| `insight.title` | string | Short summary (max 10 words) |
| `insight.content` | string | Full analysis text |
| `insight.thinking` | string? | LLM reasoning (if available) |
| `insight.data_range_start` | string | Start of analyzed period |
| `insight.data_range_end` | string | End of analyzed period |
| `insight.metadata` | object | Additional context |

#### Error Responses

**400 Bad Request** - Invalid insight type or parameters
```json
{
    "error": "Invalid insight type: unknown_type"
}
```

**Note**: Insufficient data does NOT return an error. The system always generates insights regardless of data availability.

#### Limited Data Response (200 OK)

When data is limited (<7 days), the system still returns a valid insight with confidence indicators:
```json
{
    "insight": {
        "insight_type": "morning_recommendation",
        "title": "Early Arrival Recommended (Limited Data)",
        "content": "Based on 3 days of available data, patterns suggest arriving before 8:00am on weekdays. Note: This recommendation has very limited confidence due to insufficient historical data.",
        "metadata": {
            "confidence": "very limited",
            "days_of_data": 3,
            "note": "More data will improve recommendation accuracy"
        }
    }
}
```

| Days of Data | Confidence Level | Behavior |
|--------------|------------------|----------|
| 1-6 days | `"very limited"` | Basic patterns with high uncertainty warnings |
| 7-13 days | `"limited"` | Day-of-week patterns, may be incomplete |
| 14-27 days | `"moderate"` | Reliable for most patterns |
| 28+ days | `"high"` | Full week-over-week analysis |

---

## Usage Examples

### Morning Recommendation (P1)

```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "morning_recommendation",
    "hours": 168,
    "carpark": "Narrabeen"
  }'
```

Expected response contains day-specific arrival times:
```
Monday: Arrive before 7:45am
Tuesday: Arrive before 8:00am
Wednesday: Arrive before 7:50am
...
```

### Commuter Patterns (P2)

```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "commuter_patterns",
    "hours": 336,
    "carpark": "Narrabeen"
  }'
```

Expected response contains rush hour analysis:
```
Morning rush: 7:00am - 8:30am (peak at 8:15am)
Evening rush: 5:00pm - 6:15pm
Typical work hours: 8:30am - 5:30pm
```

---

## Backward Compatibility

- Existing `daily_summary` type unchanged
- Existing response structure preserved
- New types simply add to available options
- No API version bump required
