# Research: Parking Anomaly Detection

**Feature**: `20260212-parking-anomaly-detect`
**Date**: 2026-02-12

## Research Questions

### R1: Statistical Anomaly Detection Approach

**Question**: What statistical method should be used to detect anomalies without external ML libraries?

**Decision**: Z-score based anomaly detection (2-sigma threshold)

**Rationale**:
- Simple to implement with Python standard library (no numpy required, use `statistics` module)
- Well-understood statistical method with predictable behavior
- Existing codebase already uses similar statistical calculations in `_calculate_safe_arrival()`
- Threshold (2 standard deviations) is configurable if tuning needed

**Alternatives Considered**:
1. **IQR (Interquartile Range)**: More robust to outliers but requires sorting, slightly more complex
2. **MAD (Median Absolute Deviation)**: More robust than mean-based but less intuitive threshold interpretation
3. **External ML (scikit-learn Isolation Forest)**: Too heavy dependency for simple use case

**Implementation**:
```python
from statistics import mean, stdev

def is_anomaly(value: float, baseline_values: list[float], threshold: float = 2.0) -> tuple[bool, float]:
    """Check if value is anomalous based on z-score."""
    if len(baseline_values) < 3:  # Need minimum samples for stdev
        return False, 0.0

    avg = mean(baseline_values)
    sd = stdev(baseline_values)
    if sd == 0:
        return False, 0.0

    z_score = (value - avg) / sd
    return abs(z_score) > threshold, z_score
```

---

### R2: Baseline Period Strategy

**Question**: How to split data into baseline vs analysis periods?

**Decision**: Adaptive baseline based on available data

**Rationale**:
- User clarified: if <30 days, use oldest 7 days as baseline
- This ensures enough baseline data for meaningful statistics while maximizing analysis window
- Matches existing pattern in `_calculate_data_quality()` confidence levels

**Algorithm**:
```
if total_days >= 30:
    baseline_period = first 21 days
    analysis_period = last 9 days
elif total_days >= 7:
    baseline_period = first 7 days
    analysis_period = remaining days
else:
    confidence = "very limited"
    return general guidance (no statistical analysis)
```

---

### R3: Time-Slot Grouping Strategy

**Question**: How to group readings for baseline calculation?

**Decision**: Group by (day_of_week, hour) tuple

**Rationale**:
- Parking patterns are highly periodic (weekday vs weekend, rush hour vs off-peak)
- Existing `DayPattern` dataclass already groups by day_of_week
- Hourly granularity captures rush hour patterns without over-fitting to minute-level noise
- ~168 time slots per week (7 days × 24 hours) provides sufficient granularity

**Trade-off**:
- Finer granularity (30-min slots) would catch more subtle patterns but require more data
- Coarser granularity (day only) would miss rush hour anomalies

---

### R4: Anomaly Severity Classification

**Question**: How to categorize anomaly severity?

**Decision**: Three-tier severity based on deviation magnitude

| Severity | Threshold | Description |
|----------|-----------|-------------|
| Low | 2.0 ≤ \|z\| < 2.5 | Notable deviation, may warrant monitoring |
| Medium | 2.5 ≤ \|z\| < 3.0 | Significant anomaly, likely actionable |
| High | \|z\| ≥ 3.0 | Severe anomaly, requires attention |

**Rationale**:
- 2-sigma is industry standard for "unusual" (covers ~95% of normal distribution)
- 3-sigma is "rare" (covers ~99.7%)
- Three tiers provide actionable differentiation without over-complicating

---

### R5: Cross-Carpark Correlation Detection

**Question**: How to detect correlated anomalies across multiple carparks?

**Decision**: Date-based clustering of anomalies

**Algorithm**:
1. Collect all anomalies across all carparks
2. Group anomalies by date
3. If 2+ carparks show anomalies on same date → flag as "correlated anomaly"
4. Describe common pattern in LLM prompt

**Rationale**:
- Simple approach that captures external events (holidays, major events, road closures)
- No need for complex correlation coefficients
- Aligns with user expectation of "compare the data of that carpark with previous data"

---

## Best Practices Applied

### From Existing Codebase (`insights.py`)

1. **Dataclass Pattern**: Use `@dataclass` for structured data (following `DayPattern`, `DataQuality`, `OverallPattern`)
2. **Method Naming**: `prepare_*_summary()` for data preparation, `_build_*_prompt()` for LLM prompts
3. **Confidence Levels**: Reuse existing confidence scale ("very limited", "limited", "moderate", "high")
4. **Graceful Degradation**: Always return something useful, even with limited data
5. **LLM Prompt Format**: Use `TITLE:` and `CONTENT:` markers for response parsing

### From Constitution

1. **Simplicity First**: Use Python stdlib `statistics` module, no external ML libraries
2. **Single Source of Truth**: All anomaly logic in `insights.py`, no duplicate calculations
3. **Data Integrity**: Read-only analysis, existing data untouched
4. **Observable Operations**: Store metadata with confidence levels and data quality indicators
