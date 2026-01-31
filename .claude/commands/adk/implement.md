---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md

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

1. Run `node .ttadk/plugins/ttadk/core/resources/scripts/check-prerequisites.js --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory
   - For each checklist, count:
      * Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
      * Completed items: Lines matching `- [X]` or `- [x]`
      * Incomplete items: Lines matching `- [ ]`
   - Create a status table:
      ```
      | Checklist | Total | Completed | Incomplete | Status |
      |-----------|-------|-----------|------------|--------|
      | ux.md     | 12    | 12        | 0          | ✓ PASS |
      | test.md   | 8     | 5         | 3          | ✗ FAIL |
      | security.md | 6   | 6         | 0          | ✓ PASS |
      ```
   - Calculate overall status:
      * **PASS**: All checklists have 0 incomplete items
      * **FAIL**: One or more checklists have incomplete items
   
   - **If any checklist is incomplete**:
      * Display the table with incomplete item counts
      * **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
      * Wait for user response before continuing
      * If user says "no" or "wait" or "stop", halt execution
      * If user says "yes" or "proceed" or "continue", proceed to step 3
   
   - **If all checklists are complete**:
      * Display the table showing all checklists passed
      * Automatically proceed to step 3

3. Load and analyze the implementation context:
   - **REQUIRED**: Read spec.md to understand the *what* and *why* (requirements and goals)
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

4. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Execution flow**: Order and dependency requirements

5. Execute implementation following the task plan:
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together  
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding

6. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
   - **Tests before code**: If you need to write tests for contracts, entities, and integration scenarios
   - **Core development**: Implement models, services, CLI commands, endpoints
   - **Integration work**: Database connections, middleware, logging, external services
   - **Polish and validation**: Unit tests, performance optimization, documentation

7. **⚠️ CRITICAL: Progress Tracking (MUST follow strictly)**

   **Resume Rule**: If a task is already marked as `[X]` or `[x]`, skip it and move to the next uncompleted task. When re-entering this command, automatically continue from where you left off - do NOT start from the beginning unless the user explicitly requests to redo or fix a specific task.

   **Immediate Update Rule**: As soon as a task is completed, you MUST immediately update its status in tasks.md from `- [ ]` to `- [x]` BEFORE moving to the next task. Do NOT batch updates. Do NOT wait until the end.

   **Workflow**: Complete task → Verify completion → Update tasks.md (`- [ ]` → `- [x]`) → Move to next task

   Other error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For parallel tasks [P], continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging

8. Completion validation:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan

9. **Final Task Completion Check**:
   - Re-read `tasks.md` and verify no `- [ ]` remains
   - If incomplete tasks exist, complete them before proceeding

10. Build and test validation:
   - After all tasks are completed, try to compile and test the project based on its build system
   - Common build systems to check:
     * `package.json` → Try `npm run build` or `npm test`
     * `Cargo.toml` → Try `cargo build` or `cargo test`
     * `go.mod` → Try `go build ./...` or `go test ./...`
     * `pom.xml` or `build.gradle` → Try Maven/Gradle commands
     * `Makefile` → Try `make` or `make test`
   - Choose the appropriate command based on the project structure
   - If compilation or tests fail, analyze the errors and fix the issues
   - Re-run the build/test until successful
   - Report final status with summary of completed work and build/test results

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/tasks` first to regenerate the task list.

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated code is correct and meets expectations.

**If needs adjustment**:
- Run `/adk:clarify [feedback]` to update documentation
- Run `/adk:implement [feedback]` to modify the code

### Step 2 - Next Step Recommendation
Once implementation is confirmed and satisfactory:

**Commit Changes**: Execute `/adk:commit` to stage changes, generate commit message, and push to remote.
