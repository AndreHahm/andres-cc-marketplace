#!/usr/bin/env node
// Smoke test: skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs
//
// Confirms every pre-flight gate short-circuits BEFORE any Codex exec is
// attempted: disabled-by-default, a tracked local override being ignored
// (fail-closed), a repository-boundary violation, a secret file anywhere
// under a directory target (not just a caller-supplied filename argument --
// this is the case an earlier draft's git-ls-files-based check silently
// missed, since a .env is normally gitignored, never tracked), and an
// instruction file resolving inside a target path.
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-windows-guardrails-preflight.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const GUARDED_DISPATCH = path.join(SCRIPT_DIR, "..", "..", "skills", "codex-windows-guardrails", "scripts", "guarded-dispatch.mjs");

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

function git(args, cwd) {
  execFileSync("git", args, { cwd, stdio: ["ignore", "ignore", "ignore"] });
}

function runDispatch(repoRoot, targetPaths, instructionFile, dispatchId = "smoke-test") {
  try {
    const stdout = execFileSync(
      "node",
      [
        GUARDED_DISPATCH,
        "--reviewer-type", "test-reviewer",
        "--instruction-file", instructionFile,
        "--target-paths", targetPaths,
        "--dispatch-id", dispatchId,
        "--repo-root", repoRoot
      ],
      { encoding: "utf8" }
    );
    return JSON.parse(stdout);
  } catch (e) {
    return JSON.parse(e.stdout.toString());
  }
}

const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codex-windows-guardrails-smoke-"));
git(["init", "-q"], repoRoot);
fs.writeFileSync(path.join(repoRoot, "target.md"), "content");
git(["add", "target.md"], repoRoot);
git(["-c", "user.email=t@t.com", "-c", "user.name=Test", "commit", "-q", "-m", "init"], repoRoot);

const instructionFile = path.join(os.tmpdir(), "codex-windows-guardrails-smoke-instr.md");
fs.writeFileSync(instructionFile, "trusted instructions");

console.log("=== Disabled by default (no config at all) ===");
{
  const result = runDispatch(repoRoot, repoRoot, instructionFile);
  check(
    "rejected with guardrails_disabled, no exec attempted",
    result.ok === false && result.category === "guardrails_disabled",
    JSON.stringify(result)
  );
}

console.log("\n=== Untracked local override (enabled: true) is honored, reaches a later check ===");
{
  fs.mkdirSync(path.join(repoRoot, ".claude"), { recursive: true });
  fs.writeFileSync(
    path.join(repoRoot, ".claude", "codex-windows-guardrails.local.json"),
    JSON.stringify({ windows_guardrails: { enabled: true, central_policy_version: "1" } })
  );
  const result = runDispatch(repoRoot, repoRoot, instructionFile);
  check(
    "no longer guardrails_disabled -- override was honored (next real gate is instruction-containment, since instructionFile is outside repoRoot here that passes too, so this should proceed toward exec and hit whatever the environment's codex resolution does)",
    result.category !== "guardrails_disabled",
    JSON.stringify(result)
  );
}

console.log("\n=== Tracked local override is ignored (fail-closed) ===");
{
  git(["add", "-f", ".claude/codex-windows-guardrails.local.json"], repoRoot);
  git(["-c", "user.email=t@t.com", "-c", "user.name=Test", "commit", "-q", "-m", "track override"], repoRoot);
  const result = runDispatch(repoRoot, repoRoot, instructionFile);
  check(
    "reverts to guardrails_disabled once the override file is tracked",
    result.ok === false && result.category === "guardrails_disabled",
    JSON.stringify(result)
  );
}

// From here on, re-untrack the override (simulate a fresh untracked one) so
// the remaining checks can exercise the enabled path.
git(["rm", "--cached", "-q", ".claude/codex-windows-guardrails.local.json"], repoRoot);
git(["-c", "user.email=t@t.com", "-c", "user.name=Test", "commit", "-q", "-m", "untrack override"], repoRoot);

console.log("\n=== Repository-boundary violation (target outside repo root) ===");
{
  const result = runDispatch(repoRoot, os.tmpdir(), instructionFile);
  check(
    "rejected with repository_boundary_violation",
    result.ok === false && result.category === "repository_boundary_violation",
    JSON.stringify(result)
  );
}

console.log("\n=== Secret file under a DIRECTORY target, untracked (the real-world .env case) ===");
{
  fs.writeFileSync(path.join(repoRoot, ".env"), "SECRET=1");
  const result = runDispatch(repoRoot, repoRoot, instructionFile);
  check(
    "rejected with secret_file_in_scope -- proves real filesystem traversal, not git ls-files (which would miss an untracked .env)",
    result.ok === false && result.category === "secret_file_in_scope" && /\.env/.test(result.detail),
    JSON.stringify(result)
  );
  fs.rmSync(path.join(repoRoot, ".env"));
}

console.log("\n=== Instruction file resolving inside a target path ===");
{
  const result = runDispatch(repoRoot, repoRoot, path.join(repoRoot, "target.md"));
  check(
    "rejected -- instruction file cannot be one of the files under review",
    result.ok === false && /instruction-file resolves inside/.test(result.detail),
    JSON.stringify(result)
  );
}

console.log("\n=== Invalid dispatch-id (charset validation, lost when the bridge CLI was bypassed, then restored) ===");
{
  const result = runDispatch(repoRoot, repoRoot, instructionFile, "not a valid id!");
  check(
    "rejected with invalid_arguments before any check or exec",
    result.ok === false && result.category === "invalid_arguments" && /dispatch-id/.test(result.detail),
    JSON.stringify(result)
  );
}

console.log("\n=== Case-insensitive secret match on Windows (uppercase .ENV) ===");
{
  fs.writeFileSync(path.join(repoRoot, ".ENV"), "SECRET=1");
  const result = runDispatch(repoRoot, repoRoot, instructionFile);
  const expectMatch = process.platform === "win32";
  check(
    expectMatch
      ? "uppercase .ENV is still rejected on Windows (case-insensitive match)"
      : "case-sensitive match on non-Windows is a documented, deliberate platform difference -- not asserting either way here",
    !expectMatch || (result.ok === false && result.category === "secret_file_in_scope"),
    JSON.stringify(result)
  );
  fs.rmSync(path.join(repoRoot, ".ENV"));
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
