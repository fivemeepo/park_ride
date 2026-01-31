#!/usr/bin/env node
"use strict";
/**
 * Create New Feature Lite Script
 * Uses only Node.js built-in modules (no external dependencies)
 *
 * Sets up feature directory and copies spec.md, plan.md, and tasks.md from templates
 * using YYYYMMDD-description naming format.
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
exports.createNewFeatureLite = createNewFeatureLite;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const common_1 = require("./common");
/**
 * Recursively scan directory for sequence numbers in filenames/foldernames
 * Pattern: 3-digit number at start of name (folder or file)
 * Note: Kept for compatibility but not used in current flow
 */
function findMaxSequenceNumber(dirPath) {
    let maxNum = 0;
    if (!(0, common_1.existsSync)(dirPath) || !(0, common_1.isDirSync)(dirPath)) {
        return maxNum;
    }
    try {
        const items = fs.readdirSync(dirPath);
        for (const item of items) {
            const fullPath = path.join(dirPath, item);
            // Check if item matches pattern: 3-digit number followed by hyphen or dot
            const match = item.match(/^(\d{3})[-.]/);
            if (match) {
                const num = parseInt(match[1], 10);
                if (num > maxNum) {
                    maxNum = num;
                }
            }
            // Recursively scan subdirectories (but skip .git and other hidden dirs)
            if ((0, common_1.isDirSync)(fullPath) && !item.startsWith('.')) {
                const subMax = findMaxSequenceNumber(fullPath);
                if (subMax > maxNum) {
                    maxNum = subMax;
                }
            }
        }
    }
    catch (error) {
        console.warn(`[ttadk] Warning: Could not scan directory ${dirPath}: ${error}`);
    }
    return maxNum;
}
/**
 * Validate feature name format (legacy format check)
 * @deprecated Kept for backward compatibility only - not used in current YYYYMMDD-description flow
 */
function validateBranchName(branchName) {
    const pattern = /^(\d{3}-)?[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$/;
    return pattern.test(branchName);
}
/**
 * Extract feature number from feature name (legacy format)
 * @deprecated Kept for backward compatibility only - not used in current YYYYMMDD-description flow
 */
function extractFeatureNumber(featureName) {
    const match = featureName.match(/^(\d{3})-/);
    return match ? match[1] : '';
}
/**
 * Copy template file to feature directory with fallback content
 */
function copyTemplate(repoRoot, templateName, featureDir, targetFileName, fallbackContent) {
    const templatePath = path.join(repoRoot, '.ttadk', 'plugins', 'ttadk', 'core', 'resources', 'templates', templateName);
    const targetPath = path.join(featureDir, targetFileName);
    if ((0, common_1.existsSync)(templatePath)) {
        const content = fs.readFileSync(templatePath, 'utf-8');
        fs.writeFileSync(targetPath, content, 'utf-8');
        console.log(`[ttadk] Debug: Copied template ${templateName} to ${targetPath}`);
    }
    else {
        fs.writeFileSync(targetPath, fallbackContent, 'utf-8');
        console.log(`[ttadk] Warning: Template ${templateName} not found, using fallback content`);
    }
    return targetPath;
}
// Suppress unused variable warnings
void findMaxSequenceNumber;
void validateBranchName;
void extractFeatureNumber;
async function createNewFeatureLite(featureDescription, _options = {}) {
    const repoRoot = (0, common_1.getRepoRoot)();
    const specsDir = path.join(repoRoot, 'specs');
    console.log(`[ttadk] Debug: Repository root: ${repoRoot}`);
    console.log(`[ttadk] Debug: Specs directory: ${specsDir}`);
    // Ensure specs directory exists
    if (!(0, common_1.existsSync)(specsDir)) {
        console.log(`[ttadk] Debug: Creating specs directory: ${specsDir}`);
        fs.mkdirSync(specsDir, { recursive: true });
    }
    // Get feature name (YYYYMMDD-description format, or from TTADK_FEATURE env var)
    const featureName = (0, common_1.getFeatureName)(featureDescription);
    console.log(`[ttadk] Debug: Feature name: ${featureName}`);
    // Extract feature number if exists (for compatibility)
    const featureNum = extractFeatureNumber(featureName) || '000';
    // Create feature directory
    const featureDir = path.join(specsDir, featureName);
    if (!(0, common_1.existsSync)(featureDir)) {
        fs.mkdirSync(featureDir, { recursive: true });
        console.log(`[ttadk] Debug: Created feature directory: ${featureDir}`);
    }
    // Copy all three template files (using lite versions)
    const specFilePath = copyTemplate(repoRoot, 'spec-template-lite.md', featureDir, 'spec.md', '# Feature Specification\n\nTODO: Fill in feature details\n');
    const planFilePath = copyTemplate(repoRoot, 'plan-template-lite.md', featureDir, 'plan.md', '# Implementation Plan\n\nTODO: Fill in implementation details\n');
    const tasksFilePath = copyTemplate(repoRoot, 'tasks-template-lite.md', featureDir, 'tasks.md', '# Tasks\n\nTODO: Fill in task breakdown\n');
    // Set the TTADK_FEATURE environment variable for the current session
    process.env.TTADK_FEATURE = featureName;
    console.log(`[ttadk] Debug: Feature: ${featureName}`);
    console.log(`[ttadk] Debug: Created spec file: ${specFilePath}`);
    console.log(`[ttadk] Debug: Created plan file: ${planFilePath}`);
    console.log(`[ttadk] Debug: Created tasks file: ${tasksFilePath}`);
    return {
        FEATURE_NAME: featureName,
        FEATURE_DIR: featureDir,
        SPEC_FILE_PATH: specFilePath,
        PLAN_FILE_PATH: planFilePath,
        TASKS_FILE_PATH: tasksFilePath,
        FEATURE_NUM: featureNum,
    };
}
// CLI mode
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {
        json: args.includes('--json'),
    };
    // Extract description from remaining args (after --json flag)
    const descriptionArgs = args.filter(arg => !arg.startsWith('--'));
    const description = descriptionArgs.join(' ') || undefined;
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`Usage: create-new-feature-lite [description] [--json]`);
        console.log(`  description  Optional feature description for naming`);
        console.log(`  --json       Output JSON format`);
        console.log(``);
        console.log(`This script:`);
        console.log(`  1. Generates feature name (YYYYMMDD-description format)`);
        console.log(`  2. Creates specs/{feature-name}/ directory`);
        console.log(`  3. Copies spec.md, plan.md, tasks.md templates to the directory`);
        process.exit(0);
    }
    createNewFeatureLite(description, options)
        .then(result => {
        if (options.json) {
            console.log(JSON.stringify(result));
        }
        else {
            console.log(`FEATURE_NAME: ${result.FEATURE_NAME}`);
            console.log(`FEATURE_DIR: ${result.FEATURE_DIR}`);
            console.log(`SPEC_FILE_PATH: ${result.SPEC_FILE_PATH}`);
            console.log(`PLAN_FILE_PATH: ${result.PLAN_FILE_PATH}`);
            console.log(`TASKS_FILE_PATH: ${result.TASKS_FILE_PATH}`);
            console.log(`FEATURE_NUM: ${result.FEATURE_NUM}`);
        }
        process.exit(0);
    })
        .catch(error => {
        console.error(`ERROR: ${error.message}`);
        process.exit(1);
    });
}
//# sourceMappingURL=create-new-feature-lite.js.map