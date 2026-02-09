# Research: Commuter-Focused Parking Insights

## Overview

This document captures research findings and decisions for implementing commuter-focused parking insights.

## Decision Log

### D1: Day-of-Week Data Grouping Strategy

**Decision**: Group readings by day of week using Python's `datetime.weekday()` method (0=Monday, 6=Sunday)

**Rationale**:
- Native Python method, no additional dependencies
- Consistent with ISO 8601 week numbering
- SQLite `strftime('%w')` uses 0=Sunday, which would require conversion

**Alternatives Considered**:
- SQLite `strftime('%w', timestamp)` - Rejected due to 0=Sunday convention mismatch
- Pandas `dt.dayofweek` - Rejected to avoid adding pandas dependency for simple grouping

### D2: Rush Hour Detection Algorithm

**Decision**: Use rate-of-change threshold (>5% occupancy change in 15 minutes) to detect rush hour boundaries

**Rationale**:
- Simple threshold-based approach aligns with Constitution Principle I (Simplicity First)
- 5% threshold is meaningful for typical carpark sizes (46-100 spots)
- 15-minute window smooths out noise from individual readings

**Algorithm**:
```
Morning Rush Start: First time occupancy increases >5% in 15 min (between 5:00-10:00)
Morning Rush End: First time occupancy stabilizes (<2% change) after peak
Evening Rush Start: First time occupancy decreases >5% in 15 min (between 15:00-20:00)
Evening Rush End: First time occupancy stabilizes (<2% change) or reaches low point
```

**Alternatives Considered**:
- Statistical change-point detection (e.g., CUSUM) - Rejected as over-engineered for this use case
- Fixed time windows (e.g., 7-9am) - Rejected as inflexible to actual patterns

### D3: Data Sufficiency Threshold

**Decision**: Always generate insights regardless of data availability; use confidence levels to indicate reliability. No minimum data requirement that would block insight generation.

**Rationale**:
- System MUST NOT return errors or refuse to generate insights for insufficient data
- Even 1 day of data should produce limited conclusions with appropriate warnings
- Confidence levels communicate reliability without blocking functionality
- Aligns with spec requirement FR-007 (handle insufficient data gracefully)

**Confidence Levels**:
- 1-6 days = "very limited" - basic patterns only, high uncertainty
- 7-13 days = "limited" - day-of-week patterns possible but may be incomplete
- 14-27 days = "moderate" - reliable for most patterns
- 28+ days = "high" - full week-over-week comparison available

**Behavior by Data Availability**:
- <7 days: Generate insight with available data, clearly note limited confidence
- 7+ days: Generate full day-of-week analysis with appropriate confidence level

**Alternatives Considered**:
- Strict 7-day minimum with error response - Rejected per user clarification; users want limited conclusions, not errors
- No confidence indicators - Rejected as users need to understand data reliability

### D4: LLM Prompt Strategy for New Insight Types

**Decision**: Create type-specific prompts using a dictionary mapping, keeping `_build_prompt()` as the single entry point

**Rationale**:
- Maintains Single Source of Truth (Constitution Principle IV)
- Each insight type has distinct output requirements
- Existing `_build_prompt(data_summary, insight_type)` signature already supports this

**Prompt Structure**:
- `morning_recommendation`: Day-by-day arrival recommendations with confidence levels
- `commuter_patterns`: Rush hour analysis with start/end times, work habit inference

### D5: Data Summary Enhancement

**Decision**: Add `prepare_day_of_week_summary()` method that groups data by day and calculates per-day metrics

**Rationale**:
- Reusable for both new insight types
- Keeps existing `prepare_data_summary()` unchanged for backward compatibility
- Returns structured dict with day-specific patterns for LLM prompt construction

**Data Structure**:
```python
{
    "day_patterns": {
        0: {  # Monday
            "day_name": "Monday",
            "readings_count": 150,
            "rush_start": "07:15",
            "rush_end": "08:45",
            "peak_time": "08:30",
            "evening_rush_start": "17:00",
            "evening_rush_end": "18:30",
            "avg_fill_rate": 0.85,
            "confidence": "high"
        },
        # ... days 1-6
    },
    "overall": {
        "busiest_day": "Monday",
        "quietest_day": "Friday",
        "typical_work_hours": "8:30am - 5:30pm"
    }
}
```

### D6: Existing API Compatibility

**Decision**: No changes to `/api/insights/generate` endpoint - new insight types passed via existing `type` parameter

**Rationale**:
- API already accepts arbitrary `insight_type` string
- Existing response structure (`insight`, `id`) unchanged
- Frontend can request new types without backend API changes

**Usage**:
```json
POST /api/insights/generate
{
    "type": "morning_recommendation",
    "hours": 168,
    "carpark": "Narrabeen"
}
```

### D7: Dashboard Frontend Integration

**Decision**: Add a dropdown/selector to the existing "Generate Insights" button in `dashboard/static/js/dashboard.js`

**Rationale**:
- Minimal UI change - extends existing button rather than adding new sections
- Users can choose between `daily_summary`, `morning_recommendation`, and `commuter_patterns`
- Carpark parameter auto-populated from current chart filter selection
- Hours parameter remains independently controlled by existing time range selector

**Behavior**:
- Dropdown appears alongside or within the existing Generate Insights button
- `morning_recommendation` and `commuter_patterns` require a single carpark to be selected
- If no carpark is filtered when a carpark-specific type is chosen, show inline message: "Please select a specific carpark first"
- Hours control remains independent (not auto-set by insight type)

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| How to handle carparks with no weekend data? | Skip weekend patterns in output, note in response |
| What if carpark fills before 7:30am consistently? | Recommend earlier arrival, note pattern in insight |
| How to handle gaps in data (e.g., server downtime)? | Calculate confidence based on data density, warn if sparse |

## Dependencies

No new dependencies required. Implementation uses:
- Python standard library: `datetime`, `collections.defaultdict`
- Existing: `parkride.storage.ParkingDatabase`
- Existing: LLM clients (OpenAI SDK for Ark, Anthropic SDK)

## Performance Considerations

- Day-of-week grouping: O(n) single pass through readings
- Rush hour detection: O(n) with 15-minute sliding window
- LLM call: ~2-10 seconds (unchanged from current)
- Total expected time: <15 seconds for 7 days of data (excluding LLM response)
