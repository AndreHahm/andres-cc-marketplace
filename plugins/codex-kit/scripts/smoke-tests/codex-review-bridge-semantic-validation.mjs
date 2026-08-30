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
import { semanticallyValidate, isTotalInspectionFailure } from "../../skills/codex-review-bridge/scripts/bridge-invoke.mjs";

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

console.log("\n=== Issue #236/#111: an out-of-scope components[] entry is dropped, not the whole envelope ===");
{
  const envelope = baseEnvelope([
    {
      id: "C2",
      location: "skill-a/SKILL.md:1",
      components: ["../outside/SKILL.md"]
    }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("envelope still validates (ok: true)", result.ok, JSON.stringify(result));
  check("the finding itself survives", envelope.findings.length === 1 && envelope.findings[0].id === "C2", JSON.stringify(envelope.findings));
  check("the out-of-scope components[] entry is stripped from the finding", envelope.findings[0].components.length === 0, JSON.stringify(envelope.findings[0]));
  check(
    "the drop is recorded in inspection_limits, not silently discarded",
    (envelope.inspection_limits ?? []).some((note) => note.includes("component")),
    JSON.stringify(envelope.inspection_limits)
  );
}

console.log("\n=== Issue #236/#111: a nonexistent components[] entry is dropped the same way ===");
{
  const envelope = baseEnvelope([
    {
      id: "C3",
      location: "skill-a/SKILL.md:1",
      components: ["skill-b/DOES-NOT-EXIST.md"]
    }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("envelope still validates when a components[] entry doesn't exist on disk", result.ok, JSON.stringify(result));
  check("the finding survives with the bad component stripped", envelope.findings.length === 1 && envelope.findings[0].components.length === 0, JSON.stringify(envelope.findings));
}

console.log("\n=== Issue #236/#111: a finding with an out-of-scope location is dropped, but sibling findings survive ===");
{
  const envelope = baseEnvelope([
    { id: "L1", location: "../outside/SKILL.md" },
    { id: "L2", location: "skill-a/SKILL.md:1" }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("envelope still validates when one finding's location is out-of-scope", result.ok, JSON.stringify(result));
  check("only the out-of-scope finding is dropped", envelope.findings.length === 1 && envelope.findings[0].id === "L2", JSON.stringify(envelope.findings));
  check(
    "the dropped finding is recorded in inspection_limits",
    (envelope.inspection_limits ?? []).length > 0,
    JSON.stringify(envelope.inspection_limits)
  );
}

console.log("\n=== Protocol-integrity failures still reject the entire envelope ===");
{
  const result = semanticallyValidate(
    baseEnvelope([{ id: "D1", location: "skill-a/SKILL.md:1" }]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "wrong-reviewer", repoRoot }
  );
  check("a dispatch.reviewer mismatch still rejects the whole envelope", !result.ok, JSON.stringify(result));
}
{
  const result = semanticallyValidate(
    baseEnvelope([
      { id: "DUP", location: "skill-a/SKILL.md:1" },
      { id: "DUP", location: "skill-b/SKILL.md:1" }
    ]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check("a duplicate finding id still rejects the whole envelope", !result.ok, JSON.stringify(result));
}

console.log("\n=== components[] is optional -- a finding with only location still validates ===");
{
  const result = semanticallyValidate(
    baseEnvelope([{ id: "M1", location: "skill-a/SKILL.md:1" }]),
    { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot }
  );
  check("omitting components[] entirely still passes (backward compatible)", result.ok, JSON.stringify(result));
}

console.log("\n=== The exact pre-fix failure mode: a semicolon-joined path list crammed into location alone still never validates as a real finding ===");
{
  // Post issues #236/#111: an invalid `location` no longer fails the whole
  // envelope (see the drop-not-reject tests above), so this now surfaces as
  // the finding being silently dropped rather than as `ok: false` -- still
  // proving the fix is the dedicated components[] field, not a looser
  // location check, since this shape never becomes a validated finding
  // either way. Post fail-closed-on-total-loss fix: since this is the
  // envelope's ONLY finding, dropping it leaves zero survivors, so the whole
  // envelope is now correctly rejected too (a stronger proof of the same
  // point, not a regression -- see the dedicated fail-closed tests below for
  // the mixed-survivors case, which still returns ok: true).
  const envelope = baseEnvelope([
    {
      id: "M2",
      location: "scoped component set: skill-a/SKILL.md; skill-b/SKILL.md"
    }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("the envelope is rejected (its only finding was dropped, zero survivors)", !result.ok, JSON.stringify(result));
  check(
    "a multi-path string stuffed into location alone (the old workaround) never becomes a validated finding -- proves the fix is components[], not a looser location check",
    envelope.findings.length === 0,
    JSON.stringify(envelope.findings)
  );
}

console.log("\n=== cross-model-review finding: a dropped-location note never leaks raw citation text that could satisfy isTotalInspectionFailure ===");
{
  // A malicious/malformed Codex response whose only finding has a location
  // string crafted to contain process-start-failure phrasing. Pre-fix, this
  // text was echoed verbatim into the dropped-finding's inspection_limits
  // note; post-fix, the note is a fixed static string with no citation text.
  // This is also the envelope's only finding, so it's correctly rejected as
  // a whole by the fail-closed-on-total-loss guard -- the inspection_limits
  // safety property below is checked independent of that outer ok:false.
  const envelope = baseEnvelope([
    { id: "X1", location: "../outside/CreateProcessAsUserW failed to start process.md" }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("the envelope is rejected (its only finding was dropped, zero survivors)", !result.ok, JSON.stringify(result));
  check("the crafted finding is dropped, leaving zero findings", envelope.findings.length === 0, JSON.stringify(envelope.findings));
  check(
    "the dropped-location note contains no raw citation text (no 'CreateProcessAsUserW', no 'failed to start process')",
    (envelope.inspection_limits ?? []).every(
      (note) => !note.includes("CreateProcessAsUserW") && !/failed to start.*process/i.test(note)
    ),
    JSON.stringify(envelope.inspection_limits)
  );
  check(
    "isTotalInspectionFailure does NOT misclassify this as a total sandbox failure",
    !isTotalInspectionFailure(envelope),
    JSON.stringify(envelope.inspection_limits)
  );
}
{
  // Same crafted phrasing, but on a dropped components[] citation instead of location.
  const envelope = baseEnvelope([
    {
      id: "X2",
      location: "skill-a/SKILL.md:1",
      components: ["../outside/CreateProcessAsUserW.md"]
    }
  ]);
  semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check(
    "a dropped components[] citation's note contains no raw 'CreateProcessAsUserW' text",
    (envelope.inspection_limits ?? []).every((note) => !note.includes("CreateProcessAsUserW")),
    JSON.stringify(envelope.inspection_limits)
  );
}

console.log("\n=== Round 2 of the same cross-model-review finding: a crafted finding.id (also model-controlled, unconstrained) never leaks into the dropped-location note either ===");
{
  const envelope = baseEnvelope([
    { id: "CreateProcessAsUserW failed to start process", location: "../outside/SKILL.md" }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("the envelope is rejected (its only finding was dropped, zero survivors)", !result.ok, JSON.stringify(result));
  check("the crafted finding is dropped, leaving zero findings", envelope.findings.length === 0, JSON.stringify(envelope.findings));
  check(
    "the dropped-location note contains no raw finding.id text either",
    (envelope.inspection_limits ?? []).every(
      (note) => !note.includes("CreateProcessAsUserW") && !/failed to start.*process/i.test(note)
    ),
    JSON.stringify(envelope.inspection_limits)
  );
  check(
    "isTotalInspectionFailure does NOT misclassify this as a total sandbox failure",
    !isTotalInspectionFailure(envelope),
    JSON.stringify(envelope.inspection_limits)
  );
}

console.log("\n=== Devin's finding: components stays null (not coerced to []) when it started null ===");
{
  const envelope = baseEnvelope([
    { id: "N1", location: "skill-a/SKILL.md:1", components: null }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("envelope still validates", result.ok, JSON.stringify(result));
  check(
    "a single-file finding's components stays null, not coerced to []",
    envelope.findings.length === 1 && envelope.findings[0].components === null,
    JSON.stringify(envelope.findings)
  );
}
{
  // A multi-file finding whose only components[] entry gets dropped is
  // still distinguishable from the null case above: components becomes []
  // (an array that started as an array), never null.
  const envelope = baseEnvelope([
    { id: "N2", location: "skill-a/SKILL.md:1", components: ["../outside/SKILL.md"] }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check("envelope still validates", result.ok, JSON.stringify(result));
  check(
    "a multi-file finding with all components dropped becomes [] (an array), not null",
    envelope.findings.length === 1 && Array.isArray(envelope.findings[0].components) && envelope.findings[0].components.length === 0,
    JSON.stringify(envelope.findings)
  );
}

console.log("\n=== Codex's P1 finding: fail closed when every finding is dropped, not just some ===");
{
  // Two findings, both with out-of-scope locations -- every finding in the
  // envelope is garbage/hallucinated, not just one among several real ones.
  const envelope = baseEnvelope([
    { id: "G1", location: "../outside/SKILL.md" },
    { id: "G2", location: "../also-outside/SKILL.md" }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check(
    "the whole envelope is rejected, not silently downgraded to an empty-but-ok findings list",
    !result.ok && result.category === "semantic_validation_failure",
    JSON.stringify(result)
  );
}
{
  // A genuine "approve, nothing to report" response never had findings to
  // begin with -- the fail-closed guard must not fire on this case.
  const envelope = baseEnvelope([]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check(
    "a genuinely empty findings list (nothing to report) still validates -- the fail-closed guard doesn't fire when there was nothing to drop",
    result.ok,
    JSON.stringify(result)
  );
}
{
  // Mixed case: one real finding survives alongside one dropped garbage
  // finding -- the envelope must still validate (issues #236/#111's whole
  // point), proving the fail-closed guard only fires on TOTAL loss.
  const envelope = baseEnvelope([
    { id: "R1", location: "../outside/SKILL.md" },
    { id: "R2", location: "skill-a/SKILL.md:1" }
  ]);
  const result = semanticallyValidate(envelope, { targetPaths, dispatchId: "smoke-test", reviewerType: "dependency-reviewer", repoRoot });
  check(
    "a mix of one dropped and one surviving finding still validates (only total loss fails closed)",
    result.ok && envelope.findings.length === 1 && envelope.findings[0].id === "R2",
    JSON.stringify(result)
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
