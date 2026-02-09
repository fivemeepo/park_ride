# Feature Spec: AI-Powered Parking Insights

## Overview

Generate intelligent morning recommendations and commuter pattern analysis of parking availability using LLM providers with automatic fallback.

## Problem Statement

Raw parking data (timestamps, occupancy numbers) is hard for users to interpret. Users need:
- Natural language summaries of parking trends
- Peak time identification
- Actionable recommendations (best times to find parking)

## Business Rules

### BR-1: LLM Provider Fallback Chain
| Priority | Provider | Condition |
|----------|----------|-----------|
| 1 | ByteDance Ark | `ARK_API_KEY` and `ARK_MODEL_ID` set |
| 2 | Anthropic Claude | `ANTHROPIC_API_KEY` set |
| 3 | Static Message | No API keys configured |

### BR-2: Insight Generation
- **Input**: Last 24 hours of parking readings
- **Minimum data**: At least 10 readings required, otherwise skip
- **Per-carpark stats calculated**:
  - Available spots: min, max, average
  - Occupancy rate: min, max, average (as percentage)
  - Peak occupancy time (timestamp of highest occupancy)

### BR-3: Insight Storage
- Each insight stored with: content, timestamp, provider used, metadata
- Insights are immutable (never updated, only new ones created)
- No automatic cleanup (retained indefinitely)

### BR-4: Rate Limiting
- Manual generation only (no auto-generation)
- User triggers via dashboard button or API call

## Data Flow

```
User clicks "Generate Insight"
         ↓
POST /api/insights/generate
         ↓
insights.py: generate_insights()
         ↓
storage.py: get_readings_by_hours(24)
         ↓
Build data summary (per-carpark stats)
         ↓
LLM prompt with parking data
         ↓
Store result in insights table
         ↓
Return insight text to user
```

## API Contract

### Generate Insight
```
POST /api/insights/generate
Response: { "success": true, "insight": "Based on the last 24 hours..." }
Error:    { "success": false, "error": "No readings available" }
```

### Get Latest Insight
```
GET /api/insights/latest
Response: { "content": "...", "timestamp": "...", "provider": "ark" }
```

### Get Insight History
```
GET /api/insights?limit=10
Response: [ { "content": "...", "timestamp": "...", "provider": "ark" }, ... ]
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No API keys configured | Return static message: "Insights require API configuration" |
| Ark API timeout (>30s) | Fall back to Anthropic |
| Anthropic API timeout | Fall back to static message |
| No readings in 24h | Return error, do not store |
| LLM returns empty response | Retry once, then fall back |

## LLM Prompt Template

```
Analyze parking availability for the following Sydney Park&Ride locations.
Provide a brief summary including:
- Overall trends
- Busiest and least busy carparks
- Best times to find parking
- Any anomalies or notable patterns

Data:
{carpark_summaries}
```

## Dependencies

- `parkride/storage.py` - Read historical data
- `volcenginesdkarkruntime` - ByteDance Ark client
- `anthropic` - Anthropic client
- Environment variables for API keys

## Testing Scenarios

1. **Happy path**: Ark API configured, 24h of data → insight generated
2. **Fallback**: Ark fails → Anthropic succeeds
3. **No data**: Empty database → error returned, nothing stored
4. **No keys**: No env vars → static message returned

## Success Metrics

- Insight generation < 10 seconds
- Fallback triggers < 5% of requests
- User finds insights actionable (qualitative)
