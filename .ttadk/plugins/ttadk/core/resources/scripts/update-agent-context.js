#!/usr/bin/env node
"use strict";
/**
 * Update Agent Context Script
 * Uses only Node.js built-in modules (no external dependencies)
 *
 * Updates agent context files (CLAUDE.md, etc.) with information from plan.md
 * Note: GEMINI.md support is currently disabled
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
exports.updateAgentContext = updateAgentContext;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const common_1 = require("./common");
// Agent-specific file paths
const AGENT_FILES = {
    claude: 'CLAUDE.md',
    gemini: '.gemini/GEMINI.md', // In .gemini/ to allow user /init at root
    copilot: '.github/copilot-instructions.md',
    cursor: '.cursor/rules/specify-rules.mdc',
    qwen: 'QWEN.md',
    agents: 'AGENTS.md',
    windsurf: '.windsurf/rules/specify-rules.md',
    kilocode: '.kilocode/rules/specify-rules.md',
    auggie: '.augment/rules/specify-rules.md',
    roo: '.roo/rules/specify-rules.md',
    q: 'AGENTS.md',
    coco: 'AGENTS.md',
    tmates: 'AGENTS.md',
};
/**
 * Parse plan.md to extract technical context
 */
function parsePlanMd(planPath) {
    if (!(0, common_1.existsSync)(planPath)) {
        return {
            language: '',
            framework: '',
            projectType: 'single',
            techStack: '',
        };
    }
    const content = fs.readFileSync(planPath, 'utf-8');
    const lines = content.split('\n');
    let language = '';
    let framework = '';
    let projectType = 'single';
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Extract Language/Version
        if (line.includes('**Language/Version**:')) {
            const match = line.match(/\*\*Language\/Version\*\*:\s*(.+)/);
            if (match) {
                language = match[1].trim();
                // Remove "or NEEDS CLARIFICATION" suffix
                language = language.replace(/\s+or\s+NEEDS CLARIFICATION.*$/, '').trim();
            }
        }
        // Extract Primary Dependencies (framework)
        if (line.includes('**Primary Dependencies**:')) {
            const match = line.match(/\*\*Primary Dependencies\*\*:\s*(.+)/);
            if (match) {
                framework = match[1].trim();
                framework = framework.replace(/\s+or\s+NEEDS CLARIFICATION.*$/, '').trim();
            }
        }
        // Extract Project Type
        if (line.includes('**Project Type**:')) {
            const match = line.match(/\*\*Project Type\*\*:\s*(.+)/);
            if (match) {
                projectType = match[1].trim().split(/[\s\-]/)[0]; // Get first word
            }
        }
    }
    // Format tech stack
    const parts = [];
    if (language && language !== 'NEEDS CLARIFICATION') {
        parts.push(language);
    }
    if (framework && framework !== 'NEEDS CLARIFICATION' && framework !== 'N/A') {
        parts.push(framework);
    }
    const techStack = parts.join(' + ');
    return { language, framework, projectType, techStack };
}
/**
 * Get project structure based on project type
 */
function getProjectStructure(projectType) {
    if (projectType.toLowerCase().includes('web')) {
        return 'backend/\nfrontend/\ntests/';
    }
    return 'src/\ntests/';
}
/**
 * Get commands for language
 */
function getCommandsForLanguage(language) {
    const lang = language.toLowerCase();
    if (lang.includes('python')) {
        return 'cd src && pytest && ruff check .';
    }
    else if (lang.includes('rust')) {
        return 'cargo test && cargo clippy';
    }
    else if (lang.includes('javascript') || lang.includes('typescript') || lang.includes('node')) {
        return 'npm test && npm run lint';
    }
    else if (lang.includes('go')) {
        return 'go test ./... && golangci-lint run';
    }
    else if (lang.includes('java')) {
        return './gradlew test && ./gradlew check';
    }
    return `# Add commands for ${language}`;
}
/**
 * Update or create agent file
 */
function updateAgentFile(agentFilePath, featureName, techStack, language, projectType, repoRoot) {
    const currentDate = new Date().toISOString().split('T')[0];
    const projectName = path.basename(repoRoot);
    // Read template
    const templatePath = path.join(repoRoot, '.ttadk', 'plugins', 'ttadk', 'core', 'resources', 'templates', 'agent-file-template.md');
    if (!(0, common_1.existsSync)(agentFilePath)) {
        // Create new file from template
        if (!(0, common_1.existsSync)(templatePath)) {
            console.warn(`[ttadk] Warning: Template not found at ${templatePath}, creating basic file`);
            const basicContent = `# ${projectName} Development Guidelines

Auto-generated from all feature plans. Last updated: ${currentDate}

## Active Technologies
- ${featureName}: ${techStack}

## Project Structure
\`\`\`
${getProjectStructure(projectType)}
\`\`\`

## Commands
${getCommandsForLanguage(language)}

## Code Style
${language}: Follow standard conventions

## Recent Changes
- ${featureName}: Added ${techStack}

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
`;
            // Ensure directory exists
            const dir = path.dirname(agentFilePath);
            if (!(0, common_1.existsSync)(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(agentFilePath, basicContent, 'utf-8');
            return;
        }
        // Use template
        let content = fs.readFileSync(templatePath, 'utf-8');
        content = content.replace(/\[PROJECT NAME\]/g, projectName);
        content = content.replace(/\[DATE\]/g, currentDate);
        content = content.replace(/\[EXTRACTED FROM ALL PLAN\.MD FILES\]/g, `- ${featureName}: ${techStack}`);
        content = content.replace(/\[ACTUAL STRUCTURE FROM PLANS\]/g, getProjectStructure(projectType));
        content = content.replace(/\[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES\]/g, getCommandsForLanguage(language));
        content = content.replace(/\[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE\]/g, `${language}: Follow standard conventions`);
        content = content.replace(/\[LAST 3 FEATURES AND WHAT THEY ADDED\]/g, `- ${featureName}: Added ${techStack}`);
        // Ensure directory exists
        const dir = path.dirname(agentFilePath);
        if (!(0, common_1.existsSync)(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(agentFilePath, content, 'utf-8');
    }
    else {
        // Update existing file
        let content = fs.readFileSync(agentFilePath, 'utf-8');
        // Update date
        content = content.replace(/Last updated: \d{4}-\d{2}-\d{2}/, `Last updated: ${currentDate}`);
        // Update Active Technologies section
        const techRegex = /## Active Technologies\n([\s\S]*?)(?=\n## )/;
        const techMatch = content.match(techRegex);
        if (techMatch) {
            const existingTech = techMatch[1];
            // Check if this feature already exists
            if (!existingTech.includes(featureName)) {
                const newTech = existingTech.trim() + `\n- ${featureName}: ${techStack}`;
                content = content.replace(techRegex, `## Active Technologies\n${newTech}\n\n`);
            }
            else {
                // Update existing entry
                const featureRegex = new RegExp(`- ${featureName}:.*`, 'g');
                content = content.replace(featureRegex, `- ${featureName}: ${techStack}`);
            }
        }
        // Update Recent Changes section (keep last 3)
        const changesRegex = /## Recent Changes\n([\s\S]*?)(?=\n<!-- MANUAL ADDITIONS START -->)/;
        const changesMatch = content.match(changesRegex);
        if (changesMatch) {
            const existingChanges = changesMatch[1].trim().split('\n').filter(line => line.trim().startsWith('-'));
            const newChange = `- ${featureName}: Added ${techStack}`;
            // Remove existing entry for this feature if exists
            const filteredChanges = existingChanges.filter(change => !change.includes(featureName));
            // Add new change and keep only last 3
            filteredChanges.unshift(newChange);
            const recentChanges = filteredChanges.slice(0, 3).join('\n');
            content = content.replace(changesRegex, `## Recent Changes\n${recentChanges}\n\n`);
        }
        fs.writeFileSync(agentFilePath, content, 'utf-8');
    }
}
/**
 * Main function
 */
async function updateAgentContext(agentType = 'claude', options = {}) {
    const repoRoot = (0, common_1.getRepoRoot)();
    const paths = (0, common_1.getFeaturePaths)();
    // Parse plan.md
    const { language, framework, projectType, techStack } = parsePlanMd(paths.IMPL_PLAN);
    if (!techStack) {
        // Provide detailed diagnostic information
        const details = [];
        // Show what was actually extracted
        details.push('Extracted values:');
        details.push(`  Language/Version: ${language || '(empty)'}`);
        details.push(`  Primary Dependencies: ${framework || '(empty)'}`);
        details.push(`  Project Type: ${projectType || '(empty)'}`);
        details.push('');
        // Analysis
        if (!language || language === 'NEEDS CLARIFICATION') {
            details.push('❌ Language/Version is missing or needs clarification');
        }
        if (!framework || framework === 'NEEDS CLARIFICATION' || framework === 'N/A') {
            details.push('❌ Primary Dependencies is missing, N/A, or needs clarification');
        }
        const errorMsg = [
            'Could not extract tech stack from plan.md.',
            '',
            'Required: At least one of the following fields in the Technical Context section:',
            '  - **Language/Version**: (e.g., Python 3.11, TypeScript 5.0)',
            '  - **Primary Dependencies**: (e.g., FastAPI, React)',
            '',
            ...details,
            '',
            `Plan file: ${paths.IMPL_PLAN}`,
            '',
            'Possible causes:',
            '  1. Technical Context section has placeholder values like [...]',
            '  2. Fields contain "NEEDS CLARIFICATION" text',
            '  3. Fields are missing the ** markdown bold markers',
            '  4. File was read before AI finished writing (timing issue)',
            '',
            'Action: Please ensure Technical Context section is filled with actual values.',
        ].join('\n');
        throw new Error(errorMsg);
    }
    // Determine agent file path
    const agentFileName = AGENT_FILES[agentType.toLowerCase()] || AGENT_FILES.claude;
    const agentFilePath = path.join(repoRoot, agentFileName);
    // Update agent file
    updateAgentFile(agentFilePath, paths.FEATURE_NAME, techStack, language, projectType, repoRoot);
    return {
        AGENT_FILE: agentFilePath,
        FEATURE_NAME: paths.FEATURE_NAME,
        TECH_STACK: techStack,
    };
}
// CLI mode
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {
        json: args.includes('--json'),
    };
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`Usage: update-agent-context [agent_type] [--json]

Agent types:
  claude    - Update CLAUDE.md (default)
  copilot   - Update .github/copilot-instructions.md
  cursor    - Update .cursor/rules/specify-rules.mdc
  qwen      - Update QWEN.md
  agents    - Update AGENTS.md
  windsurf  - Update .windsurf/rules/specify-rules.md
  kilocode  - Update .kilocode/rules/specify-rules.md
  auggie    - Update .augment/rules/specify-rules.md
  roo       - Update .roo/rules/specify-rules.md
  q         - Update AGENTS.md
  coco      - Update AGENTS.md
  tmates    - Update AGENTS.md

Options:
  --json    Output in JSON format
  --help    Show this help message
`);
        process.exit(0);
    }
    const agentType = args.find(arg => !arg.startsWith('--')) || 'claude';
    updateAgentContext(agentType, options)
        .then(result => {
        if (options.json) {
            console.log(JSON.stringify(result));
        }
        else {
            console.log(`AGENT_FILE: ${result.AGENT_FILE}`);
            console.log(`FEATURE_NAME: ${result.FEATURE_NAME}`);
            console.log(`TECH_STACK: ${result.TECH_STACK}`);
        }
        process.exit(0);
    })
        .catch(error => {
        console.error(`ERROR: ${error.message}`);
        process.exit(1);
    });
}
//# sourceMappingURL=update-agent-context.js.map