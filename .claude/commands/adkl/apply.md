---

description: Implement an approved change and keep tasks in sync.

---



## Phase

- ### **Phase 1: Initialization & Context Loading**

  **Objective:** Understand the task at hand by loading all relevant context.
  
  1.  **Set Language:**
      - Read `.ttadk/config.json` to determine `preferred_language` (default: 'en').
      - All your communication (status updates, questions, errors) MUST be in this language.
  2.  **Load Core Instructions:**
      - Read and internalize the principles from `.ttadk/memory/constitution.md`.
  3.  **Identify the Active Feature:**
      - Run `node .ttadk/plugins/ttadk/core/resources/scripts/check-prerequisites.js --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list.
      - This command tells you which feature you are currently working on.
  4.  **Load Planning Documents:**
      - Read the full content of `spec.md` to understand the *what* and *why* (requirements and goals).
      - Read the full content of `plan.md` to understand the *how* (technical approach).
      - Read the full content of `tasks.md` to get your ordered to-do list.

  ---
  ### **Phase 2: Staged Implementation & Verification**
  **Objective:** Implement the feature by completing tasks sequentially and verifying each step.

  **⚠️ CRITICAL: Progress Tracking Rules**
  - **Resume Rule**: Skip tasks already marked `[x]` or `[X]`, continue from the first `- [ ]`. When re-entering this command, automatically continue from where you left off - do NOT start from the beginning unless the user explicitly requests to redo or fix a specific task.
  - **Immediate Update Rule**: Update tasks.md IMMEDIATELY after each task, BEFORE moving to the next. Do NOT batch updates.

  1.  **Analyze the Task List:**
      - Parse `tasks.md` and identify the **first uncompleted task** (the first line that starts with `- [ ]`).
      - Focus exclusively on this single task.
  2.  **Code Implementation:**
      - Based on the task description and the `plan.md`, determine which files need to be modified or created.
      - **Before writing code**, use `rg` and `cat` to read the current state of the relevant files. This ensures your changes are based on the latest version.
      - Write the necessary code to complete the task. Adhere strictly to the implementation plan and coding standards.
  3.  **Self-Correction & Verification (Critical Step):**
      - After applying changes, re-read the code you just wrote.
      - Does it correctly implement the task?
      - Does it introduce any obvious bugs?
      - Does it align with the `plan.md`?
      - If you find issues, correct them immediately before moving on.
  4.  **Update Task Status (MUST do immediately):**
      - Once the task is verifiably complete, IMMEDIATELY update its corresponding line in `tasks.md` from `- [ ]` to `- [x]`.
      - Save the updated `tasks.md` file NOW, before proceeding.
  5.  **Loop or Complete:**
      - **If there are more uncompleted tasks** in `tasks.md`, return to Step 1 of this phase and begin the next task.
      - **If all tasks are marked `- [x]`**, proceed to Phase 3.
  ---
  ### **Phase 3: Finalization**
  **Objective:** Confirm completion and prepare for the next stage (e.g., pull request).

  1.  **Final Review:**
      - Perform a quick final scan of all modified files to ensure consistency.
      - Double-check that `tasks.md` is fully marked as complete.
  2.  **Final Task Completion Check:**
      - Re-read `tasks.md` and verify no `- [ ]` remains
      - If incomplete tasks exist, complete them before proceeding
  3.  **Build and Test Validation:**
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
  3.  **Report Completion:**
      - Output a summary message confirming that all implementation tasks for the feature are complete and ready for review.
      - Include build/test results in the summary if validation was performed.
  ---
  ### **Guiding Principles (Guardrails)**
  - **Minimalism:** Implement the simplest possible solution that meets the requirements. Avoid premature optimization or complexity.
  - **Focus:** Keep your changes tightly scoped to the current task. Do not modify unrelated code.
  - **Sequential Execution:** Always complete tasks in the order they are listed in `tasks.md`. Do not skip ahead.
  - **Idempotency:** If a task is already marked as complete (`- [x]`), do not re-do it. Simply acknowledge its completion and move to the next.

## Next Step Guidance

After executing this command, provide next-step guidance to user:

### Step 1 - Confirmation
Guide user to verify the generated code is correct and meets expectations.

**If needs adjustment**:
- Run `/adkl:revise [feedback]` to update documentation
- Run `/adkl:apply [feedback]` to modify the code

### Step 2 - Next Step Recommendation
Once implementation is confirmed and satisfactory:

**Commit Changes**: Execute `/adk:commit` to stage changes, generate commit message, and push to remote.