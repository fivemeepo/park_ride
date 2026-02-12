# Tasks: Parking Anomaly Detection Insight

**Input**: Design documents from `/specs/20260212-parking-anomaly-detect/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in spec - tests are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `parkride/`, `dashboard/`, `mcp_server.py` at repository root
- All anomaly logic goes in `parkride/insights.py` (following existing patterns)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No setup required - existing project structure supports new feature

This feature extends existing infrastructure. No new setup tasks needed.

**Checkpoint**: Setup complete - proceed to foundational tasks

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core dataclasses and utility functions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T001 [P] [Foundation] Add `Anomaly` dataclass to `parkride/insights.py`
  - Fields: timestamp, carpark, anomaly_type, severity, z_score, actual_value, baseline_mean, baseline_std, description
  - Import from dataclasses, add after existing DayPattern class

- [x] T002 [P] [Foundation] Add `TimeSlotBaseline` dataclass to `parkride/insights.py`
  - Fields: day_of_week, hour, mean_occupancy_rate, std_deviation, sample_count
  - Add after Anomaly dataclass

- [x] T003 [Foundation] Add `AnomalySummary` dataclass to `parkride/insights.py`
  - Fields: carpark, analysis_start, analysis_end, baseline_start, baseline_end, anomalies, total_readings_analyzed, anomaly_count, anomalies_by_type, anomalies_by_severity, data_quality
  - Depends on T001, T002 (references Anomaly and existing DataQuality)

- [x] T004 [Foundation] Add `_calculate_z_score()` helper method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_calculate_z_score(self, value: float, mean: float, std: float) -> float`
  - Use Python stdlib `statistics` module
  - Cap z-score at ±10 to avoid floating point issues
  - Return 0.0 if std == 0

- [x] T005 [Foundation] Add `_get_severity()` helper method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_get_severity(self, z_score: float) -> str`
  - Returns: "low" (2.0-2.5), "medium" (2.5-3.0), "high" (≥3.0)
  - Based on absolute value of z_score

- [x] T006 [Foundation] Add `_calculate_time_slot_baselines()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_calculate_time_slot_baselines(self, readings: list[dict], baseline_end: datetime) -> dict[tuple[int, int], TimeSlotBaseline]`
  - Groups readings by (day_of_week, hour), filters to baseline period
  - Calculates mean and stdev for each time slot
  - Returns dict keyed by (day_of_week, hour) tuple

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Single Carpark Anomaly Detection (Priority: P1) 🎯 MVP

**Goal**: Generate anomaly detection insight for a specific carpark, identifying unusual patterns over 30 days

**Independent Test**: Call `generate_insight(insight_type="anomaly_detection", hours=720, carpark="Narrabeen")` and verify it returns anomalies with explanations

### Implementation for User Story 1

- [x] T007 [US1] Add `_detect_occupancy_rate_anomalies()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_detect_occupancy_rate_anomalies(self, readings: list[dict], baselines: dict, total_spots: int, carpark: str) -> list[Anomaly]`
  - For each reading in analysis period, calculate z-score vs baseline
  - Flag if |z| > 2.0, create Anomaly with severity from `_get_severity()`

- [x] T008 [US1] Add `_detect_sudden_changes()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_detect_sudden_changes(self, readings: list[dict], total_spots: int, carpark: str) -> list[Anomaly]`
  - Look for >20% occupancy change in 30-minute windows
  - Create "sudden_spike" or "sudden_drop" anomalies (always "high" severity)

- [x] T009 [US1] Add `prepare_anomaly_summary()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `prepare_anomaly_summary(self, hours: int = 720, carpark: Optional[str] = None) -> Optional[AnomalySummary]`
  - Load readings, split into baseline (first 21 days or 7 days if <30) and analysis periods
  - Call `_calculate_time_slot_baselines()`, `_detect_occupancy_rate_anomalies()`, `_detect_sudden_changes()`
  - Aggregate anomalies into AnomalySummary
  - Handle insufficient data (<7 days) gracefully

- [x] T010 [US1] Add `_build_anomaly_detection_prompt()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_build_anomaly_detection_prompt(self, data_summary: dict, anomaly_summary: AnomalySummary) -> str`
  - Format anomaly list for LLM interpretation
  - Include carpark name, analysis period, anomaly count by type/severity
  - Request TITLE: and CONTENT: format (consistent with existing prompts)

- [x] T011 [US1] Update `generate_insight()` method in `parkride/insights.py` to handle `insight_type="anomaly_detection"`
  - Add condition: `if insight_type == "anomaly_detection":`
  - Call `prepare_anomaly_summary()` to get anomaly data
  - Call `_build_anomaly_detection_prompt()` to build LLM prompt
  - If no anomalies, generate "no anomalies detected" message
  - Build metadata with anomaly_count, anomalies_by_type, anomalies_by_severity, baseline_period, analysis_period

- [x] T012 [US1] Add `_generate_limited_anomaly_insight()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_generate_limited_anomaly_insight(self, hours: int, carpark: str, data_summary: dict) -> dict`
  - Handle case when <7 days of data (cannot establish baseline)
  - Return "very limited" confidence with general guidance
  - Follow pattern from existing `_generate_limited_data_insight()`

**Checkpoint**: User Story 1 complete - single carpark anomaly detection works independently

---

## Phase 4: User Story 2 - All Carparks Anomaly Detection (Priority: P2)

**Goal**: Generate cross-carpark anomaly analysis identifying system-wide patterns

**Independent Test**: Call `generate_insight(insight_type="anomaly_detection", hours=720, carpark=None)` and verify it returns per-carpark summaries and correlated events

### Implementation for User Story 2

- [x] T013 [P] [US2] Add `CrossCarparkAnalysis` dataclass to `parkride/insights.py`
  - Fields: carpark_summaries (dict[str, AnomalySummary]), correlated_events (list[dict]), most_anomalous_carpark (Optional[str]), system_wide_patterns (list[str])
  - Add after AnomalySummary dataclass

- [x] T014 [US2] Add `_detect_correlated_events()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_detect_correlated_events(self, carpark_summaries: dict[str, AnomalySummary]) -> list[dict]`
  - Group anomalies by date across all carparks
  - If 2+ carparks have anomalies on same date, flag as correlated event
  - Return list of {date, carparks, anomaly_types, description}

- [x] T015 [US2] Add `prepare_cross_carpark_analysis()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `prepare_cross_carpark_analysis(self, hours: int = 720) -> CrossCarparkAnalysis`
  - Get all carparks from `db.get_available_carparks()`
  - Call `prepare_anomaly_summary()` for each carpark
  - Call `_detect_correlated_events()` to find system-wide patterns
  - Identify most anomalous carpark (highest anomaly count)

- [x] T016 [US2] Add `_build_cross_carpark_prompt()` method to `InsightsGenerator` in `parkride/insights.py`
  - Signature: `_build_cross_carpark_prompt(self, data_summary: dict, analysis: CrossCarparkAnalysis) -> str`
  - Format per-carpark summaries and correlated events for LLM
  - Request synthesis of system-wide patterns
  - Request TITLE: and CONTENT: format

- [x] T017 [US2] Update `generate_insight()` in `parkride/insights.py` to handle all-carparks mode
  - In the `if insight_type == "anomaly_detection":` block
  - If `carpark is None`: call `prepare_cross_carpark_analysis()`
  - Use `_build_cross_carpark_prompt()` for LLM prompt
  - Include all carparks in metadata

**Checkpoint**: User Story 2 complete - cross-carpark analysis works independently

---

## Phase 5: User Story 3 - MCP Server Integration (Priority: P3)

**Goal**: Update MCP server docstring to document the new anomaly_detection type

**Independent Test**: Run MCP inspector, call `parkride_generate_insight(type="anomaly_detection", hours=720)` and verify JSON response

### Implementation for User Story 3

- [x] T018 [US3] Update `parkride_generate_insight()` docstring in `mcp_server.py`
  - Add "anomaly_detection" to the type parameter description
  - Document default hours=720 (30 days) for anomaly detection
  - Mention that it detects abnormal patterns compared to baseline
  - No code changes needed (existing API already passes type through to dashboard)

**Checkpoint**: All user stories complete - full feature is functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and validation

- [x] T019 [P] [Polish] Update `CLAUDE.md` insight types documentation
  - Add `anomaly_detection` to the insight types list in Business Logic section
  - Document the baseline calculation rules (21 days for ≥30 days, 7 days for <30)

- [x] T020 [P] [Polish] Update `docs/TECHNICAL_DESIGN.md` (if exists) with anomaly detection details
  - Add new dataclasses to data model section
  - Document the 5 anomaly types and their detection criteria

- [x] T021 [Polish] Run quickstart.md validation
  - Execute the examples from `specs/20260212-parking-anomaly-detect/quickstart.md`
  - Verify single carpark and all-carparks modes work
  - Verify edge cases (limited data, no anomalies) are handled

- [x] T022 [US3] Add `anomaly_detection` to dashboard UI insight type dropdown
  - Update `dashboard/templates/index.html` to add "Anomaly Detection" option
  - Follows existing pattern for morning_recommendation and commuter_patterns

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks - existing infrastructure
- **Foundational (Phase 2)**: T001-T006 - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational AND User Story 1 (reuses `prepare_anomaly_summary()`)
- **User Story 3 (Phase 5)**: Depends on User Stories 1 & 2 (documents the feature)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core single-carpark functionality
- **User Story 2 (P2)**: Depends on US1 (`prepare_anomaly_summary()` is reused per-carpark)
- **User Story 3 (P3)**: Depends on US1 & US2 (documents complete feature)

### Within Each Phase

**Foundational (Phase 2)**:
- T001, T002 can run in parallel [P]
- T003 depends on T001, T002
- T004, T005 can run in parallel (no dependencies)
- T006 depends on T002

**User Story 1 (Phase 3)**:
- T007, T008 can run after T004-T006 (parallel within story)
- T009 depends on T007, T008
- T010 depends on T009
- T011 depends on T010
- T012 can be done after T011 (handles edge case)

### Parallel Opportunities

```
Phase 2 (parallel):
  T001 ──┐
  T002 ──┼──► T003
         │
  T004 ──┼──► (standalone)
  T005 ──┼──► (standalone)
  T002 ──┴──► T006

Phase 3 (after Phase 2):
  T007 ──┐
  T008 ──┴──► T009 ──► T010 ──► T011 ──► T012

Phase 4 (after Phase 3):
  T013 (parallel with T014-T017)
  T014 ──► T015 ──► T016 ──► T017

Phase 5 (after Phase 4):
  T018 (standalone)

Phase 6 (after all):
  T019, T020 [P] ──► T021
```

---

## Parallel Example: Foundational Phase

```bash
# Launch parallel dataclass creation:
Task: "Add Anomaly dataclass to parkride/insights.py"
Task: "Add TimeSlotBaseline dataclass to parkride/insights.py"

# After both complete, add AnomalySummary:
Task: "Add AnomalySummary dataclass to parkride/insights.py"

# Launch parallel helper methods:
Task: "Add _calculate_z_score() helper method"
Task: "Add _get_severity() helper method"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T006)
2. Complete Phase 3: User Story 1 (T007-T012)
3. **STOP and VALIDATE**: Test with `generate_insight(insight_type="anomaly_detection", carpark="Narrabeen")`
4. Single carpark anomaly detection is fully functional

### Incremental Delivery

1. Foundational → dataclasses and helpers ready
2. Add User Story 1 → Single carpark works (MVP!)
3. Add User Story 2 → Cross-carpark analysis works
4. Add User Story 3 → MCP documentation complete
5. Polish → Full documentation and validation

---

## Notes

- All code changes are in `parkride/insights.py` (except T018 in `mcp_server.py`)
- No database schema changes required (existing `insights` table works)
- No REST API changes required (existing `/api/insights/generate` handles new type)
- Follow existing code patterns in `insights.py` (DayPattern, DataQuality, etc.)
- Use `statistics` module from Python stdlib (no external ML libraries)
- Commit after each task or logical group
