---
description: Generate comprehensive Technical Design Document (TDD) based on existing feature specifications and design artifacts. Creates detailed technical documentation following ByteDance engineering standards.

---

## User Input

```text
$ARGUMENTS
```
You **MUST** consider the user input before proceeding (if not empty).

If the given `$ARGUMENTS` contains a link, you need to read the content of the link (use lark-docs mcp if it's a lark doc) and replace the link with content.

## Context

**Read context before Executing**:

1. **Language Setting**
   - Read `preferred_language` from `.ttadk/config.json` (default: 'en' if missing)
   - **IMPORTANT**: Use the configured language for ALL outputs: 'en' → English, 'zh' → Chinese
   - This applies to: generated documents, interactive prompts, confirmations, status messages, and error descriptions

2. **Reference Setting**
   - Load tech stack references from plan.md's Technical Context section. Use these references for technical design decisions and architecture patterns.

## Outline

1. **Setup**: Run `node .ttadk/plugins/ttadk/core/resources/scripts/check-prerequisites.js --json` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. All paths must be absolute.

2. **Load design artifacts**: Read all available documents from FEATURE_DIR:
   - **Primary sources**: spec.md, plan.md, data-model.md, research.md
   - **Secondary sources**: contracts/, checklists/, quickstart.md, tasks.md, any other .md files
   - **Note**: Only focus on documents within the spec directory, no need to search external database schema files

3. **Load template**: Load `.ttadk/plugins/ttadk/core/resources/templates/technical-design-template.md` to understand the required structure and sections.

4. **Generate TDD**: Follow the template structure to generate comprehensive technical documentation. **IMPORTANT**: `FEATURE_DIR/technical-design.md` will be created or updated (upsert mode - no need to ask user for confirmation).
   - **Business Background**: Extract from spec.md, plan.md, research.md
   - **Feature Module Division**: Extract from spec.md, plan.md with priority levels (P0/P1/P2)
   - **Detailed Design**:
     - Overall Architecture - Use **Mermaid** graph/C4 diagram, highlight changes in red
     - Business Flow Diagram - Use **Mermaid** flowchart
     - Sequence Diagram - Use **Mermaid** sequenceDiagram
     - State Diagram - Optional, use **Mermaid** stateDiagram-v2
     - Domain Model / ER Diagram - Optional, use **Mermaid** erDiagram
     - Core Changes - Include diff blocks with `🔴 Change:` comments
     - Interface Definitions (API/RPC) - Include IDL definitions, request/response examples
     - Schema Definitions - DB tables, MQ messages, cache, TCC configs
   - **TODO List**: Organize by Development/Testing/Release with priority markers

5. **Write output**: Save to `FEATURE_DIR/technical-design.md` (create or overwrite)

6. **Self-check Mermaid diagrams**: Before finalizing, review ALL Mermaid code blocks in the generated document:
   - ✅ All node text is quoted: `A["Text"]`
   - ✅ Only use allowed arrows: `-->`, `-.->`, `==>`
   - ✅ Arrow labels are simple (no `[]`, `<>`, special chars)
   - ✅ No forbidden syntax: `-,->`, `--x`, `--o`, `-x`
   - ✅ Subgraph names have no brackets: `subgraph Title` not `subgraph Name[Text]`
   - ✅ ER diagram decimal fields: `decimal` not `decimal(10,2)`
   - If any issues found, FIX them before writing the file

7. **Report completion**: Output summary with:
   - Output file path
   - Documentation sections completed (✓ or ⚠ To be supplemented)
   - Data sources used
   - Mermaid diagram validation status (✓ All diagrams validated)
   - Next steps

## Key Rules

### Documentation Principles

1. **Template Structure is Fixed**: DO NOT modify section order, merge sections, or add/remove top-level sections
2. **Source Prioritization**: data-model.md > plan.md > spec.md (always document which source was used)
3. **Completeness**: Generate ALL sections in template, use "⚠ To be supplemented" markers for insufficient information
4. **Diagram Tool Selection**:
   - **Use ONLY Mermaid** for all diagrams: Architecture (graph/C4), flow diagrams (flowchart), sequence diagrams (sequenceDiagram), state diagrams (stateDiagram-v2), ER diagrams (erDiagram)
5. **Language Consistency**: Respect language setting for ALL text output

### Critical Diagram Rules

**USE ONLY MERMAID** for all diagrams in this document. All diagram rules below apply to Mermaid syntax only.

**Target Version: Mermaid 9.1.x** - Use only basic, widely-supported syntax

**Mermaid Flowchart Syntax** (Use `graph` keyword, NOT `flowchart`):

```
graph TD
    A["Node 1"]
    B["Node 2"]
    A --> B
```

**Basic Rules**:
- **Always quote node text**: `A["Text"]`, `B["中文文本"]`
- **Arrow types** (CRITICAL - only these 3 types):
  - `-->` : Solid arrow (normal flow)
  - `-.->` : Dotted arrow (optional/async flow)
  - `==>` : Thick arrow (emphasis)
  - ❌ **FORBIDDEN**: `-,->`, `--x`, `--o`, `-x` (these will cause syntax errors)
- **Arrow labels must be simple**:
  - ✅ Correct: `A -->|Label| B`, `A -.->|旧链路| B`
  - ❌ Wrong: `A -,->|[旧链路]| B` - brackets `[]` cause errors
  - ❌ Wrong: `A -->|<br/>| B` - HTML tags cause errors
  - **Rule**: Labels can ONLY contain letters, numbers, Chinese, spaces, and basic punctuation (`,`, `.`, `-`)
- **Node shapes**:
  - Rectangle: `A["Text"]`
  - Rounded: `A("Text")`
  - Circle: `A(("Text"))`
  - Diamond: `A{"Decision"}`
- **Graph direction**: `graph TD` (top-down) or `graph LR` (left-right)
- **Subgraph syntax** (avoid if possible, use only when necessary):
  ```
  graph TD
      subgraph Title
          A["Node"]
      end
  ```
  - ❌ **DO NOT use brackets in subgraph name**: `subgraph Name[Text]` is WRONG
  - ✅ **Use simple text**: `subgraph Title` or `subgraph "Title with spaces"`
  - Keep subgraphs simple or avoid them entirely

**Mermaid SequenceDiagram Syntax**:

```
sequenceDiagram
    participant A as Client
    participant B as Server
    A->>B: Request
    B-->>A: Response
```

**Basic Rules**:
- Use `participant` to define actors with aliases
- Arrow types: `->>` (solid), `-->>` (dotted)
- Keep message text simple

**Mermaid ER Diagram Syntax**:

```
erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id
        string name
    }
    ORDER {
        int order_id
        decimal amount
    }
```

**Basic Rules**:
- For `decimal`: Use `decimal` without parameters (avoid `decimal(10,2)`)
- For `varchar`: Use `string` type
- Relationship: `||--o{` (one-to-many), `||--||` (one-to-one)

**Mermaid StateDiagram Syntax**:

```
stateDiagram-v2
    [*] --> State1
    State1 --> State2
    State2 --> [*]
```

**Basic Rules**:
- Use `stateDiagram-v2` keyword
- Simple state transitions with `-->`
- Use `[*]` for start/end states

**Highlight Changes**:
- Apply styles AFTER diagram: `style NodeName fill:#ff6b6b`

### Change Documentation

1. **Diff Format**: Use `-` and `+`, add `-- 🔴 Change: <explanation>` for key changes
2. **Rollback Planning**: Always include rollback mechanism (prefer config switches)
3. **Monitoring**: Document key metrics (API latency, success rate, error count)

### Error Handling

1. **No design artifacts found**: ERROR "Cannot generate TDD without at least spec.md or plan.md. Please run `/adk:specify` first."
2. **Insufficient information**: Generate skeleton with "⚠ To be supplemented: Insufficient information, need to add XXX details"
3. **Invalid diagram syntax**:
   - Run self-check on all Mermaid code blocks before writing file
   - Common issues to fix:
     - Unquoted node text → Add quotes: `A[Text]` → `A["Text"]`
     - Wrong arrow syntax → Replace: `-,->` → `-.->`, `--x` → `-->`
     - Complex labels → Simplify: `[旧链路]` → `旧链路`, `<br/>` → remove
     - Subgraph brackets → Remove: `subgraph Name[Text]` → `subgraph Name`
   - If syntax cannot be simplified, use text description instead of diagram
4. **Conflicting information**: Prioritize data-model.md > plan.md > spec.md, document conflict in notes

## Template Sections Reference

The `technical-design-template.md` provides detailed examples and formatting for:
- Priority markers (🔴 P0, 🟠 P1, 🟡 P2)
- Architecture diagram options (Layered/Component/Deployment) using Mermaid
- Sequence diagram syntax using Mermaid sequenceDiagram
- ER diagram format using Mermaid erDiagram
- Flowchart syntax using Mermaid flowchart
- State diagram syntax using Mermaid stateDiagram-v2
- API/RPC interface tables with IDL definitions
- Schema definition tables (DB/MQ/Cache/TCC)
- TODO list organization by category and priority

Refer to the template for concrete examples of each section's expected format and content.

## Success Criteria

✅ All required sections present (Business Background, Modules, Architecture, Flow, Sequence, Changes, Interfaces, Schemas, TODO)
✅ At least one valid Mermaid diagram per required section (correct Mermaid syntax with quoted special characters)
✅ Core changes documented with diff blocks and rollback plans
✅ Consistency between Feature Modules and Core Changes sections
✅ All cross-references accurate (file paths, table names, API endpoints)
✅ Language setting respected throughout document
✅ Clear marking of "To be supplemented" sections where information is insufficient
✅ Completion summary report generated with data source checklist

## Important Notes

1. **Incremental Updates**: If TDD needs adjustment after generation, use `/adk:clarify` or `/adkl:revise` to update design documents first
2. **Team Collaboration**: TDD is meant for team technical review - encourage feedback
3. **Living Document**: Regenerate TDD from source documents when major design changes occur
4. **No Manual Edits**: Don't manually edit technical-design.md without updating source documents

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated technical-design.md is correct and meets expectations.

**If needs adjustment**:
- Regular workflow → Run `/adk:clarify [feedback]`
- Lite workflow → Run `/adkl:revise [feedback]`

### Step 2 - Next Step Recommendation
Once technical design is confirmed and satisfactory:

**Regular workflow**:
- If `tasks.md` does NOT exist → Execute `/adk:tasks`
- If `tasks.md` exists → Execute `/adk:implement`

**Lite workflow**:
- Execute `/adkl:apply`
