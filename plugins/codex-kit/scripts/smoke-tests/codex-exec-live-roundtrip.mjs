#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's runCodexExec, against the REAL
// codex binary.
//
// Every other smoke test in this suite proves codex-kit's own scaffolding
// (arg parsing, schema validation, prompt assembly, RPC auth, Windows
// spawn escaping) without ever completing a real `codex exec` round-trip --
// documented explicitly in this directory's README ("these are static/
// mechanical checks... they do not call the real Codex CLI or consume API
// quota"). That left a real gap: nothing persisted actually proved
// runCodexExec's stdin-piping, --output-schema/--output-last-message
// contract, and findSchemaViolation checking worked end-to-end against a
// live Codex response rather than an in-memory fixture. Added in response
// to running-a-full-retrospective:M7 (2026-08-18), which found ~10 direct
// `codex` invocations across the 2026-08-15..2026-08-18 window, all
// exploratory (--version/--help/login status), no live `codex exec`
// round-trip anywhere.
//
// Requires a real, authenticated `codex` CLI on PATH -- unlike every other
// file in this directory, this one is NOT dependency-free. When codex is
// unavailable or unauthenticated it SKIPs (not FAILs) via runCodexExec's own
// CLI_UNAVAILABLE/AUTH_UNAVAILABLE typed-failure categories, so this test
// stays safe to include in the default sweep across environments that don't
// have a live, logged-in codex install -- it only asserts on the shape of a
// response it actually received. Uses --sandbox read-only and a scratch cwd
// so the live call can't write anywhere on disk. Spends a small amount of
// real API quota when it runs live -- see README.md's "When to re-run".
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-live-roundtrip.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runCodexExec, FAILURE_CATEGORIES } from "../lib/codex-exec.mjs";

let pass = 0;
let fail = 0;
let skip = 0;

function check(label, condition, detail = "") {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${label}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${label}${detail ? " -- " + detail : ""}`);
  }
}

function skipScenario(label, reason) {
  skip += 1;
  console.log(`SKIP  ${label} -- ${reason}`);
}

const ACK_VALUE = "codex-kit-smoke-test-ok";

const schema = {
  type: "object",
  additionalProperties: false,
  required: ["ack"],
  properties: {
    ack: { type: "string" }
  }
};

const prompt = [
  "This is an automated smoke test of a tool integration. Do not run any",
  "commands, read any files, or use any tools -- just respond directly.",
  "",
  `Respond with only a JSON object matching this exact shape: {"ack": "${ACK_VALUE}"}`,
  `Set "ack" to the literal string "${ACK_VALUE}" and nothing else.`
].join("\n");

console.log("=== Live codex exec round-trip (real binary, real API call) ===");

const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-kit-live-smoke-"));
// codex refuses to run outside a trusted (git) directory unless the caller
// passes --skip-git-repo-check, which runCodexExec deliberately never sets
// (confirmed live, 2026-08-18: a bare tmp dir fails fast with "Not inside a
// trusted directory"). A throwaway git repo inside the scratch dir satisfies
// that check without depending on -- or touching -- this repo's own git state.
execFileSync("git", ["init", "-q"], { cwd: scratchDir, stdio: ["ignore", "ignore", "ignore"] });

try {
  const result = await runCodexExec({
    prompt,
    schema,
    sandbox: "read-only",
    cwd: scratchDir,
    timeoutMs: 90000,
    dispatchId: "smoke-live-roundtrip"
  });

  if (result.ok) {
    check("runCodexExec resolves ok:true against the real binary", true);
    check(
      "response JSON matches the requested schema and ack value",
      result.data && result.data.ack === ACK_VALUE,
      JSON.stringify(result.data)
    );
  } else if (
    result.category === FAILURE_CATEGORIES.CLI_UNAVAILABLE ||
    result.category === FAILURE_CATEGORIES.AUTH_UNAVAILABLE
  ) {
    skipScenario(
      "live codex exec round-trip",
      `no live, authenticated codex CLI in this environment (${result.category}): ${result.detail}`
    );
  } else {
    check(
      "live codex exec round-trip",
      false,
      `unexpected failure category ${result.category}: ${result.detail}`
    );
  }
} finally {
  fs.rmSync(scratchDir, { recursive: true, force: true });
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed, ${skip} skipped ===`);
process.exit(fail > 0 ? 1 : 0);
