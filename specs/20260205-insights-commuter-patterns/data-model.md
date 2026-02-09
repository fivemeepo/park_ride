# Data Model: Commuter-Focused Parking Insights

**Feature**: `insights-commuter-patterns` | **Date**: 2026-02-05

## Entity Definitions

### DayPattern

Aggregated statistics for a specific day of week, derived from parking readings.

```python
@dataclass
class DayPattern:
    """Statistics for a single day of the week."""
    day_of_week: int          # 0=Monday, 6=Sunday (Python weekday convention)
    day_name: str             # "Monday", "Tuesday", etc.
    readings_count: int       # Number of readings for this day

    # Morning rush analysis
    rush_start: str           # Time when occupancy increases >5% in 15min (HH:MM)
    rush_end: str             # Time when occupancy stabilizes after peak (HH:MM)
    peak_time: str            # Time of maximum occupancy (HH:MM)

    # Evening rush analysis
    evening_rush_start: str   # Time when occupancy decreases >5% in 15min (HH:MM)
    evening_rush_end: str     # Time when occupancy stabilizes or hits low (HH:MM)

    # Derived metrics
    avg_fill_rate: float      # Average occupancy rate (0.0-1.0)
    avg_work_hours: str       # Typical work hours derived from patterns (e.g., "8:30am - 5:30pm")
    confidence: str           # "high" (28+ days), "moderate" (14-27), "limited" (7-13), "very limited" (1-6)
```

**Storage**: Not persisted directly; computed on-demand from `parking_readings` table.

---

### MorningRecommendation

Arrival time suggestion for a specific day of the week.

```python
@dataclass
class MorningRecommendation:
    """Recommended arrival time for a single day."""
    day_of_week: int          # 0=Monday, 6=Sunday
    day_name: str             # "Monday", "Tuesday", etc.
    recommended_arrival: str  # Recommended arrival time (HH:MM)
    risk_level: str           # "low", "medium", "high" (chance of not finding spot)
    reasoning: str            # Brief explanation for the recommendation
```

**Storage**: Embedded in LLM-generated insight content (not separate table).

---

### DayOfWeekSummary

Container for aggregated day-of-week analysis passed to LLM prompts.

```python
@dataclass
class DayOfWeekSummary:
    """Complete day-of-week analysis for a carpark."""
    carpark: str
    day_patterns: dict[int, DayPattern]  # Keyed by day_of_week (0-6)
    overall: OverallPattern
    data_quality: DataQuality

@dataclass
class OverallPattern:
    """Cross-day aggregated patterns."""
    busiest_day: str          # Day name with highest avg occupancy
    quietest_day: str         # Day name with lowest avg occupancy
    typical_work_hours: str   # Most common work hours pattern

@dataclass
class DataQuality:
    """Data sufficiency indicators."""
    total_days: int           # Number of distinct days with data
    min_days_per_weekday: int # Minimum readings across weekdays
    confidence: str           # Overall confidence level
    gaps: list[str]           # Any notable data gaps
```

**Storage**: Not persisted; computed transiently for prompt construction.

---

## Data Flow

```
parking_readings (SQLite)
        │
        ▼
┌──────────────────────────────────┐
│  prepare_day_of_week_summary()   │  ← New method in InsightsGenerator
│  - Groups by datetime.weekday()  │
│  - Calculates per-day metrics    │
│  - Detects rush hour boundaries  │
└──────────────────────────────────┘
        │
        ▼
   DayOfWeekSummary
        │
        ▼
┌──────────────────────────────────┐
│  _build_prompt() (enhanced)      │  ← Existing method, extended
│  - Routes to type-specific prompt│
│  - morning_recommendation prompt │
│  - commuter_patterns prompt      │
└──────────────────────────────────┘
        │
        ▼
    LLM Response
        │
        ▼
   insights table (existing)
```

## Database Schema

No schema changes required. Existing tables suffice:

### parking_readings (existing)
```sql
CREATE TABLE parking_readings (
    id INTEGER PRIMARY KEY,
    carpark_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    total_spots INTEGER NOT NULL,
    occupancy INTEGER NOT NULL,
    available INTEGER NOT NULL
);
```

### insights (existing)
```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY,
    insight_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    thinking TEXT,
    data_range_start TEXT,
    data_range_end TEXT,
    metadata TEXT,  -- JSON string
    created_at TEXT DEFAULT (datetime('now'))
);
```

New `insight_type` values:
- `"morning_recommendation"` - Day-specific arrival suggestions
- `"commuter_patterns"` - Rush hour and work habit analysis

## Constraints and Validations

| Field | Constraint | Rationale |
|-------|------------|-----------|
| `day_of_week` | 0-6 | Python weekday convention |
| `rush_start` | 05:00-10:00 | Morning detection window |
| `evening_rush_start` | 15:00-20:00 | Evening detection window |
| `confidence` | "high"/"moderate"/"limited"/"very limited" | Based on data days: 28+=high, 14-27=moderate, 7-13=limited, 1-6=very limited |
| `avg_fill_rate` | 0.0-1.0 | Normalized occupancy rate |

## Relationships

```
parking_readings 1───────* DayPattern (computed)
                           │
                           └──* MorningRecommendation (computed)
                           └──* CommuterInsight (stored)
```
