#!/usr/bin/env node
// Smoke test: skills/codex-prompt-protocol/SKILL.md's reference table
//
// codex-prompt-protocol is disable-model-invocation: true and has no runtime
// behavior of its own -- every other codex-kit component Reads its reference
// files directly instead of duplicating their content. Its own "Testing &
// Validation" section names three concrete, mechanically-checkable
// invariants: every table row's file exists, and a cited symbol name in
// invocation-protocol.md resolves to something real in codex-companion.mjs /
// scripts/lib. This test checks both, plus the frontmatter invariants that
// keep this skill non-invocable.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-prompt-protocol-references.mjs

import fs from "node:fs";
import path from "node:path";

let pass = 0;
let fail = 0;

function check(label, condition, detail = "") {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${label}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${label}${detail ? " -- " + detail : ""}`);
  }
}

const skillDir = path.resolve("skills/codex-prompt-protocol");
const skillPath = path.join(skillDir, "SKILL.md");
const skillContent = fs.readFileSync(skillPath, "utf8");

console.log("=== Frontmatter invariants ===");
check("disable-model-invocation: true is set", /disable-model-invocation:\s*true/.test(skillContent));
check(
  "allowed-tools is scoped to Read only",
  /allowed-tools:\s*\["Read"\]/.test(skillContent)
);

console.log("\n=== Reference table: every row's file exists ===");
const referenceFiles = [
  "references/prompt-blocks.md",
  "references/invocation-protocol.md",
  "references/evaluation-framework.md",
  "references/cli-reference.md",
  "references/error-taxonomy.md",
  "references/shared-skill-conventions.md"
];
for (const rel of referenceFiles) {
  const p = path.join(skillDir, rel);
  check(`${rel} exists`, fs.existsSync(p));
  check(`${rel} is referenced in SKILL.md's table`, skillContent.includes(rel));
}

console.log("\n=== invocation-protocol.md: cited symbols resolve in codex-companion.mjs / scripts/lib ===");
const citedSymbols = [
  "handleReviewCommand",
  "handleStatus",
  "handleTask",
  "handleCancel",
  "handleResult",
  "handleTransfer",
  "handleTaskWorker",
  "executeReviewRun",
  "runAppServerReview",
  "runCodexExec",
  "waitForSingleJobSnapshot",
  "parseCommandInput",
  "normalizeArgv",
  "readTaskPrompt",
  "readStdinIfPiped",
  "ensureGitRepository",
  "getCodexAvailability",
  "buildAuthStatus",
  "validateNativeReviewRequest",
  "resolveClaudeSessionPath",
  "renderTransferResult",
  "requireTaskRequest",
  "splitRawArgumentString",
  "enqueueBackgroundTask"
];

const invocationProtocol = fs.readFileSync(path.join(skillDir, "references/invocation-protocol.md"), "utf8");
const scriptsRoot = path.resolve("scripts");
const scriptFiles = [
  path.join(scriptsRoot, "codex-companion.mjs"),
  ...fs.readdirSync(path.join(scriptsRoot, "lib")).map((f) => path.join(scriptsRoot, "lib", f))
];
const scriptsSource = scriptFiles.map((f) => fs.readFileSync(f, "utf8")).join("\n");

let citedNotInDoc = 0;
for (const sym of citedSymbols) {
  if (!invocationProtocol.includes(sym)) {
    citedNotInDoc += 1;
  }
}
check(
  "every symbol in this test's own list is actually cited in invocation-protocol.md",
  citedNotInDoc === 0,
  `${citedNotInDoc} of ${citedSymbols.length} not found in the doc -- update this test's list to match the doc`
);

const funcPattern = (sym) => new RegExp(`\\b(function|async function)\\s+${sym}\\b|\\bexport\\s+(async\\s+)?function\\s+${sym}\\b`);
let unresolved = [];
for (const sym of citedSymbols) {
  if (!funcPattern(sym).test(scriptsSource)) {
    unresolved.push(sym);
  }
}
check(
  "every cited symbol resolves to a real function in codex-companion.mjs/scripts/lib",
  unresolved.length === 0,
  unresolved.join(", ")
);

console.log("\n=== Controlled negative: an unresolvable symbol name is correctly flagged ===");
{
  const bogusSymbols = [...citedSymbols, "thisFunctionDoesNotExistAnywhere"];
  const bogusUnresolved = bogusSymbols.filter((sym) => !funcPattern(sym).test(scriptsSource));
  check(
    "a deliberately-injected nonexistent symbol is caught as unresolved",
    bogusUnresolved.length === 1 && bogusUnresolved[0] === "thisFunctionDoesNotExistAnywhere"
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
