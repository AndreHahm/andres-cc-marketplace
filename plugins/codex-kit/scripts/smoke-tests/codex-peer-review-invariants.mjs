#!/usr/bin/env node
// Smoke test: skills/codex-peer-review/SKILL.md's structural invariants
//
// This skill's own "Testing & Validation" section correctly documents that
// it has no persisted smoke test because its output depends on Claude's own
// position and Codex's live response. What IS mechanically checkable is the
// SKILL.md's own text: the two safety-relevant invariants named in its
// "Concrete scenarios to check" (never ask before Round 1/Round 2; the
// #1 command-selection mistake stays documented) and the --resume-last
// invocation form this skill depends on for Round 2.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-peer-review-invariants.mjs

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

  results.roundsInOrder = (() => {
    const r1 = content.indexOf("## Round 1");
    const r2 = content.indexOf("## Round 2");
    const esc = content.indexOf("## Escalation");
    return r1 !== -1 && r2 !== -1 && esc !== -1 && r1 < r2 && r2 < esc;
  })();

  results.neverAsksBeforeRounds = content.includes(
    "Never ask before Round 1 or Round 2"
  );

  results.diffCommandDocumented = (content.match(/`[^`]*review --base <ref>[^`]*`/) || []).length > 0;

  results.designCommandDocumented = (content.match(/`[^`]*codex-companion\.mjs task`/) || []).length > 0;

  results.resumeLastForm = content.includes("task --resume-last");

  results.noBareResumeThreadIdForm = !content.includes("--resume <threadId>") ||
    content.includes("there is no `--resume <threadId>` form");

  results.alwaysDispatchViaSubagent = content.includes(
    "Always dispatch via a subagent"
  );

  results.neverInventTiebreak = content.includes("Never invent a tiebreak");

  console.log(`\n=== ${label} ===`);
  for (const [name, ok] of Object.entries(results)) {
    check(name, ok);
  }
  return results;
}

const skillPath = path.resolve("skills/codex-peer-review/SKILL.md");
const realContent = fs.readFileSync(skillPath, "utf8");
assertInvariants(realContent, "Real SKILL.md");

console.log("\n=== Controlled negative: removing the never-ask invariant is caught ===");
{
  const tampered = realContent.replace(
    "Never ask before Round 1 or Round 2 — only the escalation and final-output steps involve the user directly, keeping the loop itself autonomous once invoked.",
    "Ask the user before Round 1 and Round 2."
  );
  const stillPresent = tampered.includes("Never ask before Round 1 or Round 2");
  check("the never-ask invariant fails on a tampered copy with the gate removed", stillPresent === false);
}

console.log("\n=== Controlled negative: dropping the subagent-dispatch requirement is caught ===");
{
  const tampered = realContent.replace("Always dispatch via a subagent", "Run this inline");
  const stillPresent = tampered.includes("Always dispatch via a subagent");
  check("the subagent-dispatch invariant fails on a tampered copy", stillPresent === false);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
