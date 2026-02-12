# Feature Specification: Parking Anomaly Detection Insight

**Feature**: `20260212-parking-anomaly-detect`
**Created**: 2026-02-12
**Status**: Draft
**Input**: User description: "I want to add one more insight type. This insight is used to find out abnormal patterns in the past 30 days. It can be based on one selected car park or all carparks. When I select one carpark, you need to compare the data of that carpark with previous data to see where there are abnormalities. You need to define what's abnormal first."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Anomaly Detection Insight for Single Carpark (Priority: P1)

As a system operator or commuter, I want to generate an anomaly detection insight for a specific carpark to identify unusual parking patterns over the past 30 days compared to its historical baseline.

**What constitutes "abnormal"** (Definition - as required by user input):
The system defines abnormality through statistical deviation from established patterns:

1. **Occupancy Rate Anomaly**: A reading where occupancy deviates more than 2 standard deviations from the same time slot's historical mean (same day-of-week, same hour) AND the absolute deviation exceeds 60% from the baseline mean. This dual threshold prevents false positives with limited baseline data.
2. **Fill Time Anomaly**: When the carpark reaches 90% capacity significantly earlier or later (>30 minutes) than the historical average for that day-of-week.
3. **Pattern Shift Anomaly**: When the day's overall occupancy pattern (morning rush start/end, peak time) differs significantly from the historical norm.
4. **Sudden Spike/Drop**: An occupancy change of >20% within a 30-minute window when historical data shows <5% change for that period.
5. **Weekend/Weekday Inversion**: Weekend showing weekday-like patterns or vice versa.

**Why this priority**: Core functionality - detecting anomalies for a single carpark is the primary use case that provides actionable insights to operators investigating specific facilities. This directly addresses the user requirement: "When I select one carpark, you need to compare the data of that carpark with previous data to see where there are abnormalities."

**Technical Implementation**:

- Add new insight type: `anomaly_detection`
- Default analysis window: 720 hours (30 days) of historical data as specified in user input
- Scope: Single carpark (carpark parameter required)
- Baseline calculation:
  - Full data (≥30 days): Use first 21 days to establish baseline, analyze last 9 days for anomalies
  - Limited data (<30 days): Use oldest 7 days as baseline, analyze remaining days for anomalies
- Anomaly detection algorithm:
  1. Group readings by (day_of_week, hour) to create time-slot baselines
  2. Calculate mean and standard deviation for each time slot
  3. Flag readings where current value > mean + 2*stddev or < mean - 2*stddev
  4. Aggregate anomalies by type and severity
- Output: List of detected anomalies with timestamps, type, severity, and deviation magnitude
- Integration with existing `InsightsGenerator.generate_insight()` method
- New method: `prepare_anomaly_summary()` in insights.py
- LLM prompt to interpret anomalies and provide natural language explanation

**Independent Test**: Can be fully tested by calling `generate_insight(insight_type="anomaly_detection", carpark="Narrabeen")` and verifying it returns detected anomalies with explanations.

**Acceptance Scenarios**:

1. **Given** a carpark with 30 days of data, **When** I generate an anomaly_detection insight for that carpark, **Then** the system identifies and lists any occupancy anomalies with timestamps and severity levels.
2. **Given** a carpark with consistent historical patterns, **When** a sudden spike occurs on a specific day, **Then** the system flags it as a "sudden spike anomaly" with the exact timestamp and magnitude.
3. **Given** a carpark with no anomalies in the past 30 days, **When** I generate an anomaly_detection insight, **Then** the system returns a "no anomalies detected" message with confidence level.

---

### User Story 2 - Generate Anomaly Detection Insight for All Carparks (Priority: P2)

As a system operator, I want to generate an anomaly detection insight across all carparks to identify system-wide unusual patterns and compare carpark behaviors.

This addresses the user requirement: "It can be based on one selected car park or all carparks."

**Why this priority**: Extends P1 functionality to provide a holistic view across the network, useful for identifying regional issues or events affecting multiple facilities.

**Technical Implementation**:

- Same insight type: `anomaly_detection` with carpark=None (all carparks)
- Analysis approach:
  1. Run anomaly detection for each carpark individually
  2. Identify common anomalies (same timestamp/date affecting multiple carparks)
  3. Rank carparks by anomaly frequency/severity
  4. Detect correlated anomalies (multiple carparks showing same pattern deviation)
- Output includes:
  - Per-carpark anomaly summary
  - Cross-carpark correlation analysis
  - System-wide anomaly events (e.g., "3 carparks showed unusual activity on Feb 5")
- LLM prompt to synthesize findings across all carparks

**Independent Test**: Can be fully tested by calling `generate_insight(insight_type="anomaly_detection", carpark=None)` and verifying it returns cross-carpark analysis.

**Acceptance Scenarios**:

1. **Given** 30 days of data across multiple carparks, **When** I generate an anomaly_detection insight without specifying a carpark, **Then** the system analyzes all carparks and identifies both individual and correlated anomalies.
2. **Given** an external event causing unusual patterns at multiple carparks, **When** I run anomaly detection, **Then** the system identifies and groups these as a correlated system-wide anomaly.

---

### User Story 3 - MCP Server Integration for Anomaly Detection (Priority: P3)

As an LLM agent user, I want to access anomaly detection insights through the MCP server to enable automated monitoring and alerting.

**Why this priority**: Enables AI-powered monitoring workflows and integration with other systems, consistent with existing MCP integration for other insight types.

**Technical Implementation**:

- Add `parkride_generate_insight` MCP tool support for `type="anomaly_detection"`
- Parameters: `type`, `hours` (default 720), `carpark` (optional)
- Returns JSON with:
  - `anomalies`: List of detected anomalies
  - `summary`: Natural language summary from LLM
  - `confidence`: Data quality confidence level
  - `metadata`: Analysis parameters and carpark list

**Independent Test**: Can be fully tested by calling the MCP tool `parkride_generate_insight(type="anomaly_detection")` and verifying JSON response.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** I call `parkride_generate_insight` with `type="anomaly_detection"`, **Then** it returns a properly formatted JSON response with anomaly data.

---

### Edge Cases

- What happens when historical data is less than 30 days? → Use oldest 7 days as baseline, analyze remaining days. Return "limited" confidence with note about reduced baseline period.
- What happens when historical data is less than 7 days? → Return "very limited" confidence with warning that baseline cannot be established; provide general guidance only.
- How does system handle carparks with sporadic data collection? → Use available data points, note gaps in analysis, adjust statistical thresholds.
- What if a carpark has no anomalies? → Return positive confirmation with confidence level.
- What happens when all readings are anomalous (e.g., construction closure)? → Detect as "pattern shift" rather than individual anomalies, suggest data quality review.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a new insight type `anomaly_detection` in `generate_insight()`.
- **FR-002**: System MUST analyze the past 30 days (720 hours) of data by default for anomaly detection (as specified: "past 30 days").
- **FR-003**: System MUST accept an optional `carpark` parameter; when provided, analyze only that carpark; when None, analyze all carparks (as specified: "based on one selected car park or all carparks").
- **FR-004**: System MUST define abnormality based on BOTH statistical deviation (>2 standard deviations from time-slot baseline) AND absolute deviation (>60% from baseline mean) - addressing the requirement: "You need to define what's abnormal first." The dual threshold prevents false positives when baseline variance is low due to limited data.
- **FR-005**: System MUST detect the following anomaly types: occupancy rate anomaly, fill time anomaly, pattern shift anomaly, sudden spike/drop, weekend/weekday inversion.
- **FR-006**: System MUST return detected anomalies with: timestamp, type, severity level (low/medium/high), deviation magnitude.
- **FR-007**: System MUST generate a natural language explanation of anomalies using LLM (Ark → Anthropic fallback, consistent with existing insight types).
- **FR-008**: System MUST include confidence level based on data quality (same as existing: very limited, limited, moderate, high).
- **FR-009**: System MUST gracefully handle insufficient data: when <30 days available, use oldest 7 days as baseline; when <7 days, provide general guidance with "very limited" confidence.
- **FR-010**: System MUST persist generated anomaly insights to the database via `save_insight()`.
- **FR-011**: System MUST compare carpark data "with previous data" as specified - baseline is established from historical readings.
- **FR-012**: System MUST filter out invalid data readings where occupancy rate >100% or <0% (sensor errors) before anomaly detection.
- **FR-013**: System MUST expose `anomaly_detection` in the web dashboard UI insight type dropdown, consistent with existing insight types.
- **FR-014**: System MUST include specific date and time (e.g., "Feb 10 at 17:00") for each anomaly mentioned in the LLM-generated insight summary.

### Key Entities

- **Anomaly**: Represents a detected abnormal pattern with attributes: timestamp, carpark, anomaly_type, severity, deviation_value, baseline_value, description.
- **AnomalySummary**: Aggregates anomalies for a carpark with attributes: carpark, total_anomalies, anomalies_by_type, anomalies_by_severity, time_range.
- **TimeSlotBaseline**: Statistical baseline for a (day_of_week, hour) combination with attributes: day_of_week, hour, mean_occupancy_rate, std_deviation, sample_count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate anomaly detection insights within 10 seconds for a single carpark with 30 days of data.
- **SC-002**: System correctly identifies >90% of injected test anomalies (validated through test cases).
- **SC-003**: False positive rate is <10% (anomalies flagged that are within normal variation).
- **SC-004**: LLM-generated explanations are understandable and actionable in >80% of cases (qualitative).
- **SC-005**: Anomaly detection works for all existing carparks in the database without errors.

## Clarifications

### Session 2026-02-12

- Q: How to handle baseline calculation when historical data is less than 30 days? → A: Use the oldest 7 days of data as baseline.
- Q: Should anomaly_detection be available in the web dashboard UI? → A: Yes, add it to the insight type dropdown like the existing insight types (morning_recommendation, commuter_patterns).
- Q: Should anomaly timestamps be included in the insight summary? → A: Yes, always include specific date and time for each anomaly mentioned in the LLM-generated insight.

## Assumptions

- Historical data is available for at least 7 days for meaningful baseline calculation (clarified from original 14 days).
- Data collection frequency is consistent enough to calculate meaningful time-slot statistics.
- The dual threshold (2-sigma z-score AND 50% absolute deviation) provides robust anomaly detection that works well with limited baseline data.
- Existing LLM fallback chain (Ark → Anthropic → static) applies to anomaly interpretation.
