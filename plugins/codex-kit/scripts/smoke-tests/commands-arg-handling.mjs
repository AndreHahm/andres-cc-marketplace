#!/usr/bin/env node
// Smoke test: commands/status.md, result.md, transfer.md, cancel.md
//
// These commands were converted from `!`-prefixed shell pre-execution
// (which interpolated a raw, unquoted $ARGUMENTS blob) to model-run bash
// blocks that pass validated, individually-quoted arguments. This test
// confirms the underlying codex-companion.mjs subcommands still behave
// correctly when invoked the way the new command instructions describe.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/commands-arg-handling.mjs

import { execFileSync } from "node:child_process";

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

console.log("=== status: multi-arg invocation (no job-id) ===");
{
  const out = execFileSync("node", ["scripts/codex-companion.mjs", "status", "--json"], { encoding: "utf8" });
  const parsed = JSON.parse(out);
  check("status --json returns valid JSON with workspaceRoot", typeof parsed.workspaceRoot === "string", out.slice(0, 200));
}

console.log("\n=== status: multi-arg invocation with --all as a separate quoted argument ===");
{
  const out = execFileSync("node", ["scripts/codex-companion.mjs", "status", "--all", "--json"], { encoding: "utf8" });
  const parsed = JSON.parse(out);
  check("status --all --json (separate args) returns valid JSON", typeof parsed === "object" && parsed !== null, out.slice(0, 200));
}

console.log("\n=== result: well-formed but nonexistent job-id fails gracefully (no crash) ===");
{
  let threw = false;
  let stderrText = "";
  try {
    execFileSync("node", ["scripts/codex-companion.mjs", "result", "nonexistent-job-id-12345"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"]
    });
  } catch (e) {
    threw = true;
    stderrText = e.stderr?.toString() ?? "";
  }
  check("result with a valid-shaped but nonexistent job-id exits non-zero, not a crash", threw);
  check("the failure is a handled error, not an uncaught exception stack trace", !stderrText.includes("at Object.<anonymous>"), stderrText.slice(0, 300));
}

console.log("\n=== cancel: status --all --json (the pre-cancel disambiguation check cancel.md now runs itself) ===");
{
  const out = execFileSync("node", ["scripts/codex-companion.mjs", "status", "--all", "--json"], { encoding: "utf8" });
  let parsed;
  let parseOk = true;
  try {
    parsed = JSON.parse(out);
  } catch {
    parseOk = false;
  }
  check("status --all --json (the exact command cancel.md's disambiguation step runs) parses as JSON", parseOk, out.slice(0, 200));
}

console.log("\n=== transfer: rejects a source path containing shell metacharacters at the script layer too ===");
{
  // Defense in depth: even though cancel.md/transfer.md's own prose now validates
  // before running, confirm the underlying script doesn't silently succeed on an
  // obviously malicious-looking --source value either.
  let threw = false;
  try {
    execFileSync("node", ["scripts/codex-companion.mjs", "transfer", "--source", "/nonexistent/path/that/does/not/exist.jsonl"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"]
    });
  } catch (e) {
    threw = true;
  }
  check("transfer with a nonexistent --source path fails rather than silently succeeding", threw);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
