#!/usr/bin/env node
// Smoke test: scripts/lib/cdx-sandbox-check.mjs's evaluateProbeResult (issue #549)
//
// /cdx-setup's sandbox probe used to ask Codex to "reply with exactly: ok" and treated only a
// non-zero exit as failure. On Windows with Codex 0.162.1 a sandbox that cannot start a process
// still exits 0 and only says so in its final message (issue #545), so the old probe reported a
// broken sandbox as working. The probe now needs Codex to run a command that reads a file holding
// a random token that appears nowhere in the prompt; this test exercises the decision function on
// finished-run shapes, offline.
//
// The failure message below is the real final message captured from Codex 0.162.1 on Windows 11
// (2026-10-12); the success shapes are synthetic.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/cdx-sandbox-check.mjs

import crypto from "node:crypto";
import { evaluateProbeResult } from "../lib/cdx-sandbox-check.mjs";

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

// Generated per run, like the probe's own token, so no static high-entropy literal sits in this file.
const TOKEN = crypto.randomBytes(8).toString("hex");
const run = (overrides) => ({ status: 0, stdout: "", stderr: "", error: null, ...overrides });

console.log("=== A sandbox that ran the command is viable ===");
{
  const r = evaluateProbeResult(run({ stdout: `${TOKEN}\n` }), TOKEN);
  check("exit 0 and the token in Codex's answer is viable", r.viable === true, JSON.stringify(r));
  const r2 = evaluateProbeResult(run({ stdout: `The file contains: ${TOKEN}` }), TOKEN);
  check("the token inside a sentence is still viable", r2.viable === true, JSON.stringify(r2));
}

console.log("\n=== Exit 0 without the token is NOT viable (the #549 gap) ===");
{
  const real = "`dir` could not run because process creation failed; no output line was produced.";
  const r = evaluateProbeResult(run({ stdout: real }), TOKEN);
  check("the real Codex 0.162.1 Windows failure message is not viable", r.viable === false, JSON.stringify(r));
  check("its detail says the command could not be run and quotes Codex's answer", /could not read the probe file/.test(r.detail) && r.detail.includes("process creation failed"), r.detail);
  check("an empty answer is not viable", evaluateProbeResult(run({ stdout: "" }), TOKEN).viable === false);
  check(
    "the token appearing only in stderr (not in Codex's answer) is not viable",
    evaluateProbeResult(run({ stdout: "ok", stderr: `exec output ${TOKEN}` }), TOKEN).viable === false
  );
  check(
    "a different token is not viable",
    evaluateProbeResult(run({ stdout: "not-the-token" }), TOKEN).viable === false
  );
}

console.log("\n=== Failures that were already caught keep being caught ===");
{
  const r = evaluateProbeResult(run({ status: 1, stderr: "ERROR: CreateProcessAsUserW failed: 1920" }), TOKEN);
  check("a non-zero exit is not viable", r.viable === false);
  check("its detail carries the stderr text", r.detail.includes("CreateProcessAsUserW"), r.detail);
  check(
    "a non-zero exit with no output still reports the exit code",
    evaluateProbeResult(run({ status: 3 }), TOKEN).detail === "exit 3"
  );
  check(
    "a long failure keeps the tail (the reason), not the head (the banner)",
    evaluateProbeResult(run({ status: 1, stderr: "banner ".repeat(200) + "REASON-AT-END" }), TOKEN).detail.endsWith("REASON-AT-END")
  );
  check("an empty token is never viable", evaluateProbeResult(run({ stdout: "anything" }), "").viable === false);
  const e = evaluateProbeResult(run({ status: 0, error: new Error("spawn codex ENOENT") }), TOKEN);
  check("a spawn error is not viable and carries its message", e.viable === false && e.detail.includes("ENOENT"), JSON.stringify(e));
}

console.log("\n=== Secrets never reach the report ===");
{
  const secret = "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz0123456789";
  const r = evaluateProbeResult(run({ status: 1, stderr: secret }), TOKEN);
  check("a secret-shaped value in stderr is redacted from the detail", !r.detail.includes("sk-abcdefghijklmnopqrstuvwxyz"), r.detail);
  const r2 = evaluateProbeResult(run({ stdout: `no luck ${secret}` }), TOKEN);
  check("a secret-shaped value in Codex's answer is redacted from the detail", !r2.detail.includes("sk-abcdefghijklmnopqrstuvwxyz"), r2.detail);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
