#!/usr/bin/env node
// Smoke test: skills/codex-plan-loop/SKILL.md's structural invariants
//
// This skill's own "Testing & Validation" section correctly documents that
// it has no persisted smoke test because each phase's Codex payload depends
// on actual plan/diff content. What IS mechanically checkable is the
// SKILL.md's own text: phase ordering, the rollback-anchor requirement
// (Phase 4), the concrete two-condition convergence exit (Phase 6), and
// that scratch artifacts are always written under
// ${CLAUDE_PLUGIN_DATA}/codex-loop/, never the repo root.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-plan-loop-invariants.mjs

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

function assertInvariants(content, label) {
  const results = {};

  results.phasesInOrder = (() => {
    const headers = [
      "## Phase 1: Plan",
      "## Phase 2: Validate (Codex)",
      "## Phase 3: Decision gate",
      "## Phase 4: Implement",
      "## Phase 5: Review (Codex)",
      "## Phase 6: Iterate — convergence check"
    ];
    const positions = headers.map((h) => content.indexOf(h));
    if (positions.some((p) => p === -1)) return false;
    for (let i = 1; i < positions.length; i += 1) {
      if (positions[i] <= positions[i - 1]) return false;
    }
    return true;
  })();

  results.rollbackAnchorInPhase4 = content.includes("**Before the first edit, capture a rollback anchor:** `git rev-parse HEAD`");

  results.resumeLastInPhase6 = content.includes("codex-companion.mjs task --resume-last");

  results.neverRawCodexExec = content.includes("never the raw `codex exec` CLI");

  results.concreteConvergenceCondition = content.includes(
    "stop iterating when either (a) two consecutive rounds report only Minor/Info findings, or (b) all Critical/Major findings from the prior round are confirmed fixed in this round's review"
  );

  results.persistingFindingDiscussedNotAutoResolved = content.includes(
    "Discuss with the user (not silently auto-resolve) if a Critical/Major finding persists past 3 rounds"
  );

  results.scratchUnderPluginData = (() => {
    const codeSpans = content.match(/`[^`]*`/g) || [];
    const scratchSpans = codeSpans.filter((s) => s.includes("codex-loop/"));
    return (
      scratchSpans.length > 0 &&
      scratchSpans.every((s) => s.includes("${CLAUDE_PLUGIN_DATA}/codex-loop/"))
    );
  })();

  results.contentTrustBoundaryInPhase2And5 = (() => {
    const phase2Start = content.indexOf("## Phase 2: Validate (Codex)");
    const phase3Start = content.indexOf("## Phase 3: Decision gate");
    const phase5Start = content.indexOf("## Phase 5: Review (Codex)");
    const phase6Start = content.indexOf("## Phase 6: Iterate");
    const phase2Body = content.slice(phase2Start, phase3Start);
    const phase5Body = content.slice(phase5Start, phase6Start);
    return phase2Body.includes("<content_trust_boundary>") && phase5Body.includes("<content_trust_boundary>");
  })();

  console.log(`\n=== ${label} ===`);
  for (const [name, ok] of Object.entries(results)) {
    check(name, ok);
  }
  return results;
}

const skillPath = path.resolve("skills/codex-plan-loop/SKILL.md");
const realContent = fs.readFileSync(skillPath, "utf8");
assertInvariants(realContent, "Real SKILL.md");

console.log("\n=== Controlled negative: removing the rollback-anchor instruction is caught ===");
{
  const tampered = realContent.replace(
    "**Before the first edit, capture a rollback anchor:** `git rev-parse HEAD`",
    "Start implementing directly."
  );
  const stillPresent = tampered.includes("**Before the first edit, capture a rollback anchor:** `git rev-parse HEAD`");
  check("the rollback-anchor invariant fails on a tampered copy", stillPresent === false);
}

console.log("\n=== Controlled negative: a scratch path missing the env-var prefix is caught ===");
{
  const tampered = realContent.replace(
    'mkdir -p "${CLAUDE_PLUGIN_DATA}/codex-loop"',
    'mkdir -p "codex-loop"'
  );
  const codeSpans = tampered.match(/`[^`]*`/g) || [];
  const scratchSpans = codeSpans.filter((s) => s.includes("codex-loop/") || s.includes("codex-loop\""));
  const stillClean =
    scratchSpans.length > 0 && scratchSpans.every((s) => s.includes("${CLAUDE_PLUGIN_DATA}/codex-loop"));
  check("the scratch-path invariant fails when a bare repo-relative path is used", stillClean === false);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
