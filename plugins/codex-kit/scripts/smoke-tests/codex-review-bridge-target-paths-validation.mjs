#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms a --target-paths entry is validated exactly as given (issue #533):
// an entry that trim() would change, or that is empty, is rejected rather than
// silently normalized into a valid-looking token. A well-formed single or
// comma-separated list must still pass the entry check.
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-target-paths-validation.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE_INVOKE = path.join(SCRIPT_DIR, "..", "..", "skills", "codex-review-bridge", "scripts", "bridge-invoke.mjs");
const ENTRY_ERROR = "target-paths entry is invalid";

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

function runBridge(tmpDir, instructionFile, targetPaths) {
  try {
    execFileSync(
      "node",
      [
        BRIDGE_INVOKE,
        "--reviewer-type", "test-reviewer",
        "--instruction-file", instructionFile,
        "--target-paths", targetPaths,
        "--execution-profile", "read-only",
        "--dispatch-id", "smoke-test",
        "--cwd", tmpDir
      ],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    return { stderr: "" };
  } catch (e) {
    return { stderr: e.stderr?.toString() ?? "" };
  }
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-paths-smoke-"));
fs.mkdirSync(path.join(tmpDir, "target"), { recursive: true });
fs.mkdirSync(path.join(tmpDir, "other"), { recursive: true });
const instructionFile = path.join(tmpDir, "reviewer.md");
fs.writeFileSync(instructionFile, "trusted instructions, outside the reviewed scope");

try {
  const rejected = [
    ["space after a comma (one name split on commas and spaces)", "target, NOTE, report"],
    ["leading space", " target"],
    ["trailing space", "target "],
    ["U+2028 padding", "target "],
    ["no-break space padding", " target"],
    ["empty entry between commas", "target,,other"],
    ["trailing comma", "target,"],
    ["leading comma", ",target"]
  ];
  for (const [label, value] of rejected) {
    console.log(`\n=== Rejected: ${label} ===`);
    const result = runBridge(tmpDir, instructionFile, value);
    check("rejected by the entry check", result.stderr.includes(ENTRY_ERROR), result.stderr);
  }

  const accepted = [
    ["single entry", "target"],
    ["two comma-separated entries without padding", "target,other"]
  ];
  for (const [label, value] of accepted) {
    console.log(`\n=== Accepted: ${label} ===`);
    const result = runBridge(tmpDir, instructionFile, value);
    check("not rejected by the entry check", !result.stderr.includes(ENTRY_ERROR), result.stderr);
  }
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
