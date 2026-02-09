# Tasks: Commuter-Focused Parking Insights

**Feature**: `insights-commuter-patterns`
**Input**: Design documents from `/specs/20260205-insights-commuter-patterns/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested in spec - test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Not Required)

**Purpose**: This feature extends existing code - no new project setup needed.

All changes are localized to `parkride/insights.py`. The existing project structure, dependencies, and database schema are sufficient.

**Checkpoint**: ✅ Setup already complete - proceed to Foundational phase.

---

## Phase 2: Foundational (Shared Infrastructure)

**Purpose**: Core methods that BOTH user stories depend on

**⚠️ CRITICAL**: These tasks must complete before User Story 1 or 2 can be implemented.

- [x] T001 [Foundation] Add day-of-week grouping method `prepare_day_of_week_summary()` in `parkride/insights.py`
  - Groups readings by `datetime.weekday()` (0=Monday, 6=Sunday)
  - Returns dict with `day_patterns` keyed by day number
  - Calculates per-day: readings_count, avg_occupancy, peak_time
  - Follows D1 decision from research.md

- [x] T002 [Foundation] Add rush hour detection logic in `parkride/insights.py`
  - Implements algorithm from D2 in research.md
  - Morning rush: detect when occupancy increases >5% in 15min (5:00-10:00)
  - Morning rush end: when occupancy stabilizes (<2% change) after peak
  - Evening rush: detect when occupancy decreases >5% in 15min (15:00-20:00)
  - Evening rush end: when occupancy stabilizes or reaches low point
  - Returns rush_start, rush_end, evening_rush_start, evening_rush_end times

- [x] T003 [Foundation] Add data quality/confidence calculation in `parkride/insights.py`
  - Implements D3 decision from research.md
  - Calculate total distinct days of data
  - Confidence levels: 1-6 days = "very limited", 7-13 days = "limited", 14-27 days = "moderate", 28+ days = "high"
  - Track data gaps and sparse periods
  - Return DataQuality structure with total_days, confidence, gaps
  - **IMPORTANT**: System MUST always return insights regardless of data availability; confidence is informational only

**Checkpoint**: Foundation ready - User Story implementation can begin.

---

## Phase 3: User Story 1 - Morning Arrival Recommendations (Priority: P1) 🎯 MVP

**Goal**: Provide day-specific arrival time recommendations for the 7:30am-9:30am commute window.

**Independent Test**: Request `morning_recommendation` insight for a carpark and verify it contains day-specific arrival time suggestions.

### Implementation for User Story 1

- [x] T004 [US1] Create `morning_recommendation` prompt template in `parkride/insights.py`
  - Add to `_build_prompt()` method using type-specific routing (D4 decision)
  - Include day-by-day data summary in prompt
  - Request: recommended arrival time per day, risk level, reasoning
  - Include confidence level context in prompt

- [x] T005 [US1] Extend `generate_insight()` to handle `morning_recommendation` type in `parkride/insights.py`
  - Call `prepare_day_of_week_summary()` for day-of-week data
  - Pass enhanced summary to `_build_prompt()` with type="morning_recommendation"
  - Add `confidence` and `days_of_data` to response metadata
  - **IMPORTANT**: Never return errors for insufficient data; always generate insight with appropriate confidence level

- [x] T006 [US1] Add "last safe arrival time" calculation per day in `parkride/insights.py`
  - Find when occupancy crosses 90% threshold for each day
  - Calculate average fill-up time per day of week
  - Identify variation to determine confidence per day
  - Include in day_patterns data passed to LLM

- [x] T007 [US1] Handle edge cases for morning_recommendation in `parkride/insights.py`
  - Carpark fills before 7:30am: recommend earlier arrival
  - Carpark never fills (occupancy <80%): note parking is generally available
  - High variance in fill times: provide wider time ranges
  - Missing data for specific days: skip those days with note

**Checkpoint**: User Story 1 complete. Test by calling:
```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "morning_recommendation", "hours": 168, "carpark": "Narrabeen"}'
```
Verify response contains day-specific arrival recommendations (Monday through Sunday).

---

## Phase 4: User Story 2 - Commuter Pattern Analysis (Priority: P2)

**Goal**: Provide rush hour analysis with morning/evening rush periods (start AND end times) to understand local work habits.

**Independent Test**: Request `commuter_patterns` insight and verify it describes morning rush (start + end), evening rush (start + end), and typical work hours.

### Implementation for User Story 2

- [x] T008 [US2] Create `commuter_patterns` prompt template in `parkride/insights.py`
  - Add to `_build_prompt()` method for type="commuter_patterns"
  - Include rush hour boundaries (morning start/end, evening start/end)
  - Request: narrative description, rush periods, typical work hours
  - Emphasize single-carpark analysis (no cross-comparison by default, per FR-005b)

- [x] T009 [US2] Extend `generate_insight()` to handle `commuter_patterns` type in `parkride/insights.py`
  - Call `prepare_day_of_week_summary()` with rush detection
  - Include overall patterns (busiest day, quietest day)
  - Derive typical work hours from morning arrival + evening departure
  - Add weekday vs weekend breakdown

- [x] T010 [US2] Calculate derived metrics for commuter patterns in `parkride/insights.py`
  - Busiest day: day with highest average occupancy
  - Quietest day: day with lowest average occupancy
  - Typical work hours: derived from average morning arrival peak and evening departure start
  - Week-over-week trend (if enough data)

- [x] T011 [US2] Handle edge cases for commuter_patterns in `parkride/insights.py`
  - No weekend data: skip weekend patterns, note in response
  - Carpark always empty or always full: note atypical pattern
  - Data gaps during rush hours: calculate confidence based on density
  - **IMPORTANT**: Always generate insight regardless of data availability; use "very limited" confidence for <7 days

**Checkpoint**: User Story 2 complete. Test by calling:
```bash
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "commuter_patterns", "hours": 336, "carpark": "Narrabeen"}'
```
Verify response contains morning rush (start + end), evening rush (start + end), and typical work hours.

---

## Phase 5: Dashboard Frontend Integration

**Purpose**: Expose new insight types in the dashboard UI (FR-011, FR-012, FR-013)

- [x] T014 [Frontend] Add insight type dropdown to Generate Insights button in `dashboard/static/js/dashboard.js`
  - Add a `<select>` dropdown with options: Daily Summary, Morning Recommendation, Commuter Patterns
  - Default selection: Daily Summary (preserves existing behavior)
  - Pass selected type as `type` parameter in the POST request to `/api/insights/generate`

- [x] T015 [Frontend] Pass selected carpark to insight generation in `dashboard/static/js/dashboard.js`
  - When `morning_recommendation` or `commuter_patterns` is selected, include current carpark filter as `carpark` parameter
  - If no single carpark is selected, show inline message: "Please select a specific carpark first" and prevent request
  - `daily_summary` does not require carpark selection (existing behavior)

- [x] T016 [Frontend] Validate frontend integration end-to-end
  - Test dropdown appears and defaults to Daily Summary
  - Test Morning Recommendation with a carpark selected
  - Test Commuter Patterns with a carpark selected
  - Test inline error message when no carpark is filtered

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [x] T012 [P] Validate quickstart.md scenarios work end-to-end
  - Run both curl commands from quickstart.md
  - Verify responses match expected format
  - Check error handling for insufficient data

- [x] T013 [P] Update CLAUDE.md with new insight types
  - Add `morning_recommendation` and `commuter_patterns` to Business Logic section
  - Document day-of-week analysis feature

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)       ─── N/A (existing project)
         │
         ▼
Phase 2 (Foundation)  ─── T001, T002, T003 (sequential, same file)
         │
         ├────────────────────────────┐
         ▼                            ▼
Phase 3 (US1: P1)               Phase 4 (US2: P2)
T004 → T005 → T006 → T007       T008 → T009 → T010 → T011
         │                            │
         └────────────────────────────┘
                    │
                    ▼
         Phase 5 (Frontend)
         T014 → T015 → T016
                    │
                    ▼
         Phase 6 (Polish)
         T012 [P], T013 [P]
```

### Task Dependencies

| Task | Depends On | Blocks |
|------|------------|--------|
| T001 | - | T002, T004, T008 |
| T002 | T001 | T003, T005, T009 |
| T003 | T002 | T005, T009 |
| T004 | T001 | T005 |
| T005 | T002, T003, T004 | T006 |
| T006 | T005 | T007 |
| T007 | T006 | T014 |
| T008 | T001, T002 | T009 |
| T009 | T002, T003, T008 | T010 |
| T010 | T009 | T011 |
| T011 | T010 | T014 |
| T014 | T007, T011 | T015 |
| T015 | T014 | T016 |
| T016 | T015 | T012 |
| T012 | T016 | - |
| T013 | T007, T011 | - |

### Parallel Opportunities

**Within Phase 2**: None - all tasks modify same methods in same file

**After Phase 2 completes**: US1 and US2 can be worked in parallel by different developers (but add different prompts to same method, so coordination needed)

**Phase 5 (Frontend)**: Sequential - T014 → T015 → T016 (same file)

**Phase 6**: T012 and T013 can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundation (T001-T003)
2. Complete Phase 3: User Story 1 (T004-T007)
3. **STOP and VALIDATE**: Test morning_recommendation independently
4. Deploy if ready - users can start getting arrival recommendations

### Full Feature (Both User Stories + Frontend)

1. Complete Phase 2: Foundation (T001-T003)
2. Complete Phase 3: User Story 1 (T004-T007)
3. Complete Phase 4: User Story 2 (T008-T011)
4. Complete Phase 5: Frontend Integration (T014-T016)
5. Complete Phase 6: Polish (T012-T013)
6. Full feature validation

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 16 |
| **Foundational Tasks** | 3 (T001-T003) |
| **User Story 1 Tasks** | 4 (T004-T007) |
| **User Story 2 Tasks** | 4 (T008-T011) |
| **Frontend Tasks** | 3 (T014-T016) |
| **Polish Tasks** | 2 (T012-T013) |
| **Parallel Opportunities** | Phase 6 (T012, T013) |
| **Primary Files Modified** | `parkride/insights.py`, `dashboard/static/js/dashboard.js` |
| **Suggested MVP** | Phase 2 + Phase 3 (7 tasks) |

---

## Notes

- All tasks modify `parkride/insights.py` - sequential execution recommended
- No database schema changes needed
- API endpoint unchanged - new types passed via existing `type` parameter
- Existing tests: None (project uses manual testing)
- Commit after each logical task group
