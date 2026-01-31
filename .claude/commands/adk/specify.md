---
description: "Create or update the feature specification from a natural language feature description."

---

## User Input

```text
$ARGUMENTS
```
You **MUST** consider the user input before proceeding (if not empty).

If the given `$ARGUMENTS` contains a link, you need to read the content of the link. For lark/feishu doc URLs, export it via lark-docs MCP with `outputDir` set to `specs/` directory, then read the exported markdown content to understand the feature requirements.

**Preserve References**: If user input contains local references (images, files, diagrams, etc.), preserve these references in spec.md with paths adjusted to remain valid from spec.md location. Read referenced content to understand context, but maintain reference format rather than forcing content embedding.

## Context
**Read context before Executing**:
1. Language Setting
   - Read `preferred_language` from `.ttadk/config.json` (default: 'en' if missing). **IMPORTANT** **Use the configured language for ALL outputs: 'en' → English, 'zh' → 中文. This applies to: generated documents (specs, plans, tasks), interactive prompts, confirmations, status messages, and error descriptions.**


## Outline

The text the user typed after `/adk:specify` in the triggering message **is** the feature description. Assume you always have it available in this conversation even if `$ARGUMENTS` appears literally below. Do not ask the user to repeat it unless they provided an empty command.

Given that feature description, do this:

1. Get feature name and setup feature directory:
- Analyze the feature description and extract key concepts (actors, actions, outcomes)
- Create a concise 3-part name in format: "part1-part2-part3"
  - Each part should be 2-10 characters, lowercase, alphanumeric with hyphens
  - Focus on: domain-action-outcome or subject-verb-object pattern
  - Examples: "user-auth-login", "payment-refund-process", "data-export-csv"
- Run `node .ttadk/plugins/ttadk/core/resources/scripts/create-new-feature.js "<generated-name>" --json` from repo root, replacing `<generated-name>` with the name you created above.
- This script generates a feature name (YYYYMMDD-description format), creates `specs/{feature-name}/` directory, and copies spec.md template.
- Parse the JSON output to get FEATURE_DIR and SPEC_FILE path.

2. Load `.ttadk/plugins/ttadk/core/resources/templates/spec-template.md` to understand required sections.

3. Follow this execution flow:

    1. Parse user description from Input
        If empty: ERROR "No feature description provided"
    2. Extract key concepts from description
        - **CRITICAL - Completeness Guarantee**: The final spec.md MUST be a superset of user input (spec.md >= user input). Every line of information from user input must be traceable in spec.md. If it exists in user input, it MUST exist in spec.md. This includes all references to local resources (code blocks, images, files, diagrams) - preserve these references so they remain findable in spec.md.
        - Identify: actors, actions, data, constraints, technical implementation details, etc.
    3. For unclear aspects:
        - Make informed guesses based on context and industry standards
        - Only mark with [NEEDS CLARIFICATION: specific question] if:
          - The choice significantly impacts feature scope or user experience
          - Multiple reasonable interpretations exist with different implications
          - No reasonable default exists
        - **LIMIT: Maximum 10 [NEEDS CLARIFICATION] markers total**
        - Prioritize clarifications by impact: technical correctness > business logic > edge cases
    4. Fill User Scenarios & Testing section
        - If no clear user flow: ERROR "Cannot determine user scenarios"
        - For each user story, fill in all fields including **Technical Implementation** section
        - **Technical Implementation**: Extract complete implementation details from user input (implementation flow, interface design, model design, data tables, pseudo code, code modifications, configuration, diagrams, local file references, etc.)
    5. Generate Functional Requirements
        Each requirement must be testable
        Use reasonable defaults for unspecified details (document assumptions in Assumptions section)
    6. Define Success Criteria
        Create measurable, technology-agnostic outcomes
        Include both quantitative metrics (time, performance, volume) and qualitative measures (user satisfaction, task completion)
        Each criterion must be verifiable without implementation details
    7. Identify Key Entities (if data involved)
    8. Return: SUCCESS (spec ready for planning)

4. Write the specification to SPEC_FILE using the template structure:
   - **CRITICAL**: Preserve ALL information from source document - nothing should be lost
   - Replace placeholders with concrete details from user input
   - Preserve section order and headings
   - **If lark doc was exported**: When filling the `Input` field in spec.md, include both the original URL and the local file path. Calculate the correct relative path based on feature directory depth:
     - For simple feature (e.g., `20250107-feature`): `specs/20250107-feature/spec.md` → `../doc_export/file.md`
     - The feature directory is always a single level under `specs/`
     - Example: `**Input**: https://bytedance.larkoffice.com/wiki/xxx (local copy: [filename.md](../doc_export/file.md))`

5. **Specification Quality Validation**: After writing the initial spec, validate it against quality criteria:

    a. **Create Spec Quality Checklist**: Generate a checklist file at `FEATURE_DIR/checklists/requirements.md` using the checklist template structure with these validation items:

    ```markdown
    # Specification Quality Checklist: [FEATURE NAME]

    **Purpose**: Validate specification completeness and quality before proceeding to planning
    **Created**: [DATE]
    **Feature**: [Link to spec.md]

    ## Content Quality

    - [ ] All user stories from source document are captured
    - [ ] Technical implementation details are preserved for each story
    - [ ] All mandatory sections completed
    - [ ] No information lost from source document
    - [ ] **Completeness check (CRITICAL)**: spec.md >= user input. For every line in user input, verify it has a corresponding entry in spec.md. All references (code blocks, images, local files) from user input must be findable in spec.md

    ## Requirement Completeness

    - [ ] No [NEEDS CLARIFICATION] markers remain
    - [ ] Requirements are testable and unambiguous
    - [ ] Success criteria are measurable
    - [ ] All acceptance scenarios are defined
    - [ ] Edge cases are identified
    - [ ] Scope is clearly bounded
    - [ ] Dependencies and assumptions identified

    ## Feature Readiness

    - [ ] All functional requirements have clear acceptance criteria
    - [ ] User scenarios cover primary flows
    - [ ] Success criteria are defined

    ## Notes

    - Items marked incomplete require spec updates before `/adk:clarify` or `/adk:plan`
    ```

    b. **Run Validation Check**: Review the spec against each checklist item:
    - For each item, determine if it passes or fails
    - **For completeness check**: Review user input ($ARGUMENTS) side by side with spec.md, verify every piece of information appears in spec (descriptions, requirements, technical details, all references, code examples, etc.)
    - Document specific issues found (quote relevant spec sections)

    c. **Handle Validation Results**:

    - **If all items pass**: Mark checklist complete and proceed to step 6

    - **If items fail (excluding [NEEDS CLARIFICATION])**:
        1. List the failing items and specific issues
        2. Update the spec to address each issue
        3. Re-run validation until all items pass (max 3 iterations)
        4. If still failing after 3 iterations, document remaining issues in checklist notes and warn user

    - **If [NEEDS CLARIFICATION] markers remain**:
        1. Extract all [NEEDS CLARIFICATION: ...] markers from the spec
        2. **LIMIT CHECK**: If more than 10 markers exist, keep only the 10 most critical (by technical correctness/business logic/edge case impact) and make reasonable inferences for the rest
        3. For each clarification needed (max 10), present options to user in this format:

            ```markdown
            ## Question [N]: [Topic]

            **Context**: [Quote relevant spec section]

            **What we need to know**: [Specific question from NEEDS CLARIFICATION marker]

            **Suggested Answers**:

            | Option | Answer | Implications |
            |--------|--------|--------------|
            | A      | [First suggested answer] | [What this means for the feature] |
            | B      | [Second suggested answer] | [What this means for the feature] |
            | C      | [Third suggested answer] | [What this means for the feature] |
            | Custom | Provide your own answer | [Explain how to provide custom input] |

            **Your choice**: _[Wait for user response]_
            ```

        4. **CRITICAL - Table Formatting**: Ensure markdown tables are properly formatted:
            - Use consistent spacing with pipes aligned
            - Each cell should have spaces around content: `| Content |` not `|Content|`
            - Header separator must have at least 3 dashes: `|--------|`
            - Test that the table renders correctly in markdown preview
        5. Number questions sequentially (Q1, Q2, ... up to Q10 max)
        6. Present all questions together before waiting for responses
        7. Wait for user to respond with their choices for all questions (e.g., "Q1: A, Q2: Custom - [details], Q3: B")
        8. Update the spec by replacing each [NEEDS CLARIFICATION] marker with the user's selected or provided answer
        9. Re-run validation after all clarifications are resolved

    d. **Update Checklist**: After each validation iteration, update the checklist file with current pass/fail status

6. Report completion with feature name, spec file path, checklist results, and readiness for the next phase (`/adk:clarify` or `/adk:plan`).

**NOTE:** The script generates a feature name in YYYYMMDD-description format and initializes the spec file before writing.

## General Guidelines

- Focus on **extracting and preserving** ALL details from user input
- **CRITICAL - Completeness Guarantee**: spec.md MUST be a superset of user input. If any information exists in user input, it MUST be findable in spec.md. This applies to every line, every reference (code blocks, images, local files), and every detail. After generation, verify: for any content in user input, you can locate its corresponding entry in spec.md.
- Technical implementation details are REQUIRED in each user story
- **Local references**: Preserve references from user input (images, files, etc.) with adjusted paths valid from spec.md location. Read referenced content to understand context, but keep reference format rather than forcing inline embedding.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation

When creating this spec from a user prompt:

1. **Preserve all details**: Extract and preserve ALL information from source document - nothing should be lost
2. **Organize into template**: Format the extracted information into the template structure
3. **Technical Implementation is key**: Each user story's Technical Implementation section should contain complete implementation details
4. **Limit clarifications**: Maximum 10 [NEEDS CLARIFICATION] markers - use only for genuinely unclear points:
    - Ambiguous technical specifications
    - Missing key information
    - Conflicting requirements
5. **Prioritize clarifications**: technical correctness > business logic > edge cases
6. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
7. **Common areas needing clarification** (only if no reasonable default exists):
    - Feature scope and boundaries (include/exclude specific use cases)
    - Technical implementation conflicts or ambiguities
    - Data model and interface design decisions
8. **Local references**: Preserve references from source (images, code files, diagrams) with paths adjusted for spec.md location. Keep reference format; read content for understanding but don't force embedding.

### Success Criteria Guidelines

Success criteria must be:

1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **User-focused**: Describe outcomes from user/business perspective
3. **Verifiable**: Can be tested/validated

**Good examples**:

- "Users can complete checkout in under 3 minutes"
- "System supports 10,000 concurrent users"
- "95% of searches return results in under 1 second"
- "Task completion rate improves by 40%"

**Bad examples** (implementation-focused):

- "API response time is under 200ms" (too technical, use "Users see results instantly")
- "Database can handle 1000 TPS" (implementation detail, use user-facing metric)
- "React components render efficiently" (framework-specific)
- "Redis cache hit rate above 80%" (technology-specific)

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated spec.md is correct and captures all requirements.

**If needs adjustment**: Run `/adk:clarify [feedback]` to refine the specification.

### Step 2 - Next Step Recommendation
Once spec is confirmed and satisfactory:

**Create Implementation Plan**: Execute `/adk:plan` to generate the technical implementation plan based on the specification.
