#!/usr/bin/env node
// Smoke test: skills/plugin-marketplace-review/SKILL.md's structural
// invariants
//
// This skill is documentation only -- "Status: policy documentation, not an
// execution mechanism" -- and its own text explains that an earlier
// revision's broader Bash(node:*) grant was a real least-privilege
// violation a security review caught, fixed by removing all execution
// grants rather than narrowing them. That's the one safety-relevant
// invariant worth a regression guard here: no Bash/Skill grant ever creeps
// back into this skill's allowed-tools. This test also checks the cited
// function names against the real orchestrator
// (scripts/marketplace_ci/review.py) and that the test files it names as
// coverage evidence actually exist -- the same reference-currency pattern
// codex-prompt-protocol-references.mjs uses for its own skill.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/plugin-marketplace-review-references.mjs

import fs from "node:fs";
import path from "node:path";

let pass = 0;
let fail = 0;

// Shared by the main invariant and both controlled negatives below
// (CodeRabbit review, PR #112, 2026-08-24) -- splits and normalizes each
// allowed-tools list entry so a bare, unquoted `Skill` (valid YAML flow-
// sequence syntax: `allowed-tools: [Read, Grep, Glob, Skill]`) is caught,
// not just the quoted `"Skill"` form the prior regex-only check matched.
function hasNoBashOrSkillGrant(content) {
  const match = content.match(/allowed-tools:\s*\[([^\]]*)\]/);
  if (!match) return false;
  const grants = match[1]
    .split(",")
    .map((grant) => grant.trim().replace(/^["']|["']$/g, ""));
  return !grants.some((grant) => grant === "Skill" || grant.startsWith("Bash"));
}

function check(label, condition, detail = "") {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${label}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${label}${detail ? " -- " + detail : ""}`);
  }
}

const repoRoot = path.resolve("../..");
const skillPath = path.resolve("skills/plugin-marketplace-review/SKILL.md");

function assertInvariants(content, label) {
  const results = {};

  results.disableModelInvocation = /disable-model-invocation:\s*true/.test(content);

  results.noBashOrSkillGrant = hasNoBashOrSkillGrant(content);

  results.documentsThePastViolation = content.includes(
    "an earlier revision's broader `Bash(node:*)` grant was a real least-privilege violation"
  );

  results.failsClosedOnTypedFailure = content.includes(
    "the orchestrator fails closed — treats the affected component as unreviewed and blocks the PR pending human review"
  );

  console.log(`\n=== ${label} ===`);
  for (const [name, ok] of Object.entries(results)) {
    check(name, ok);
  }
  return results;
}

const realContent = fs.readFileSync(skillPath, "utf8");
assertInvariants(realContent, "Real SKILL.md");

console.log("\n=== Cited functions resolve in scripts/marketplace_ci/review.py ===");
{
  const reviewPyPath = path.join(repoRoot, "scripts/marketplace_ci/review.py");
  check("scripts/marketplace_ci/review.py exists", fs.existsSync(reviewPyPath));
  const reviewPy = fs.readFileSync(reviewPyPath, "utf8");
  const citedFunctions = ["derive_review_scope", "dispatch_reviewers"];
  for (const fn of citedFunctions) {
    check(
      `${fn} is cited in SKILL.md and defined in review.py`,
      realContent.includes(fn) && new RegExp(`def ${fn}\\(`).test(reviewPy)
    );
  }
}

console.log("\n=== Referenced test files exist ===");
{
  const testFiles = [
    "tests/marketplace_ci/test_review.py",
    "tests/marketplace_ci/test_cli.py"
  ];
  for (const rel of testFiles) {
    const p = path.join(repoRoot, rel);
    check(`${rel} exists`, fs.existsSync(p), p);
    check(`${rel} is referenced in SKILL.md`, realContent.includes(path.basename(rel)));
  }
}

console.log("\n=== evals/plugin-marketplace-review/evals.json exists ===");
{
  const evalPath = path.join(repoRoot, "evals/plugin-marketplace-review/evals.json");
  check("evals/plugin-marketplace-review/evals.json exists", fs.existsSync(evalPath));
}

console.log("\n=== Controlled negative: a reintroduced Bash grant is caught ===");
{
  const tampered = realContent.replace(
    'allowed-tools: ["Read", "Grep", "Glob"]',
    'allowed-tools: ["Read", "Grep", "Glob", "Bash(node:*)"]'
  );
  check(
    "the no-Bash/Skill-grant invariant fails on a tampered copy with Bash reintroduced",
    hasNoBashOrSkillGrant(tampered) === false
  );
}

console.log("\n=== Controlled negative: a bare (unquoted) Skill grant is caught ===");
{
  const tampered = realContent.replace(
    'allowed-tools: ["Read", "Grep", "Glob"]',
    "allowed-tools: [Read, Grep, Glob, Skill]"
  );
  check(
    "the no-Bash/Skill-grant invariant fails on a tampered copy with a bare Skill entry",
    hasNoBashOrSkillGrant(tampered) === false
  );
}

console.log("\n=== Controlled negative: a renamed/removed cited function is caught ===");
{
  const reviewPyPath = path.join(repoRoot, "scripts/marketplace_ci/review.py");
  const reviewPy = fs.readFileSync(reviewPyPath, "utf8");
  const bogusResolved = new RegExp(`def thisFunctionDoesNotExist_derive_review_scope\\(`).test(reviewPy);
  check("a deliberately-mismatched function name is correctly reported as unresolved", bogusResolved === false);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
