---
description: Archive old spec folders to compressed tar.gz format and maintain a searchable registry in specs/ARCHIVE.md

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

## Usage Examples

- Archive all specs: `/adk:archive`
- Preview what would be archived (dry-run): `/adk:archive --dry-run`
- Output in JSON format: `/adk:archive --json`

## Command Execution

When you invoke this command:

1. Parse the arguments to extract:
    - `--dry-run` flag for preview mode
    - `--json` flag for JSON output

2. Execute the archive script from repo root:
    ```bash
    node .ttadk/plugins/ttadk/core/resources/scripts/archive-spec.js [arguments]
    ```

3. Handle the output:
    - **Success**: Show which specs were archived, their sizes, and paths
    - **Dry-run**: Show preview of what would be archived without making changes
    - **Error**: Display error message with context

## Behavior

The archive script uses **feature-based spec organization**:

- **Recursively scans** `specs/` for all directories containing `spec.md`
- **Archives ALL spec directories** (including current feature) into `specs/archived/`
- **ALL spec directories are deleted** after successful archiving (including current feature)
- **Updates specs/ARCHIVE.md** with metadata (feature name, description, date, size, path)
- **Overwrites existing archives** with the same name (no timestamp suffix)
- **Skips** `archived/` and `doc_export/` directories

## Arguments

- **--dry-run** (optional): Preview mode - shows what would be archived without making any changes
  - No tar.gz files created
  - No ARCHIVE.md modifications
  - No spec folders deleted
  - Displays estimated archive sizes

- **--json** (optional): Output result in JSON format instead of human-readable format

## Output Format

### Human-Readable (default)
```
✓ Archived 3 spec(s)

Current feature: 20250107-new-feature

  20250106-old-feature (deleted)
    → 20250106-old-feature.tar.gz (45.2 KB)

  20250105-bug-fix (deleted)
    → 20250105-bug-fix.tar.gz (128.7 KB)

  20250107-new-feature (deleted)
    → 20250107-new-feature.tar.gz (32.1 KB)
```

### Dry-Run Format
```
[DRY RUN] Archived 3 spec(s)

Current feature: 20250107-new-feature

  20250106-old-feature (will be deleted)
    → 20250106-old-feature.tar.gz (estimated 22.6 KB)

  20250105-bug-fix (will be deleted)
    → 20250105-bug-fix.tar.gz (estimated 64.3 KB)

  20250107-new-feature (will be deleted)
    → 20250107-new-feature.tar.gz (estimated 16.0 KB)
```

### JSON Format
```json
{
  "success": true,
  "currentFeature": "20250107-new-feature",
  "archived": [
    {
      "featureName": "20250106-old-feature",
      "specPath": "/path/to/specs/20250106-old-feature",
      "archivePath": "/path/to/specs/archived/20250106-old-feature.tar.gz",
      "size": "45.2 KB",
      "description": "Old Feature Spec",
      "deleted": true
    },
    {
      "featureName": "20250107-new-feature",
      "specPath": "/path/to/specs/20250107-new-feature",
      "archivePath": "/path/to/specs/archived/20250107-new-feature.tar.gz",
      "size": "32.1 KB",
      "description": "New Feature Spec",
      "deleted": true
    }
  ]
}
```

## Notes

- Spec directories are named using **YYYYMMDD-description format** (e.g., `specs/20250107-update-feature/`)
- Feature names are already in a flat format, so archive filenames match directory names (e.g., `20250107-update-feature.tar.gz`)
- ARCHIVE.md provides searchable metadata without needing to extract tar.gz files
- Archived specs can be restored by extracting: `tar -xzf specs/archived/20250107-feature-name.tar.gz -C specs/`
- Empty parent directories are automatically cleaned up after deleting spec folders
