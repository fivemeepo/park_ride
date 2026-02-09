# Feature Specification: Commuter-Focused Parking Insights

**Feature**: `insights-commuter-patterns`
**Created**: 2026-02-05
**Status**: Draft
**Input**: User description for enhancing the current "insights" function to serve commuters

## Clarifications

### Session 2026-02-05
- Q: For evening pattern analysis, what specifically should be measured? → A: Analyze when commuters return to pick up their car (evening departure pattern)
- Q: Should the commuter patterns insight support cross-suburb comparison? → A: No cross-carpark comparison by default; only compare when explicitly requested
- Q: What time details should be included for rush periods? → A: Both start AND end times for morning rush and evening rush periods
- Q: How should the system handle data with less than 7 days of history? → A: Output limited conclusions with confidence warnings; NEVER return errors or refuse to generate insights

### Session 2026-02-06
- Q: How should new insight types be triggered from the dashboard UI? → A: Add a dropdown/selector to the existing "Generate Insights" button to choose insight type
- Q: How should the carpark be determined for carpark-specific insight types? → A: Use the currently selected/filtered carpark from the dashboard chart view
- Q: What happens when no single carpark is selected and a commuter insight type is chosen? → A: Show an inline message prompting the user to select a specific carpark first
- Q: Should the insight type dropdown auto-set the hours parameter? → A: No, keep hours control independent; user sets both type and hours manually

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Morning Arrival Recommendations (Priority: P1)

A commuter needs to go to office in the morning between 7:30am~9:30am. They need to find a parking spot and want actionable suggestions from the insights about **when** they should arrive to get a spot. The recommendation strategy should be **different for each day of the week** (Monday to Sunday) since commuting patterns vary by day.

**Why this priority**: This is the primary user need - the commuter wants to know "when should I leave home to get a parking spot?" This directly solves their daily problem and provides immediate value.

**Technical Implementation**:

1. **Data Analysis Requirements**:
   - Analyze historical data by day of week (Mon-Sun separately)
   - Focus on the 7:30am-9:30am window (morning commute period)
   - Track when spots become scarce (occupancy crosses threshold, e.g., >90%)
   - Identify the "last safe arrival time" for each day

2. **Pattern Detection**:
   - Calculate average fill-up time per day of week
   - Identify variation/standard deviation to give confidence levels
   - Detect if Monday is typically busier than Friday, etc.

3. **Output Format** (LLM prompt enhancement):
   - Day-specific recommendations: "On Mondays, arrive before 7:45am"
   - Confidence indication: "Based on 4 weeks of data, this is consistent"
   - Risk assessment: "Arriving at 8:00am on Tuesday has 70% chance of finding a spot"

4. **Existing Code Modifications**:
   - Enhance `InsightsGenerator._build_prompt()` in `parkride/insights.py` to include day-of-week breakdown
   - Add new data aggregation in `prepare_data_summary()` for per-day stats
   - Add new `insight_type`: `morning_recommendation`

**Independent Test**: Can be fully tested by generating a "morning_recommendation" insight for a specific carpark and verifying it contains day-specific arrival time suggestions.

**Acceptance Scenarios**:

1. **Given** at least 7 days of parking data for a carpark, **When** user requests a morning recommendation insight, **Then** the insight contains specific arrival time recommendations for each day of the week.

2. **Given** data shows Monday fills up by 7:50am and Friday by 8:30am, **When** user requests insight, **Then** Monday recommendation is earlier than Friday recommendation.

3. **Given** insufficient data (less than 7 days), **When** user requests insight, **Then** system provides available recommendations with a note about limited data confidence.

---

### User Story 2 - Commuter Pattern Analysis (Priority: P2)

The user is curious about the commuting patterns at the carpark. They want to understand when people start commuting in that area. The carpark is built by the government for commuters and is free to use, so the patterns reflect local commuter behavior.

**Why this priority**: This provides context and understanding to the user, helping them make informed decisions beyond just "when to arrive." It satisfies curiosity and builds trust in the system.

**Technical Implementation**:

1. **Pattern Metrics to Calculate**:
   - "Rush hour start": When occupancy begins climbing rapidly (e.g., >5% increase in 15 min)
   - "Peak time": When carpark reaches maximum occupancy
   - "Rush hour end": When occupancy stabilizes or starts declining
   - "Evening departure pattern": When commuters return to pick up their cars (occupancy starts dropping)
   - "Evening rush start": When occupancy begins declining rapidly (e.g., >5% decrease in 15 min)
   - "Evening rush end": When carpark is mostly empty or decline stabilizes
   - "Typical work hours": Derived from morning arrival + evening departure (reflects local work habits)

2. **Day-of-Week Breakdown**:
   - Weekday vs weekend patterns
   - Individual day patterns if significantly different
   - Holiday detection (if applicable)

3. **Trend Analysis**:
   - Week-over-week comparison
   - Is the carpark getting busier over time?
   - Seasonal patterns (if enough historical data)

4. **Output Format**:
   - Narrative description: "Commuters in this area typically start arriving around 6:45am and leave around 5:30pm..."
   - **Morning rush period**: Start time AND end time (e.g., "Morning rush: 7:00am - 8:30am")
   - **Evening rush period**: Start time AND end time (e.g., "Evening rush: 5:00pm - 6:30pm")
   - Key statistics: Peak time, fill-up duration, typical emptying time, average work hours
   - Visualization-ready data points (for potential future charting)
   - **Note**: Single carpark analysis by default. Cross-suburb comparison only when explicitly requested.

5. **Existing Code Modifications**:
   - Add new `insight_type`: `commuter_patterns` in `parkride/insights.py`
   - Enhance `prepare_data_summary()` with rush hour detection
   - Calculate rate of change metrics (spots filled per minute)

**Independent Test**: Can be fully tested by generating a "commuter_patterns" insight and verifying it describes when commuters start arriving, when they return to pick up their cars, and what typical work hours look like in that suburb.

**Acceptance Scenarios**:

1. **Given** historical parking data, **When** user requests commuter pattern insight, **Then** the insight describes when morning rush hour starts AND ends.

2. **Given** weekday data shows different pattern from weekend, **When** insight is generated, **Then** weekday and weekend patterns are described separately.

3. **Given** historical parking data for a carpark, **When** user requests commuter pattern insight, **Then** the insight includes evening rush period with both start AND end times.

4. **Given** user requests commuter pattern insight for a single carpark, **When** insight is generated, **Then** no cross-carpark comparison is included unless explicitly requested.

---

### Edge Cases

- **Insufficient data**: Less than 7 days of data - MUST still provide best-effort analysis with confidence warning; system MUST NOT return errors or refuse to generate insights. Even 1 day of data should produce limited conclusions.
- **Data gaps**: Missing readings during critical hours - note the gap and adjust recommendations
- **Carpark always full**: If carpark fills before 7:30am consistently, recommend alternative strategies (e.g., "consider arriving before 7:00am")
- **Carpark never fills**: If occupancy never exceeds 80%, note that parking is generally available
- **Inconsistent patterns**: High variance in fill times - provide wider time ranges with lower confidence
- **Weekend vs weekday**: Handle carparks that may be unused on weekends (government commuter carparks)
- **No carpark selected**: If user selects `morning_recommendation` or `commuter_patterns` without a specific carpark filtered, show an inline message prompting them to select a carpark first

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST analyze parking data by day of week (Monday through Sunday separately)
- **FR-002**: System MUST identify the morning rush period (7:30am-9:30am) fill-up patterns
- **FR-003**: System MUST provide day-specific arrival time recommendations
- **FR-004**: System MUST detect when commuters start arriving (morning rush start time) AND when morning rush ends
- **FR-005**: System MUST detect peak occupancy times
- **FR-005a**: System MUST detect evening rush period with both start AND end times (when commuters return to pick up cars)
- **FR-005b**: System MUST NOT include cross-carpark comparison by default; comparison only when explicitly requested
- **FR-006**: System MUST work with the existing LLM integration (Ark primary, Anthropic fallback)
- **FR-007**: System MUST handle insufficient data gracefully by providing limited conclusions with appropriate confidence warnings; system MUST NOT return errors or refuse to generate insights regardless of data availability
- **FR-008**: System MUST support carpark-specific analysis (single carpark filter)
- **FR-009**: System MUST store generated insights in the existing `insights` table
- **FR-010**: System MUST expose new insight types via the existing `/api/insights/generate` endpoint
- **FR-011**: Dashboard MUST provide a dropdown/selector on the "Generate Insights" button allowing users to choose between `morning_recommendation` and `commuter_patterns` insight types
- **FR-012**: For carpark-specific insight types (`morning_recommendation`, `commuter_patterns`), the dashboard MUST use the currently selected/filtered carpark from the chart view as the `carpark` parameter
- **FR-013**: The insight type dropdown and existing hours/time range control MUST remain independent; selecting an insight type MUST NOT auto-change the hours parameter

### Key Entities

- **DayPattern**: Aggregated statistics for a specific day of week (day_of_week, avg_fill_time, peak_time, rush_start, rush_end, evening_rush_start, evening_rush_end, avg_work_hours, confidence_level)
- **MorningRecommendation**: Arrival time suggestion per day (day_of_week, recommended_arrival, risk_level, reasoning)
- **CommuterInsight**: Enhanced insight with pattern data (existing insight fields + day_patterns, rush_hour_analysis)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can request a "morning_recommendation" insight and receive day-specific arrival suggestions
- **SC-002**: Recommendations differ by day of week when historical data shows different patterns
- **SC-003**: Users can request a "commuter_patterns" insight and understand when commuters start arriving AND when morning rush ends
- **SC-003a**: Commuter pattern insight includes evening rush period (start AND end times) to understand work habits
- **SC-003b**: Commuter pattern insight analyzes single carpark by default without cross-carpark comparison
- **SC-004**: Insights include confidence indicators based on data availability
- **SC-005**: System handles edge cases (insufficient data, always full, never full) with appropriate messaging
