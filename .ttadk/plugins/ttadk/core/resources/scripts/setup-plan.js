#!/usr/bin/env node
"use strict";
/**
 * Setup Plan Script
 * Uses only Node.js built-in modules (no external dependencies)
 *
 * Creates plan.md from template for the current feature.
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
exports.setupPlan = setupPlan;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const common_1 = require("./common");
async function setupPlan(options = {}) {
    const paths = (0, common_1.getFeaturePaths)();
    // Log current feature info
    if (!options.json) {
        console.log(`[ttadk] Using feature: ${paths.FEATURE_NAME}`);
    }
    // Ensure the feature directory exists
    if (!(0, common_1.existsSync)(paths.FEATURE_DIR)) {
        fs.mkdirSync(paths.FEATURE_DIR, { recursive: true });
    }
    // Copy plan template if it exists
    const repoRoot = (0, common_1.getRepoRoot)();
    const template = path.join(repoRoot, '.ttadk', 'plugins', 'ttadk', 'core', 'resources', 'templates', 'plan-template.md');
    if ((0, common_1.existsSync)(template)) {
        const content = fs.readFileSync(template, 'utf-8');
        fs.writeFileSync(paths.IMPL_PLAN, content, 'utf-8');
        if (!options.json) {
            console.log(`Copied plan template to ${paths.IMPL_PLAN}`);
        }
    }
    else {
        console.warn(`Warning: Plan template not found at ${template}`);
        // Create a basic plan file if template doesn't exist
        fs.writeFileSync(paths.IMPL_PLAN, '# Implementation Plan\n\nTODO: Fill in implementation details\n', 'utf-8');
    }
    return {
        FEATURE_SPEC: paths.FEATURE_SPEC,
        IMPL_PLAN: paths.IMPL_PLAN,
        SPECS_DIR: paths.FEATURE_DIR,
        FEATURE_NAME: paths.FEATURE_NAME,
        HAS_GIT: paths.HAS_GIT ? 'true' : 'false',
    };
}
// CLI mode
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {
        json: args.includes('--json'),
    };
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`Usage: setup-plan [--json]
  --json    Output results in JSON format
  --help    Show this help message`);
        process.exit(0);
    }
    setupPlan(options)
        .then(result => {
        if (options.json) {
            console.log(JSON.stringify(result));
        }
        else {
            console.log(`FEATURE_SPEC: ${result.FEATURE_SPEC}`);
            console.log(`IMPL_PLAN: ${result.IMPL_PLAN}`);
            console.log(`SPECS_DIR: ${result.SPECS_DIR}`);
            console.log(`FEATURE_NAME: ${result.FEATURE_NAME}`);
            console.log(`HAS_GIT: ${result.HAS_GIT}`);
        }
        process.exit(0);
    })
        .catch(error => {
        console.error(`ERROR: ${error.message}`);
        process.exit(1);
    });
}
//# sourceMappingURL=setup-plan.js.map