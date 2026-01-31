"use strict";
/**
 * Common utilities for TTADK workflow scripts
 * Uses only Node.js built-in modules (no external dependencies)
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.existsSync = existsSync;
exports.isDirSync = isDirSync;
exports.getRepoRoot = getRepoRoot;
exports.getCurrentBranch = getCurrentBranch;
exports.normalizeDescription = normalizeDescription;
exports.generateFeatureName = generateFeatureName;
exports.findLatestFeatureDir = findLatestFeatureDir;
exports.getFeatureName = getFeatureName;
exports.hasGit = hasGit;
exports.checkFeatureBranch = checkFeatureBranch;
exports.getFeaturePaths = getFeaturePaths;
exports.getArchivePaths = getArchivePaths;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const child_process_1 = require("child_process");
/**
 * Check if path exists (sync)
 */
function existsSync(filePath) {
    try {
        fs.accessSync(filePath, fs.constants.F_OK);
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Check if path is a directory (sync)
 */
function isDirSync(filePath) {
    try {
        return fs.statSync(filePath).isDirectory();
    }
    catch {
        return false;
    }
}
/**
 * Get repository root, with fallback for non-git repositories
 *
 * Priority:
 * 1. Search for .ttadk directory (TTADK project root marker)
 * 2. Use git repository root (if available)
 * 3. Search for .git directory
 *
 * This ensures that specs/ and other project files are always co-located with .ttadk/,
 * even when the project is inside a parent git repository.
 */
function getRepoRoot() {
    // Priority 1: Search upward for .ttadk directory (TTADK project root)
    let dir = process.cwd();
    while (dir !== path.parse(dir).root) {
        if (existsSync(path.join(dir, '.ttadk'))) {
            return dir;
        }
        dir = path.dirname(dir);
    }
    // Priority 2: Try git repository root (for backward compatibility)
    try {
        const root = (0, child_process_1.execSync)('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();
        return root;
    }
    catch {
        // Priority 3: Search for .git directory
        dir = process.cwd();
        while (dir !== path.parse(dir).root) {
            if (existsSync(path.join(dir, '.git'))) {
                return dir;
            }
            dir = path.dirname(dir);
        }
        throw new Error('Could not determine repository root. Please run from within the repository.');
    }
}
/**
 * Get current branch, with fallback for non-git repositories
 *
 * Priority:
 * 1. TTADK_FEATURE environment variable (highest priority)
 * 2. git symbolic-ref --short HEAD (works in empty repos without commits)
 * 3. git rev-parse --abbrev-ref HEAD (works in detached HEAD state)
 * 4. 'master' fallback (for non-git repos)
 */
function getCurrentBranch() {
    // First check if TTADK_FEATURE environment variable is set
    if (process.env.TTADK_FEATURE) {
        return process.env.TTADK_FEATURE;
    }
    // Try git symbolic-ref first (works in empty repos without commits)
    try {
        const branch = (0, child_process_1.execSync)('git symbolic-ref --short HEAD', {
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe'],
        }).trim();
        if (branch) {
            return branch;
        }
    }
    catch {
        // Fall through to next method
    }
    // Try git rev-parse (works in detached HEAD state, returns 'HEAD' if detached)
    try {
        const branch = (0, child_process_1.execSync)('git rev-parse --abbrev-ref HEAD', {
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe'],
        }).trim();
        if (branch && branch !== 'HEAD') {
            return branch;
        }
    }
    catch {
        // Fall through to fallback
    }
    return 'master'; // Fallback for non-git repos
}
/**
 * Normalize description to URL-safe format
 * - Convert to lowercase
 * - Replace spaces and special chars with hyphens
 * - Remove consecutive hyphens
 * - Trim hyphens from start/end
 * - Keep only first 3 words (consistent with original NNN- format)
 */
function normalizeDescription(description) {
    if (!description) {
        return 'unnamed';
    }
    return description
        .toLowerCase()
        .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-') // Keep alphanumeric and Chinese chars
        .replace(/-+/g, '-') // Remove consecutive hyphens
        .replace(/^-|-$/g, '') // Trim hyphens from start/end
        .split('-')
        .filter(word => word.length > 0)
        .slice(0, 3) // Only keep first 3 words
        .join('-') || 'unnamed';
}
/**
 * Generate feature name in format: YYYYMMDD-normalized-description
 */
function generateFeatureName(description) {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const datePrefix = `${year}${month}${day}`;
    const normalizedDesc = normalizeDescription(description);
    return `${datePrefix}-${normalizedDesc}`;
}
/**
 * Find the latest feature directory in specs/
 * Looks for directories matching YYYYMMDD-* pattern and returns the most recent one by creation time
 */
function findLatestFeatureDir() {
    try {
        const repoRoot = getRepoRoot();
        const specsDir = path.join(repoRoot, 'specs');
        if (!existsSync(specsDir) || !isDirSync(specsDir)) {
            return null;
        }
        const dirs = fs.readdirSync(specsDir)
            .filter(name => {
                const fullPath = path.join(specsDir, name);
                // Match YYYYMMDD-* pattern (new format) or NNN-* pattern (legacy format)
                // Exclude special directories like 'archived', 'doc_export'
                return isDirSync(fullPath) &&
                       (/^\d{8}-/.test(name) || /^\d{3}-/.test(name)) &&
                       !['archived', 'doc_export'].includes(name);
            })
            .map(name => {
                const fullPath = path.join(specsDir, name);
                const stat = fs.statSync(fullPath);
                // Use birthtime (creation time), fallback to mtime if not available
                const time = stat.birthtime ? stat.birthtime.getTime() : stat.mtime.getTime();
                return { name, time };
            });
        if (dirs.length === 0) {
            return null;
        }
        // Sort by creation time, most recent first
        dirs.sort((a, b) => b.time - a.time);
        return dirs[0].name;
    }
    catch {
        return null;
    }
}
/**
 * Get feature name for specs directory
 *
 * Priority:
 * 1. TTADK_FEATURE environment variable (highest priority, for existing features)
 * 2. Find latest feature directory in specs/ (for commands that work on existing features)
 * 3. Generate new name from description parameter (for new features)
 * 4. Fallback to 'YYYYMMDD-unnamed'
 */
function getFeatureName(description) {
    // First check if TTADK_FEATURE environment variable is set
    if (process.env.TTADK_FEATURE) {
        return process.env.TTADK_FEATURE;
    }
    // If no description provided, try to find the latest feature directory
    if (!description) {
        const latestFeature = findLatestFeatureDir();
        if (latestFeature) {
            return latestFeature;
        }
    }
    // Generate new feature name from description
    return generateFeatureName(description);
}
/**
 * Check if we have git available
 */
function hasGit() {
    try {
        (0, child_process_1.execSync)('git rev-parse --show-toplevel', { stdio: 'ignore' });
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Check if current branch is valid (always returns true, kept for compatibility)
 */
function checkFeatureBranch(_branch) {
    return true;
}
/**
 * Get all feature-related paths
 * @param {string} description - Optional description for generating new feature name
 */
function getFeaturePaths(description) {
    const repoRoot = getRepoRoot();
    const featureName = getFeatureName(description);
    const hasGitRepo = hasGit();
    const featureDir = path.join(repoRoot, 'specs', featureName);
    return {
        REPO_ROOT: repoRoot,
        FEATURE_NAME: featureName,
        HAS_GIT: hasGitRepo,
        FEATURE_DIR: featureDir,
        FEATURE_SPEC: path.join(featureDir, 'spec.md'),
        IMPL_PLAN: path.join(featureDir, 'plan.md'),
        TASKS: path.join(featureDir, 'tasks.md'),
        RESEARCH: path.join(featureDir, 'research.md'),
        DATA_MODEL: path.join(featureDir, 'data-model.md'),
        QUICKSTART: path.join(featureDir, 'quickstart.md'),
        CONTRACTS_DIR: path.join(featureDir, 'contracts'),
    };
}
/**
 * Get archive-specific paths
 */
function getArchivePaths(repoRoot) {
    const root = repoRoot || getRepoRoot();
    const specsDir = path.join(root, 'specs');
    const archivedDir = path.join(specsDir, 'archived');
    const archiveIndexPath = path.join(specsDir, 'ARCHIVE.md');
    return {
        specsDir,
        archivedDir,
        archiveIndexPath,
    };
}
//# sourceMappingURL=common.js.map