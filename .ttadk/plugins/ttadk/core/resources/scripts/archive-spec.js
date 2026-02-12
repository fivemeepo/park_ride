#!/usr/bin/env node
"use strict";
/**
 * Archive Spec Script
 *
 * Archives all feature specifications by packaging them into tar.gz format
 * and maintaining a searchable registry in specs/ARCHIVE.md
 *
 * Key behaviors:
 * - Recursively scans specs/ for all spec directories (supports nested like feat/update-1-1)
 * - Archives ALL spec directories (including current feature)
 * - ALL spec directories are deleted after archiving
 * - If archive file already exists, it is overwritten (not duplicated with timestamp)
 * - archived/ and doc_export/ directories are never touched
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.archiveSpecs = archiveSpecs;
const fsSync = __importStar(require("fs"));
const path_1 = __importDefault(require("path"));
const child_process_1 = require("child_process");
const common_1 = require("./common");
/**
 * Extract spec description from first heading of spec.md
 */
function extractSpecDescription(specMdPath) {
    if (!fsSync.existsSync(specMdPath)) {
        return null;
    }
    const content = fsSync.readFileSync(specMdPath, 'utf-8');
    const lines = content.split('\n');
    for (const line of lines) {
        const trimmed = line.trim();
        // Skip empty lines and front matter
        if (!trimmed || trimmed === '---')
            continue;
        // Match ATX-style heading: # Text or # Text #
        const match = trimmed.match(/^(#{1,6})\s+([^\n]+?)\s*#*\s*$/);
        if (match) {
            const text = match[2].trim();
            return text;
        }
        // Stop at first non-heading content
        if (!trimmed.startsWith('#'))
            break;
    }
    return null;
}
/**
 * Get archive description from spec folder
 */
function getArchiveDescription(specPath) {
    const specMdPath = path_1.default.join(specPath, 'spec.md');
    const description = extractSpecDescription(specMdPath);
    if (description) {
        // Truncate to 200 characters and escape pipes
        return description.slice(0, 200).replace(/\|/g, '\\|');
    }
    // Fallback to folder name
    return path_1.default.basename(specPath);
}
/**
 * Format file size in human-readable format
 */
function formatSize(bytes) {
    if (bytes < 1024)
        return `${bytes} B`;
    if (bytes < 1024 * 1024)
        return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024)
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}
/**
 * Create tar.gz archive from directory
 */
function createTarGz(sourceDir, outputPath) {
    const sourceName = path_1.default.basename(sourceDir);
    const sourceParent = path_1.default.dirname(sourceDir);
    // Quote paths to handle spaces
    const command = `tar -czf "${outputPath}" -C "${sourceParent}" "${sourceName}"`;
    try {
        (0, child_process_1.execSync)(command, {
            encoding: 'utf-8',
            stdio: 'pipe'
        });
        if (!fsSync.existsSync(outputPath)) {
            throw new Error('Archive file not created');
        }
        return outputPath;
    }
    catch (error) {
        if (fsSync.existsSync(outputPath)) {
            fsSync.unlinkSync(outputPath);
        }
        throw new Error(`Failed to create tar.gz: ${error.message}`);
    }
}
/**
 * Parse ARCHIVE.md markdown table into row objects
 */
function parseArchiveTable(content) {
    const rows = [];
    const lines = content.split('\n');
    let inTable = false;
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.match(/^\|[-:\s|]+\|$/)) {
            inTable = true;
            continue;
        }
        if (inTable && trimmed.startsWith('|') && trimmed.endsWith('|')) {
            const cells = trimmed.split('|')
                .map(cell => cell.trim())
                .filter(cell => cell.length > 0);
            if (cells.length === 5) {
                rows.push({
                    featureName: cells[0],
                    description: cells[1],
                    archived: cells[2],
                    size: cells[3],
                    path: cells[4]
                });
            }
        }
        if (inTable && !trimmed.startsWith('|'))
            break;
    }
    return rows;
}
/**
 * Update ARCHIVE.md with new entry
 */
function updateArchiveIndex(archiveIndexPath, metadata) {
    const header = `# Archived Specs\n\n| Feature | Description | Archived | Size | Path |\n|---------|-------------|----------|------|------|\n`;
    let rows = [];
    if (fsSync.existsSync(archiveIndexPath)) {
        const content = fsSync.readFileSync(archiveIndexPath, 'utf-8');
        rows = parseArchiveTable(content);
    }
    // Update existing or add new
    const existingIndex = rows.findIndex(r => r.featureName === metadata.featureName);
    const newRow = {
        featureName: metadata.featureName,
        description: metadata.description,
        archived: metadata.date,
        size: metadata.size,
        path: metadata.archivePath
    };
    if (existingIndex >= 0) {
        rows[existingIndex] = newRow;
    }
    else {
        rows.push(newRow);
    }
    // Sort by archived date (descending)
    rows.sort((a, b) => b.archived.localeCompare(a.archived));
    const tableRows = rows.map(row => `| ${row.featureName} | ${row.description} | ${row.archived} | ${row.size} | ${row.path} |`).join('\n');
    fsSync.writeFileSync(archiveIndexPath, header + tableRows + '\n', 'utf-8');
}
/**
 * Get archive size from tar.gz file
 */
function getArchiveSize(archivePath) {
    const stats = fsSync.statSync(archivePath);
    return formatSize(stats.size);
}
/**
 * Estimate size of directory for dry-run
 */
function estimateDirectorySize(dirPath) {
    let totalSize = 0;
    function walkDir(currentPath) {
        if (!fsSync.existsSync(currentPath))
            return;
        const items = fsSync.readdirSync(currentPath);
        for (const item of items) {
            const fullPath = path_1.default.join(currentPath, item);
            const stats = fsSync.statSync(fullPath);
            if (stats.isDirectory()) {
                walkDir(fullPath);
            }
            else {
                totalSize += stats.size;
            }
        }
    }
    try {
        walkDir(dirPath);
    }
    catch {
        // Ignore errors
    }
    return totalSize;
}
/**
 * Pre-flight checks
 */
function preFlightChecks() {
    try {
        (0, child_process_1.execSync)('tar --version', { stdio: 'ignore' });
    }
    catch {
        return {
            valid: false,
            error: 'tar command not found. Please ensure tar is installed and available in PATH.'
        };
    }
    return { valid: true };
}
/**
 * Convert feature name to safe filename (replace / with -)
 * Note: With the new YYYYMMDD-description format, feature names are already flat
 * but this function is kept for backward compatibility with any nested paths
 */
function featureNameToFilename(featureName) {
    return featureName.replace(/\//g, '-');
}
/**
 * Recursively find all spec directories (directories containing spec.md)
 */
function findAllSpecDirs(specsDir, relativePath = '') {
    const results = [];
    const currentDir = relativePath ? path_1.default.join(specsDir, relativePath) : specsDir;
    if (!fsSync.existsSync(currentDir)) {
        return results;
    }
    const items = fsSync.readdirSync(currentDir);
    for (const item of items) {
        // Skip archived and doc_export directories
        if (item === 'archived' || item === 'doc_export')
            continue;
        const fullPath = path_1.default.join(currentDir, item);
        const itemRelativePath = relativePath ? `${relativePath}/${item}` : item;
        if (!fsSync.statSync(fullPath).isDirectory())
            continue;
        // Check if this directory contains spec.md
        const specMdPath = path_1.default.join(fullPath, 'spec.md');
        if (fsSync.existsSync(specMdPath)) {
            results.push({
                featureName: itemRelativePath,
                fullPath: fullPath
            });
        }
        else {
            // Recursively search subdirectories
            const subResults = findAllSpecDirs(specsDir, itemRelativePath);
            results.push(...subResults);
        }
    }
    return results;
}
/**
 * Main archive function
 */
async function archiveSpecs(options = {}) {
    const result = {
        success: true,
        archived: [],
        currentFeature: ''
    };
    try {
        const repoRoot = (0, common_1.getRepoRoot)();
        const { specsDir, archivedDir, archiveIndexPath } = (0, common_1.getArchivePaths)(repoRoot);
        // Pre-flight checks
        const preFlightResult = preFlightChecks();
        if (!preFlightResult.valid) {
            return {
                ...result,
                success: false,
                error: preFlightResult.error,
                errorCode: 3
            };
        }
        // Get current feature name
        const currentFeature = (0, common_1.getFeatureName)();
        result.currentFeature = currentFeature;
        // Ensure archived directory exists
        if (!fsSync.existsSync(archivedDir)) {
            fsSync.mkdirSync(archivedDir, { recursive: true });
        }
        // Find all spec directories recursively
        const allSpecs = findAllSpecDirs(specsDir);
        if (allSpecs.length === 0) {
            return {
                ...result,
                error: 'No spec directories found in specs/'
            };
        }
        const today = new Date().toISOString().split('T')[0];
        // Dry-run mode
        if (options.dryRun) {
            result.dryRun = true;
            for (const spec of allSpecs) {
                const estimatedSize = estimateDirectorySize(spec.fullPath);
                const archiveFilename = `${featureNameToFilename(spec.featureName)}.tar.gz`;
                result.archived.push({
                    featureName: spec.featureName,
                    specPath: spec.fullPath,
                    archivePath: path_1.default.join(archivedDir, archiveFilename),
                    size: `estimated ${formatSize(Math.floor(estimatedSize * 0.5))}`,
                    description: getArchiveDescription(spec.fullPath),
                    deleted: true
                });
            }
            return result;
        }
        // Archive each spec directory
        for (const spec of allSpecs) {
            const archiveFilename = `${featureNameToFilename(spec.featureName)}.tar.gz`;
            let archivePath = path_1.default.join(archivedDir, archiveFilename);
            // Overwrite if archive already exists
            if (fsSync.existsSync(archivePath)) {
                fsSync.unlinkSync(archivePath);
            }
            // Create archive
            createTarGz(spec.fullPath, archivePath);
            // Update ARCHIVE.md
            const metadata = {
                featureName: spec.featureName,
                description: getArchiveDescription(spec.fullPath),
                date: today,
                size: getArchiveSize(archivePath),
                archivePath: path_1.default.relative(specsDir, archivePath)
            };
            updateArchiveIndex(archiveIndexPath, metadata);
            // Delete original folder (ALL folders, including current feature)
            const shouldDelete = true;
            if (shouldDelete) {
                fsSync.rmSync(spec.fullPath, { recursive: true, force: true });
                // Clean up empty parent directories
                let parentDir = path_1.default.dirname(spec.fullPath);
                while (parentDir !== specsDir) {
                    const items = fsSync.readdirSync(parentDir);
                    if (items.length === 0) {
                        fsSync.rmdirSync(parentDir);
                        parentDir = path_1.default.dirname(parentDir);
                    }
                    else {
                        break;
                    }
                }
            }
            result.archived.push({
                featureName: spec.featureName,
                specPath: spec.fullPath,
                archivePath,
                size: metadata.size,
                description: metadata.description,
                deleted: shouldDelete
            });
        }
        return result;
    }
    catch (error) {
        return {
            ...result,
            success: false,
            error: error.message,
            errorCode: 4
        };
    }
}
/**
 * Parse CLI arguments
 */
function parseArgs(args) {
    const options = {
        dryRun: false,
        json: false
    };
    for (const arg of args) {
        if (arg === '--dry-run') {
            options.dryRun = true;
        }
        else if (arg === '--json') {
            options.json = true;
        }
    }
    return options;
}
// CLI mode detection
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`Usage: archive-spec [OPTIONS]

Archives all spec directories in specs/ to specs/archived/.

OPTIONS:
  --dry-run        Preview mode - shows what would be archived without making changes
  --json           Output result in JSON format
  -h, --help       Show this help message

BEHAVIOR:
  - Recursively finds all directories containing spec.md
  - Archives ALL spec directories (including current feature)
  - ALL spec directories are deleted after archiving
  - archived/ and doc_export/ directories are never touched
  - Updates specs/ARCHIVE.md with archive metadata

EXAMPLES:
  archive-spec                    # Archive all specs
  archive-spec --dry-run          # Preview what would be archived
  archive-spec --json             # Output in JSON format
`);
        process.exit(0);
    }
    const options = parseArgs(args);
    archiveSpecs(options)
        .then(result => {
        if (options.json) {
            console.log(JSON.stringify(result, null, 2));
        }
        else {
            if (result.success) {
                if (result.archived.length === 0) {
                    console.log(result.error || 'Nothing to archive');
                }
                else {
                    const prefix = result.dryRun ? '[DRY RUN] ' : '✓ ';
                    console.log(`${prefix}Archived ${result.archived.length} spec(s)\n`);
                    console.log(`Current feature: ${result.currentFeature}\n`);
                    for (const spec of result.archived) {
                        const deleteStatus = spec.deleted ? '(will be deleted)' : '(preserved)';
                        const deleteStatusActual = spec.deleted ? '(deleted)' : '(preserved)';
                        const status = result.dryRun ? deleteStatus : deleteStatusActual;
                        console.log(`  ${spec.featureName} ${status}`);
                        console.log(`    → ${path_1.default.basename(spec.archivePath)} (${spec.size})`);
                    }
                }
            }
            else {
                console.error(`ERROR: ${result.error}`);
            }
        }
        process.exit(result.success ? 0 : (result.errorCode || 1));
    })
        .catch(error => {
        console.error(`FATAL: ${error.message}`);
        process.exit(1);
    });
}
//# sourceMappingURL=archive-spec.js.map