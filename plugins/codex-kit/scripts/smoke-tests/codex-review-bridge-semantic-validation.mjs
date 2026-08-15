#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms semanticallyValidate's `components[]` field (added alongside the
// single-string `location` field in ENVELOPE_SCHEMA) validates each listed
// component against the same containment/existence check `location` already
// gets -- closing a real gap where a multi-file finding (a dependency
// cycle, a bidirectional coupling, a cross-file consistency mismatch) had
// no schema field to cite its second file in, forcing the model to cram a
// semicolon-joined path list into `location` instead, which then failed
// validation as an unresolvable single path.
//
// Imports the pure functions directly (bridge-invoke.mjs's entry-point
// guard means main() never fires on import) rather than going through the
// full CLI subprocess, since this logic only runs after a successful Codex
// response -- no real Codex CLI call needed to exercise it this way.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-review-bridge-semantic-validation.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { semanticallyValidate } from "../../skills/codex-review-bridge/scripts/bridge-invoke.mjs";

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

const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-semantic-"));
const skillADir = path.join(repoRoot, "skill-a");
const skillBDir = path.join(repoRoot, "skill-b");
fs.mkdirSync(skillADir, { recursive: true });
fs.mkdirSync(skillBDir, { recursive: true });
fs.writeFileSync(path.join(skillADir, "SKILL.md"), "skill a");
fs.writeFileSync(path.join(skillBDir, "SKILL.md"), "skill b");

const targetPaths = ["skill-a", "skill-b"];
const baseEnvelope = (findings) => ({
  dispatch: { id: "smoke-test", reviewer: "dependency-reviewer" },
  findings
});

console.log("=== A finding with a valid components[] entry (both in-scope) passes ===");
{
  const result = semanticallyValidate(
    baseEnvelope([
      {
        id: "C1",
        location: "skill-a/SKILL.md:1",
        components: ["skill-b/SKILL.md"]
      }
    ]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check("validation passes when both location and components[] resolve in-scope", result.ok, JSON.stringify(result));
}

console.log("\n=== A finding with an out-of-scope components[] entry is rejected ===");
{
  const result = semanticallyValidate(
    baseEnvelope([
      {
        id: "C2",
        location: "skill-a/SKILL.md:1",
        components: ["../outside/SKILL.md"]
      }
    ]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check(
    "rejected with a components-specific error message, not the generic location one",
    !result.ok && result.detail.includes("nonexistent component"),
    JSON.stringify(result)
  );
}

console.log("\n=== A finding with a nonexistent components[] entry is rejected ===");
{
  const result = semanticallyValidate(
    baseEnvelope([
      {
        id: "C3",
        location: "skill-a/SKILL.md:1",
        components: ["skill-b/DOES-NOT-EXIST.md"]
      }
    ]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check("rejected when a components[] entry doesn't exist on disk", !result.ok, JSON.stringify(result));
}

console.log("\n=== components[] is optional -- a finding with only location still validates ===");
{
  const result = semanticallyValidate(
    baseEnvelope([{ id: "M1", location: "skill-a/SKILL.md:1" }]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check("omitting components[] entirely still passes (backward compatible)", result.ok, JSON.stringify(result));
}

console.log("\n=== The exact pre-fix failure mode: a semicolon-joined path list crammed into location alone still fails ===");
{
  const result = semanticallyValidate(
    baseEnvelope([
      {
        id: "M2",
        location: "scoped component set: skill-a/SKILL.md; skill-b/SKILL.md"
      }
    ]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check(
    "a multi-path string stuffed into location alone (the old workaround) is still correctly rejected -- proves the fix is components[], not a looser location check",
    !result.ok,
    JSON.stringify(result)
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
