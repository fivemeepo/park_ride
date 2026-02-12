# Data Model: Parking Anomaly Detection

**Feature**: `20260212-parking-anomaly-detect`
**Date**: 2026-02-12

## New Dataclasses (in `parkride/insights.py`)

### Anomaly

Represents a single detected anomaly.

```python
@dataclass
class Anomaly:
    """A single detected anomaly in parking data."""
    timestamp: str              # ISO format datetime when anomaly occurred
    carpark: str                # Carpark name
    anomaly_type: str           # One of: occupancy_rate, fill_time, pattern_shift, sudden_spike, sudden_drop, weekday_inversion
    severity: str               # One of: low, medium, high
    z_score: float              # Statistical deviation (how many std devs from mean)
    actual_value: float         # The observed value (occupancy rate 0.0-1.0)
    baseline_mean: float        # Expected value (mean of baseline period)
    baseline_std: float         # Standard deviation of baseline period
    description: str            # Human-readable description of the anomaly
```

### TimeSlotBaseline

Statistical baseline for a specific time slot (day_of_week, hour).

```python
@dataclass
class TimeSlotBaseline:
    """Baseline statistics for a (day_of_week, hour) time slot."""
    day_of_week: int            # 0=Monday, 6=Sunday
    hour: int                   # 0-23
    mean_occupancy_rate: float  # Average occupancy rate (0.0-1.0)
    std_deviation: float        # Standard deviation
    sample_count: int           # Number of readings in baseline
```

### AnomalySummary

Aggregated anomaly analysis for a carpark.

```python
@dataclass
class AnomalySummary:
    """Complete anomaly analysis for a carpark."""
    carpark: str
    analysis_start: str         # Start of analysis period
    analysis_end: str           # End of analysis period
    baseline_start: str         # Start of baseline period
    baseline_end: str           # End of baseline period
    anomalies: list[Anomaly]    # Detected anomalies
    total_readings_analyzed: int
    anomaly_count: int
    anomalies_by_type: dict[str, int]    # Count per anomaly type
    anomalies_by_severity: dict[str, int] # Count per severity level
    data_quality: DataQuality   # Reuse existing DataQuality dataclass
```

### CrossCarparkAnalysis

Multi-carpark correlation analysis (for all-carparks mode).

```python
@dataclass
class CrossCarparkAnalysis:
    """Cross-carpark anomaly correlation analysis."""
    carpark_summaries: dict[str, AnomalySummary]  # Per-carpark results
    correlated_events: list[dict]  # [{date, carparks, anomaly_types, description}]
    most_anomalous_carpark: Optional[str]  # Carpark with most anomalies
    system_wide_patterns: list[str]  # Notable patterns across all carparks
```

## Database Schema

**No schema changes required.** Existing `insights` table handles new insight type:

```sql
-- Existing table (no changes)
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL,
    insight_type TEXT NOT NULL,    -- "anomaly_detection" (new value)
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    data_range_start DATETIME,
    data_range_end DATETIME,
    metadata TEXT                  -- JSON with anomaly details
);
```

### Metadata Structure for `anomaly_detection`

```json
{
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
  },
  "baseline_period": "2026-01-13 to 2026-01-19",
  "analysis_period": "2026-01-20 to 2026-02-12"
}
```

## Entity Relationships

```
parking_readings (existing)
        │
        │ (read by)
        ▼
TimeSlotBaseline ────► AnomalySummary
        │                    │
        │ (aggregated)       │ (stored as)
        │                    ▼
        │              insights table
        ▼                    │
    Anomaly ─────────────────┘
        │
        │ (if all carparks)
        ▼
CrossCarparkAnalysis
```

## Anomaly Type Definitions

| Type | Trigger Condition | Severity Calculation |
|------|-------------------|----------------------|
| `occupancy_rate` | Reading deviates >2σ from time-slot baseline AND >60% absolute deviation | Based on z-score magnitude |
| `fill_time` | 90% fill time differs >30 min from baseline | Based on time deviation |
| `pattern_shift` | Rush hour timing shifts >30 min | Based on shift magnitude |
| `sudden_spike` | >20% occupancy increase in 30 min (vs <5% baseline) | Always "high" |
| `sudden_drop` | >20% occupancy decrease in 30 min (vs <5% baseline) | Always "high" |
| `weekday_inversion` | Weekend shows weekday pattern or vice versa | Based on pattern similarity |

## Validation Rules

1. **Minimum baseline samples**: At least 3 readings per time slot for meaningful statistics
2. **Minimum data period**: 7 days required for any statistical analysis
3. **Z-score bounds**: Cap at ±10 to avoid floating point issues with extreme outliers
4. **Dual threshold for occupancy_rate anomalies**:
   - Z-score threshold: |z| > 2.0
   - Absolute deviation threshold: >60% from baseline mean
   - Both conditions must be met to flag an anomaly (prevents false positives with limited data)
5. **Invalid data filtering**: Skip readings where occupancy rate >100% or <0% (sensor errors)
6. **Severity mapping**:
   - `low`: 2.0 ≤ |z| < 2.5
   - `medium`: 2.5 ≤ |z| < 3.0
   - `high`: |z| ≥ 3.0
