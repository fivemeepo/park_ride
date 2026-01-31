---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.

---

## User Input

```text
$ARGUMENTS
```
You **MUST** consider the user input before proceeding (if not empty).

If the given `$ARGUMENTS` contains a link, you need to read the content of the link (use lark-docs mcp if it's a lark doc) and replace the link with content.

## Context
**Read context before Executing**:
1. Language Setting
   - Read `preferred_language` from `.ttadk/config.json` (default: 'en' if missing). **IMPORTANT** **Use the configured language for ALL outputs: 'en' → English, 'zh' → 中文. This applies to: generated documents (specs, plans, tasks), interactive prompts, confirmations, status messages, and error descriptions.** 


## Outline

1. **Setup**: Run `node .ttadk/plugins/ttadk/core/resources/scripts/setup-plan.js --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, FEATURE_NAME.

2. **Load context**: Read FEATURE_SPEC and `.ttadk/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
    - Fill Technical Context section:
      * **CRITICAL**: Keep all field names in ENGLISH (Language/Version, Primary Dependencies, Storage, Testing, Target Platform, Project Type, Performance Goals, Constraints, Scale/Scope)
      * **REASON**: The update-agent-context.js script parses these English field names to extract tech stack information
      * **DO NOT translate field names** even if preferred_language is 'zh' - only translate the values/descriptions
      * Mark unknowns as "NEEDS CLARIFICATION"
    - Fill Constitution Check section from constitution
    - Evaluate gates (ERROR if violations unjustified)
    - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
    - Phase 1: Generate data-model.md, contracts/, quickstart.md
    - Phase 1: **Save all files to disk, then** update agent context by running the agent script
    - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report feature name, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
    - For each NEEDS CLARIFICATION → research task
    - For each dependency → best practices task
    - For each integration → patterns task

2. **Generate and dispatch research agents**:
    ```
    For each unknown in Technical Context:
    Task: "Research {unknown} for {feature context}"
    For each technology choice:
    Task: "Find best practices for {tech} in {domain}"
    ```

3. **Consolidate findings** in `research.md` using format:
    - Decision: [what was chosen]
    - Rationale: [why chosen]
    - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
    - Entity name, fields, relationships
    - Validation rules from requirements
    - State transitions if applicable

2. **Generate API contracts** from functional requirements:
    - For each user action → endpoint
    - Use standard REST/GraphQL patterns
    - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
    - **CRITICAL**: Ensure plan.md is completely written and saved to disk BEFORE running this script
    - The script reads Technical Context from plan.md file (not from memory/buffer)
    - Wait for file system write to complete (use Edit/Write tool completion)
    - Then run: `node .ttadk/plugins/ttadk/core/resources/scripts/update-agent-context.js claude`
    - These scripts detect which AI agent is in use
    - Update the appropriate agent-specific context file
    - Add only new technology from current plan
    - Preserve manual additions between markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated plan.md is correct and the technical approach is sound.

**If needs adjustment**: Run `/adk:clarify [feedback]` to refine the plan.

### Step 2 - Next Step Recommendation
Once plan is confirmed and satisfactory:

**Create Task Breakdown**: Execute `/adk:tasks` to generate the detailed task breakdown based on the implementation plan.
