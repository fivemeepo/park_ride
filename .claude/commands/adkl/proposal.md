---
description: propose new features based on existing code and draft specifications/plans/task documents.

---

## User Input

```text
$ARGUMENTS
```
You **MUST** consider the user input before proceeding (if not empty).

If the given `$ARGUMENTS` contains a link, you need to read the content of the link. For lark/feishu doc URLs, export it via lark-docs MCP with `outputDir` set to `specs/` directory, then read the exported markdown content to understand the feature requirements.

**Preserve References**: If user input contains local references (images, files, diagrams, etc.), preserve these references in spec.md with paths adjusted to remain valid from spec.md location. Read referenced content to understand context, but maintain reference format rather than forcing content embedding.

## Phase

- ### **Phase 1: Context & Environment Setup**

  **Objective:** Gather all necessary context and configure the environment.

  1.  **Set Language:**
      - Read `.ttadk/config.json` to determine `preferred_language`.
      - Default to 'en' if the file or key is missing.
      - **Crucially, all subsequent outputs MUST be in this language.**
  2.  **Load Core Instructions:**
      - Read `.ttadk/memory/constitution.md`.
      - These are your guiding principles. Adhere to them strictly.
  3.  **Analyze User Request (`$ARGUMENTS`):**
      - If `$ARGUMENTS` contains a URL (e.g., a Lark document), fetch its full content and use that as the primary input.
      - Carefully parse the final text to understand the core feature requirements.
  ---

  ### **Phase 2: Analysis & Planning**

  **Objective:** Bridge the user's request with the current state of the codebase.

  1.  **Initial Investigation:**
      - Use tools like `rg` and `ls` to explore the codebase related to the feature request.
      - **Goal:** Understand the current implementation, identify potential areas for modification, and note any knowledge gaps.

  2.  **Clarification (Interactive Step):**
      - **If the request is ambiguous, incomplete, or conflicts with existing code:**
          - Formulate specific, targeted questions for the user.
          - **Do not proceed until you receive clarification.** This prevents rework and ensures alignment.

  3.  **Check for Duplicates:**
      - Before creating new requirements, search for similar or overlapping features in the archive:
        `rg -n "ARCHIVE:|{feature-name-keyword}:" specs/archived`
      - If a similar feature exists, notify the user and ask whether to modify it or create a new one.

  ---

  ### **Phase 3: Document Generation**

  **Objective:** Create the feature specification, implementation plan, and task breakdown.

  1.  **Get Feature Name & Setup Files:**
      - Analyze the feature description and extract key concepts (actors, actions, outcomes)
      - Create a concise 3-part name in format: "part1-part2-part3"
        - Each part should be 2-10 characters, lowercase, alphanumeric with hyphens
        - Focus on: domain-action-outcome or subject-verb-object pattern
        - Examples: "user-auth-login", "payment-refund-process", "data-export-csv"
      - Run `node .ttadk/plugins/ttadk/core/resources/scripts/create-new-feature-lite.js "<generated-name>" --json` from repo root, replacing `<generated-name>` with the name you created above.
      - This script generates a feature name (YYYYMMDD-description format), creates `specs/{feature-name}/` directory, and copies template files (spec.md, plan.md, tasks.md).
      - Parse the JSON output to get FEATURE_DIR and file paths.

  2.  **Draft Feature Specification (`spec.md`):**
      - Load the `spec.md`.
      - **CRITICAL - Completeness Guarantee**: The final spec.md MUST be a superset of user input (spec.md >= user input). Every line of information from user input must be traceable in spec.md. If it exists in user input, it MUST exist in spec.md. This includes all references to local resources (code blocks, images, files, diagrams) - preserve these references so they remain findable in spec.md.
      - Fill in all placeholders based on user input:
        - For each User Story, fill in all fields including **Technical Implementation** section
        - **Technical Implementation**: Extract complete implementation details from user input (implementation flow, interface design, model design, data tables, pseudo code, code modifications, configuration, diagrams, local file references, etc.)
      - Maintain the original section order.
      - **If lark doc was exported**: When filling the `Input` field in spec.md, include both the original URL and the local file path. The relative path from spec.md to doc_export is always `../doc_export/` since feature directories are single-level under `specs/`.
        - Example: `**Input**: https://bytedance.larkoffice.com/wiki/xxx (local copy: [filename.md](../doc_export/file.md))`
      - **Completeness Validation**: Review user input ($ARGUMENTS) side by side with generated spec.md. Verify every piece of information appears in spec.md (descriptions, requirements, technical details, all references, code examples, etc.). If anything is missing, update spec.md before proceeding.

  3.  **Draft Implementation Plan (`plan.md`):**
      - Load the `plan.md`.
      - Based on the `spec.md` and your codebase investigation, devise a concrete technical solution.
      - Detail the "how": specify which files to create/modify, what classes or functions to add, and any key technical decisions.
      - Adhere to the project's existing architecture and best practices.
      - **CRITICAL - Technical Context Section**:
        * Keep all field names in ENGLISH (Language/Version, Primary Dependencies, Storage, Testing, Target Platform, Project Type, Performance Goals, Constraints, Scale/Scope)
        * **REASON**: The update-agent-context.js script parses these English field names to extract tech stack information
        * **DO NOT translate field names** even if preferred_language is 'zh' - only translate the values/descriptions
        * Mark unknowns as "NEEDS CLARIFICATION"

  4.  **Draft Task Breakdown (`tasks.md`):**
      - Load the `tasks.md`.
      - Break down the implementation plan into a series of small, actionable development tasks.
      - Each task should be a logical, sequential step that a developer can pick up and complete. This must perfectly align with the User Stories defined in the plan.

  ---

  ### **Guiding Principles (Guardrails)**

  - **Preserve All Details (Completeness Guarantee):** spec.md MUST be a superset of user input. If any information exists in user input, it MUST be findable in spec.md. This applies to every line, every reference (code blocks, images, local files), and every detail. After generation, verify: for any content in user input, you can locate its corresponding entry in spec.md.
  - **Simplicity First:** Always start with the most straightforward and minimal implementation. Avoid over-engineering.
  - **Scoped Changes:** Keep all proposed changes tightly focused on the requested feature. Do not introduce unrelated modifications.
  - **Respect Templates:** Preserve the section order and headings of all template files (`spec`, `plan`, `tasks`).
  - **URL Content Fetch**: Use lark-docs mcp to get a lark document content.

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated documents (spec.md, plan.md, tasks.md..) are correct.

**If needs adjustment**: Run `/adkl:revise [feedback]` to refine the documents.

### Step 2 - Next Step Recommendation
Once documents are confirmed and satisfactory:

**Start Implementation**: Execute `/adkl:apply` to begin implementing the tasks sequentially.
