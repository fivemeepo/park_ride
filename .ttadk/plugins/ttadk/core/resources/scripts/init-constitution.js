#!/usr/bin/env node
/**
 * Initialize Constitution Script
 * If .ttadk/memory/constitution.md exists, skip.
 * Otherwise, copy constitution-template.md to .ttadk/memory/constitution.md
 */
const fs = require("fs");
const path = require("path");
const { existsSync, getRepoRoot } = require("./common");

const repoRoot = getRepoRoot();
const memoryDir = path.join(repoRoot, ".ttadk", "memory");
const constitutionPath = path.join(memoryDir, "constitution.md");
const templatePath = path.join(repoRoot, ".ttadk", "plugins", "ttadk", "core", "resources", "templates", "constitution-template.md");

// Already exists, skip
if (existsSync(constitutionPath)) {
    console.log(JSON.stringify({ status: "exists", path: constitutionPath }));
    process.exit(0);
}

// Ensure memory directory exists
if (!existsSync(memoryDir)) {
    fs.mkdirSync(memoryDir, { recursive: true });
}

// Copy template
fs.copyFileSync(templatePath, constitutionPath);
console.log(JSON.stringify({ status: "created", path: constitutionPath }));
