# Quickstart: Commuter-Focused Parking Insights

**Feature**: `insights-commuter-patterns` | **Date**: 2026-02-05

## Prerequisites

- Python 3.11+
- Park&Ride environment configured (`.env` with `ARK_API_KEY` or `ANTHROPIC_API_KEY`)
- Some parking data collected (any amount works; 7+ days recommended for better accuracy)

## Quick Usage

### Via Dashboard UI

1. Open the dashboard at `http://localhost:8080`
2. Select a specific carpark from the carpark filter (e.g., "Narrabeen")
3. Use the insight type dropdown next to "Generate Insights" button to choose:
   - **Daily Summary** - General parking trends (default)
   - **Morning Recommendation** - Day-specific arrival time suggestions
   - **Commuter Patterns** - Rush hour and work habit analysis
4. Click "Generate Insights"

**Note**: `Morning Recommendation` and `Commuter Patterns` require a specific carpark to be selected. If no carpark is filtered, an inline message will prompt you to select one.

### 1. Morning Arrival Recommendations

Get day-specific arrival time suggestions for the 7:30am-9:30am commute window.

**Via API:**
```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "morning_recommendation", "hours": 168, "carpark": "Narrabeen"}'
```

**Expected Output:**
- Day-by-day arrival time recommendations
- Confidence indicators based on data availability
- Risk assessment for different arrival times

### 2. Commuter Pattern Analysis

Understand rush hour patterns and local work habits.

**Via API:**
```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "commuter_patterns", "hours": 336, "carpark": "Narrabeen"}'
```

**Expected Output:**
- Morning rush period (start AND end times)
- Evening rush period (start AND end times)
- Typical work hours for the area
- Weekday vs weekend pattern comparison

## Parameters

| Parameter | Recommended Value | Description |
|-----------|-------------------|-------------|
| `hours` | 168 (7 days) minimum | More data = higher confidence |
| `carpark` | Specific carpark name | Single carpark analysis (no cross-comparison by default) |

## Confidence Levels

The system always generates insights regardless of data availability. Confidence level indicates reliability:

| Days of Data | Confidence | Notes |
|--------------|------------|-------|
| 1-6 days | Very Limited | Basic patterns with high uncertainty; still useful for initial guidance |
| 7-13 days | Limited | Day-of-week patterns possible but may be incomplete |
| 14-27 days | Moderate | Reliable for most patterns |
| 28+ days | High | Full week-over-week comparison |

**Important**: The system will NEVER refuse to generate insights due to insufficient data. Even 1 day of data produces limited conclusions.

## Example Scenarios

### Scenario A: Planning Monday Commute
```bash
# Get recommendations for Narrabeen car park
curl -X POST http://localhost:8080/api/insights/generate \
  -d '{"type": "morning_recommendation", "hours": 336, "carpark": "Narrabeen"}'
```

Response might include:
> "On Mondays, arrive before 7:45am for best chance of finding a spot.
> Based on 4 weeks of data, the carpark typically fills by 8:00am on Mondays."

### Scenario B: Understanding Local Work Habits
```bash
# Analyze commuter patterns at Warriewood
curl -X POST http://localhost:8080/api/insights/generate \
  -d '{"type": "commuter_patterns", "hours": 336, "carpark": "Warriewood"}'
```

Response might include:
> "Morning rush: 6:45am - 8:30am (peak at 8:00am)
> Evening rush: 5:00pm - 6:30pm
> Commuters in this area typically work 8:30am - 5:30pm"

## Troubleshooting

### "Very Limited Confidence" in Response
This is normal for new carparks with less than 7 days of data. The system still provides useful recommendations - just note they may change as more data is collected.

### No Rush Hour Detected
- Carpark may not have typical commuter patterns
- Check if carpark has sufficient variability (always full or always empty won't show rush)
- Try a longer time range (336 hours = 14 days)
