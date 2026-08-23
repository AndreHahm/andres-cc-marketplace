#!/usr/bin/env node
// Smoke test: skills/codex-session-lookup/scripts/find-session-id.py and
// inspect-session-file.py
//
// Both scripts are real, deterministic Python (a named exception to this
// plugin's declared .mjs language, per CONTRIBUTING.md) that operate on a
// caller-supplied file path (--history for find-session-id.py, a positional
// path for inspect-session-file.py) -- never a hardcoded, untestable
// ~/.codex/ lookup. This test spawns both against scratch fixtures only,
// never a real ~/.codex/ directory, and covers this skill's own documented
// "Concrete scenarios to check": truncation at 140 chars unless --full,
// --id-only output, and a missing/malformed file producing a clear error.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-session-lookup-scripts.mjs

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
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

const findScript = path.resolve("skills/codex-session-lookup/scripts/find-session-id.py");
const inspectScript = path.resolve("skills/codex-session-lookup/scripts/inspect-session-file.py");

function runPython(script, args) {
  const result = spawnSync("python3", [script, ...args], { encoding: "utf8" });
  if (result.error && result.error.code === "ENOENT") {
    return spawnSync("python", [script, ...args], { encoding: "utf8" });
  }
  return result;
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-session-lookup-smoke-"));

console.log("=== find-session-id.py ===");
{
  const historyPath = path.join(tmpDir, "history.jsonl");
  const longPrompt = "x".repeat(200);
  const lines = [
    JSON.stringify({ session_id: "sess-old", ts: 1000, text: "refactor the login form" }),
    JSON.stringify({ session_id: "sess-new", ts: 2000, text: longPrompt }),
    JSON.stringify({ session_id: "sess-noquery", ts: 1500, text: "unrelated entry" }),
    "not valid json, must be skipped",
    JSON.stringify({ session_id: "sess-notext" })
  ];
  fs.writeFileSync(historyPath, lines.join("\n") + "\n");

  const truncated = runPython(findScript, ["--history", historyPath, "--query", longPrompt.slice(0, 5)]);
  check("query match exits 0", truncated.status === 0, truncated.stderr);
  check(
    "long prompt text is truncated to 140 chars (+ ellipsis) by default",
    truncated.stdout.trim().split("\t")[2]?.length === 140,
    JSON.stringify(truncated.stdout)
  );
  check("truncated output ends with an ellipsis", truncated.stdout.trim().endsWith("..."));
  check("truncated output includes the matched session id", truncated.stdout.includes("sess-new"));

  const full = runPython(findScript, ["--history", historyPath, "--query", longPrompt.slice(0, 5), "--full"]);
  check(
    "--full suppresses truncation",
    full.stdout.trim().split("\t")[2]?.length === 200,
    String(full.stdout.trim().split("\t")[2]?.length)
  );

  const last = runPython(findScript, ["--history", historyPath, "--last"]);
  check("--last returns exactly one row", last.stdout.trim().split("\n").length === 1);
  check("--last returns the most recent entry by ts", last.stdout.includes("sess-new"));

  const malformedSkipped = runPython(findScript, ["--history", historyPath, "--limit", "10"]);
  check(
    "malformed JSON lines are silently skipped, not crashed on",
    malformedSkipped.status === 0 && !malformedSkipped.stderr.includes("Traceback")
  );
  check(
    "an entry missing session_id/text is excluded from results",
    !malformedSkipped.stdout.includes("sess-notext")
  );

  const missing = runPython(findScript, ["--history", path.join(tmpDir, "does-not-exist.jsonl")]);
  check("a missing history file exits 1", missing.status === 1);
  check("a missing history file reports a clear error on stderr", missing.stderr.includes("not found"));
}

console.log("\n=== inspect-session-file.py ===");
{
  const rolloutPath = path.join(tmpDir, "rollout-test.jsonl");
  const rolloutLines = [
    JSON.stringify({ type: "other", payload: {} }),
    JSON.stringify({
      type: "session_meta",
      payload: { id: "rollout-session-42", timestamp: "2026-08-23T00:00:00Z", cwd: "/scratch/project" }
    })
  ];
  fs.writeFileSync(rolloutPath, rolloutLines.join("\n") + "\n");

  const full = runPython(inspectScript, [rolloutPath]);
  check("full metadata print exits 0", full.status === 0, full.stderr);
  check("full metadata includes the session id", full.stdout.includes("rollout-session-42"));
  check("full metadata includes the cwd", full.stdout.includes("/scratch/project"));

  const idOnly = runPython(inspectScript, [rolloutPath, "--id-only"]);
  check(
    "--id-only prints only the session id, nothing else",
    idOnly.stdout.trim() === "rollout-session-42"
  );

  const jsonPath = path.join(tmpDir, "session-test.json");
  fs.writeFileSync(jsonPath, JSON.stringify({ session: { id: "json-session-7" } }));
  const jsonResult = runPython(inspectScript, [jsonPath, "--id-only"]);
  check(".json (non-jsonl) session file is also handled", jsonResult.stdout.trim() === "json-session-7");

  const missingFile = runPython(inspectScript, [path.join(tmpDir, "nope.jsonl")]);
  check("a missing session file exits 1", missingFile.status === 1);
  check("a missing session file reports a clear error on stderr", missingFile.stderr.includes("not found"));

  const emptyPath = path.join(tmpDir, "empty.jsonl");
  fs.writeFileSync(emptyPath, "\n");
  const emptyResult = runPython(inspectScript, [emptyPath]);
  check("a rollout file with no session_meta exits 1, not a silent empty success", emptyResult.status === 1);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
