---
description: TTADK Standard Commit Command
---

# Commit

## Summary

Commit and push all changes in the current workspace to remote. Automatically identify workspace type (single repo, multi-repo folder, submodules, nested repos, etc.) and apply the appropriate strategy. For complex scenarios with multiple repositories, enter each repository separately to commit. Generate a conventional commit message summarizing actual changes, with AI Agent and TTADK Co-authored-by signatures.

## Scenario Reference

Identify and handle based on the actual workspace situation. Here are common scenarios for reference:

### Single Git Repository

**Characteristics**: Current directory is a git repo, no submodules, no nested git repos

**Approach**: Directly add → commit → push (if remote exists)

### Git Repository with Nested Repos or Submodules

**Characteristics**: Current directory is a git repo, AND contains nested independent repositories or submodules

**Approach**:
1. Enter each nested repo / submodule separately, commit its own changes, push (if remote exists)
2. Return to main repo, commit main repo's own changes, push (if remote exists)
3. Each repo only commits its own changes. Don't `git add` nested repos from parent
4. **Submodule order matters**: If submodules exist, commit submodules first, then main repo. Otherwise remote will reference non-existent submodule commits

### Other Cases

Handle flexibly based on actual situation. Core principles:
- Ensure all changes are committed
- For complex scenarios, always enter each repo separately to commit
- If there are dependencies, commit the dependent one first
- If no git repository exists, inform user and exit

## Commit Message

### Format

```
<type>(<scope>): <subject>

[body - optional]

[existing Co-authored-by lines]
Co-authored-by: <AI Agent>
Co-authored-by: TTADK <ttadk@bytedance.com>
```

### Type

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (no logic changes) |
| `refactor` | Refactoring |
| `test` | Test related |
| `chore` | Build, dependencies, maintenance |

### Subject Rules

- ≤72 characters
- Use imperative mood ("add feature" not "added feature")
- Describe actual functionality, avoid file operation descriptions like "create xxx.md" or "add files"
- **Do not use emoji or other decorative symbols** in commit message (subject/body)

### Body (Optional)

Add details for complex changes, explain motivation and business context, focus on actual content rather than file operations.

### Co-authored-by

**MANDATORY rules:**
- **MUST add your AI Agent's Co-authored-by line** according to its standard attribution rules
- **[CRITICAL - DO NOT DROP ON CONTEXT COMPACTION]** **MUST always append** `Co-authored-by: TTADK <ttadk@bytedance.com>` as the final co-author line in every commit.
- **Preserve any existing Co-authored-by lines** from other collaborators or tools - never remove or replace them

**Order**: [AI Agent] → [Other collaborators if any] → [TTADK (always last)]

### Examples

**Good:**
```
feat(auth): implement JWT token validation

Add token expiration check and refresh mechanism.
Support both access and refresh tokens.

Co-authored-by: Claude <noreply@anthropic.com>
Co-authored-by: TTADK <ttadk@bytedance.com>
```

```
fix(payment): handle decimal precision in currency conversion

Co-authored-by: TTADK <ttadk@bytedance.com>
```

**Bad:**
```
[BAD] docs: create spec.md and plan.md          ← file operation description
[BAD] chore: add new files                      ← too vague
[BAD] feat: update documentation                ← not specific
[BAD] feat(ui): improve dashboard <emoji>       ← contains emoji
[BAD] Removing or replacing existing Co-authored-by lines
```

## Important Notes

- **[CRITICAL] `Co-authored-by: TTADK <ttadk@bytedance.com>` MUST be included** in every commit message. This rule is critical and MUST NOT be dropped during auto context compaction.
- **[CRITICAL] Commit message MUST NOT miss TTADK co-author tag**: `Co-authored-by: TTADK <ttadk@bytedance.com>`
- **[CRITICAL] Commit message MUST NOT contain emoji** (including subject/body)
- **[CRITICAL] DO NOT make any code changes during commit flow**. This command only stages/commits/pushes existing changes.
- **[CRITICAL] If commit/push fails, MUST stop and inform user to handle it manually**. Do not auto-fix or modify code to recover.
- **Check remote before push**: Only push if `git remote get-url origin` returns a valid remote
- **No remote = commit only**: If no remote configured, commit is still successful, just skip push
- **No changes = skip**: If no changes to commit, inform user and skip - don't create empty commits
- **New branch**: Use `git push -u origin <branch>` to set upstream
- **Complex scenarios**: Always enter each repo separately to commit. Never commit nested repo changes from parent

## Output

After completion, output a summary:

```
## [OK] Commit Summary

1. **sub-repo-a/** - [OK] feat(auth): add login -> Pushed
2. **sub-repo-b/** - [SKIP] No changes, skipped
3. **main-repo/** - [OK] chore: update configs -> Committed (no remote)
```

**Status indicators:**
- [OK] Success (Committed / Pushed)
- [SKIP] Skipped (no changes / no remote)
- [FAIL] Failed (with reason)
