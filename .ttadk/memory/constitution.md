<!--
  ============================================================================
  SYNC IMPACT REPORT
  ============================================================================
  Version Change: 1.0.0 → 1.0.1

  Modified Principles:
    - V. Observable Operations: Removed "Logging MUST include context" requirement

  Added Sections:
    - None

  Removed Sections:
    - None

  Templates Requiring Updates:
    - .ttadk/plugins/ttadk/core/resources/templates/plan-template.md ✅ (no changes needed)
    - .ttadk/plugins/ttadk/core/resources/templates/spec-template.md ✅ (no changes needed)
    - .ttadk/plugins/ttadk/core/resources/templates/tasks-template.md ✅ (no changes needed)
    - .ttadk/plugins/ttadk/core/resources/templates/plan-template-lite.md ✅ (no changes needed)
    - .ttadk/plugins/ttadk/core/resources/templates/spec-template-lite.md ✅ (no changes needed)
    - .ttadk/plugins/ttadk/core/resources/templates/tasks-template-lite.md ✅ (no changes needed)

  Follow-up TODOs:
    - None
  ============================================================================
-->

# Park&Ride Constitution

## Core Principles

### I. Simplicity First

All code MUST be as simple as possible while meeting requirements. Before adding any abstraction,
pattern, or new dependency, ask: "Can this be done with what already exists?"

- Functions MUST do one thing well
- No premature abstractions - wait until the third similar pattern emerges
- Prefer flat structures over nested hierarchies
- Delete code rather than comment it out
- No unused imports, variables, or functions

**Rationale**: A simple codebase is easier to debug, extend, and maintain. Over-engineering
creates cognitive overhead that slows future development.

### II. Data Integrity

Parking data is the core value of this system. All data operations MUST preserve accuracy and
consistency.

- Database writes MUST be atomic with proper error handling
- Calculated fields (e.g., `available = total - occupancy`) MUST be computed consistently
- Timestamps MUST use UTC internally, display local time only in UI
- No silent data loss - all API failures MUST be logged with context
- Retry logic MUST use exponential backoff (current: 5s → 15s → 30s)

**Rationale**: Users depend on accurate parking availability. Corrupted or lost data directly
impacts the usefulness of the system.

### III. Graceful Degradation

The system MUST remain functional even when external dependencies fail.

- API failures MUST NOT crash the application
- LLM failures (Ark/Anthropic) MUST fall back to static messages
- Database sync failures MUST NOT block dashboard operation
- All external calls MUST have timeouts (default: 30s for API, 60s for LLM)

**Rationale**: External services (Transport NSW API, LLM providers) are outside our control.
The dashboard should always show the latest available data, even if updates are delayed.

### IV. Single Source of Truth

Configuration, business logic, and data formats MUST have exactly one canonical definition.

- Carpark name normalization happens in ONE place (`collector.py`)
- Database schema is defined in ONE place (`storage.py`)
- Dashboard configuration lives in ONE file (`dashboard_config.json`)
- Environment variables are the ONLY source for API keys and secrets
- Documentation (CLAUDE.md, TECHNICAL_DESIGN.md) MUST stay synchronized with code

**Rationale**: Duplicate definitions lead to inconsistencies that cause bugs. Changes should
require updating only one location.

### V. Observable Operations

All significant operations MUST be traceable for debugging and monitoring.

- Error logs MUST include enough information to reproduce the issue
- Sync operations MUST log success/failure to `logs/sync.log`
- No silent failures - if something fails, it MUST be logged or reported

**Rationale**: When issues occur in production, observability enables quick diagnosis without
needing to reproduce the problem locally.

## Development Standards

### Code Organization

- **Entry points**: `run_collector.py`, `run_dashboard.py` at repository root
- **Core logic**: `parkride/` package (collector, storage, insights, visualize)
- **Web layer**: `dashboard/` package (Flask app, API routes, static files)
- **Documentation**: `docs/` for technical design, `CLAUDE.md` for quick reference

### Naming Conventions

- Python: snake_case for functions/variables, PascalCase for classes
- Files: lowercase with underscores (e.g., `parking_data.db`)
- API endpoints: lowercase with hyphens (e.g., `/api/insights/latest`)
- CSS classes: lowercase with hyphens (e.g., `.chart-container`)

### Error Handling

- External API calls: try/except with logging and retry
- Database operations: context managers for connection handling
- User-facing errors: friendly messages with actionable guidance
- Internal errors: full stack traces in logs, sanitized messages to UI

## Quality Gates

Before merging to `master`, the following MUST be verified:

1. **Functional**: Core features work (data collection, dashboard display, insights generation)
2. **No regressions**: Existing functionality continues to work
3. **Documentation**: CLAUDE.md and TECHNICAL_DESIGN.md updated if code changed
4. **Spec sync**: If `parkride/` code changed, check corresponding `specs/` for updates
5. **Clean state**: No debug code, no hardcoded secrets, no commented-out blocks

## Fixed Rules

- **Commit**: When user requests to commit code through natural language (e.g., "help me commit",
  "commit changes"), execute `/adk:commit` to stage changes, generate commit messages, and push
  to remote.

- **Code Consistency**: When implementing features, prioritize referencing existing codebase
  patterns, coding styles, and architectural designs. Follow established conventions to maintain
  consistency.

- **Knowledge Search**: When encountering unfamiliar concepts, use `tiksearch` MCP for internal
  documentation and best practices, use `lark-docs` MCP for Lark/Feishu documents.

## Governance

### Amendment Process

1. Propose changes in a feature branch
2. Document rationale for principle changes
3. Update all dependent templates if principle affects them
4. Review with team before merging
5. Increment version according to semantic versioning

### Version Policy

- **MAJOR**: Backward-incompatible governance/principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- PRs MUST be checked against Constitution Check section in plan templates
- Complexity violations MUST be justified in the Complexity Tracking table
- Use `CLAUDE.md` for runtime development guidance

**Version**: 1.0.1 | **Ratified**: 2026-02-05 | **Last Amended**: 2026-02-05
