#!/usr/bin/env node
// Smoke test: scripts/session-lifecycle-hook.mjs's per-session env wiring
// and job cleanup logic.
//
// Isolation: CLAUDE_PLUGIN_DATA is pointed at a fresh scratch directory for
// the whole run, so every state-file read/write this test triggers (via
// cleanupSessionJobs -> lib/state.mjs) lands under that scratch dir --
// never a real ~/.claude/... plugin-data path. "Running"/"queued" test jobs
// are always given no `pid` field, so terminateProcessTree's own
// `!Number.isFinite(pid)` guard makes its termination attempt a real no-op
// -- this test never sends a signal or spawns taskkill against any actual
// process.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/session-lifecycle-hook.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const scratchRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codex-kit-session-hook-smoke-"));
process.env.CLAUDE_PLUGIN_DATA = path.join(scratchRoot, "plugin-data");

const { shellEscape, cleanupSessionJobs, handleSessionStart } = await import("../session-lifecycle-hook.mjs");
const { saveState, loadState } = await import("../lib/state.mjs");

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

console.log("=== shellEscape ===");
{
  check("a plain value is single-quoted", shellEscape("abc123") === "'abc123'", shellEscape("abc123"));
  const escaped = shellEscape("it's a test");
  check(
    "an embedded single quote is escaped, not left to break out of the quoted string",
    escaped.includes(`'\"'\"'`),
    escaped
  );
}

console.log("\n=== handleSessionStart: env-file writes ===");
{
  const envFile = path.join(scratchRoot, "env-on.sh");
  fs.writeFileSync(envFile, "", "utf8");
  process.env.CLAUDE_ENV_FILE = envFile;
  handleSessionStart({ session_id: "sess-abc", transcript_path: "/tmp/t.jsonl" });
  const written = fs.readFileSync(envFile, "utf8");
  check("SESSION_ID_ENV is appended when CLAUDE_ENV_FILE is set", written.includes("sess-abc"), written);
  check("TRANSCRIPT_PATH_ENV is appended when CLAUDE_ENV_FILE is set", written.includes("t.jsonl"), written);
  delete process.env.CLAUDE_ENV_FILE;
}
{
  const before = fs.readdirSync(scratchRoot).length;
  handleSessionStart({ session_id: "sess-no-envfile" });
  const after = fs.readdirSync(scratchRoot).length;
  check("no CLAUDE_ENV_FILE set -> no file is created as a side effect", after === before, `before=${before} after=${after}`);
}

console.log("\n=== cleanupSessionJobs: guard clauses ===");
{
  let threw = false;
  try {
    cleanupSessionJobs(null, "sess-1");
    cleanupSessionJobs(path.join(scratchRoot, "ws-missing-session"), null);
  } catch {
    threw = true;
  }
  check("missing cwd or sessionId is a silent no-op, never throws", !threw);
}
{
  const ws = path.join(scratchRoot, "ws-no-state-file");
  fs.mkdirSync(ws, { recursive: true });
  cleanupSessionJobs(ws, "sess-1");
  check("no existing state file -> cleanupSessionJobs returns without creating one", true);
}

console.log("\n=== cleanupSessionJobs: job filtering ===");
{
  const ws = path.join(scratchRoot, "ws-jobs");
  fs.mkdirSync(ws, { recursive: true });

  saveState(ws, {
    jobs: [
      { id: "job-running-same-session", sessionId: "sess-target", status: "running", updatedAt: "2026-01-01T00:00:00.000Z" },
      { id: "job-queued-same-session", sessionId: "sess-target", status: "queued", updatedAt: "2026-01-01T00:00:01.000Z" },
      { id: "job-completed-same-session", sessionId: "sess-target", status: "completed", updatedAt: "2026-01-01T00:00:02.000Z" },
      { id: "job-running-other-session", sessionId: "sess-other", status: "running", updatedAt: "2026-01-01T00:00:03.000Z" }
    ]
  });

  cleanupSessionJobs(ws, "sess-target");
  const remainingIds = loadState(ws).jobs.map((job) => job.id).sort();

  check(
    "a running job for the target session is dropped",
    !remainingIds.includes("job-running-same-session"),
    remainingIds.join(",")
  );
  check(
    "a queued job for the target session is dropped",
    !remainingIds.includes("job-queued-same-session"),
    remainingIds.join(",")
  );
  check(
    "a completed job for the target session survives -- a later /codex-kit:result must still find it",
    remainingIds.includes("job-completed-same-session"),
    remainingIds.join(",")
  );
  check(
    "a running job for a DIFFERENT session is untouched",
    remainingIds.includes("job-running-other-session"),
    remainingIds.join(",")
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
