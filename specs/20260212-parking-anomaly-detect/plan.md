# Implementation Plan: Parking Anomaly Detection Insight

**Feature**: `20260212-parking-anomaly-detect` | **Date**: 2026-02-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/20260212-parking-anomaly-detect/spec.md`

## Summary

Add a new `anomaly_detection` insight type to the Park&Ride system that identifies abnormal parking patterns over a 30-day window. The feature uses statistical analysis (2-sigma deviation from time-slot baselines) to detect 5 anomaly types: occupancy rate anomalies, fill time anomalies, pattern shifts, sudden spikes/drops, and weekend/weekday inversions. Supports both single carpark and cross-carpark analysis with LLM-generated explanations.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Flask, SQLite3, httpx, openai (for Ark), anthropic
**Storage**: SQLite (`parking_data.db` with `parking_readings` and `insights` tables)
**Testing**: pytest (manual testing via CLI and MCP inspector)
**Target Platform**: macOS/Linux server
**Project Type**: single
**Performance Goals**: Generate insight within 10 seconds for single carpark with 30 days of data
**Constraints**: Minimal dependencies, graceful LLM fallback, no external ML libraries
**Scale/Scope**: ~5 carparks, ~30 days of data per carpark, ~4000 readings per carpark

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Extends existing `InsightsGenerator` class, reuses patterns from `morning_recommendation` and `commuter_patterns` |
| II. Data Integrity | PASS | Read-only analysis of existing data, no new writes except insight storage |
| III. Graceful Degradation | PASS | Uses existing LLM fallback chain (Ark → Anthropic → static) |
| IV. Single Source of Truth | PASS | Anomaly logic in `insights.py`, consistent with existing insight types |
| V. Observable Operations | PASS | Insights stored with metadata including confidence level |

**All gates pass. No violations to justify.**

## Project Structure

### Documentation (this feature)

```
specs/20260212-parking-anomaly-detect/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (from /adk:tasks)
```

### Source Code (repository root)

```
parkride/
├── insights.py          # ADD: prepare_anomaly_summary(), _build_anomaly_detection_prompt(), new dataclasses
├── storage.py           # NO CHANGES (existing insert_insight supports new type)
└── collector.py         # NO CHANGES

dashboard/
├── api.py               # NO CHANGES (existing /api/insights/generate handles new type)
└── static/              # NO CHANGES

mcp_server.py            # UPDATE: Add anomaly_detection to parkride_generate_insight docstring
```

**Structure Decision**: Single project structure. Feature adds to existing `parkride/insights.py` module, following the established pattern for `morning_recommendation` and `commuter_patterns` insight types.

## Complexity Tracking

*No violations - table not needed*
