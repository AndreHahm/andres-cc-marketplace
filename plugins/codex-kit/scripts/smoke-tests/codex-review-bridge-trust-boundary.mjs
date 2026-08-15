#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms the trust-boundary containment check added to bridge-invoke.mjs
// rejects a reviewer instruction file that resolves inside the target paths
// under review (the self-referential case: a PR that could otherwise rewrite
// the instructions that judge it), and does not false-positive on a
// legitimately trusted instruction file living outside the target scope.
// Also confirms the CODEX_KIT_REVIEW_MODEL env-var validation fails fast on
// a malformed value before any Codex call is attempted.
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-trust-boundary.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE_INVOKE = path.join(SCRIPT_DIR, "..", "..", "skills", "codex-review-bridge", "scripts", "bridge-invoke.mjs");

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

function runBridge(tmpDir, instructionFile, targetPaths, dispatchId = "smoke-test", extraEnv = {}) {
  try {
    execFileSync(
      "node",
      [
        BRIDGE_INVOKE,
        "--reviewer-type", "test-reviewer",
        "--instruction-file", instructionFile,
        "--target-paths", targetPaths,
        "--execution-profile", "read-only",
        "--dispatch-id", dispatchId,
        "--cwd", tmpDir
      ],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, ...extraEnv } }
    );
    return { ok: true };
  } catch (e) {
    return { ok: false, stderr: e.stderr?.toString() ?? "" };
  }
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-smoke-"));
const targetDir = path.join(tmpDir, "target");
fs.mkdirSync(targetDir, { recursive: true });

console.log("=== Self-referential instruction file (inside target-paths) ===");
{
  const selfReferentialFile = path.join(targetDir, "reviewer.md");
  fs.writeFileSync(selfReferentialFile, "these are the instructions, and they live inside the reviewed scope");
  const result = runBridge(tmpDir, selfReferentialFile, "target");
  check(
    "rejected before any Codex call, with the expected containment-check message",
    !result.ok && result.stderr.includes("instruction-file resolves inside"),
    result.stderr
  );
}

console.log("\n=== Exact-match instruction file (instruction file IS the only target path) ===");
{
  const exactMatchFile = path.join(tmpDir, "self.md");
  fs.writeFileSync(exactMatchFile, "instructions");
  const result = runBridge(tmpDir, exactMatchFile, path.relative(tmpDir, exactMatchFile) || "self.md");
  check(
    "rejected when instruction-file exactly equals the (only) target path",
    !result.ok && result.stderr.includes("instruction-file resolves inside"),
    result.stderr
  );
}

console.log("\n=== Trusted instruction file outside target-paths ===");
{
  const trustedFile = path.join(tmpDir, "trusted-reviewer.md");
  fs.writeFileSync(trustedFile, "trusted, outside-scope instructions");
  const result = runBridge(tmpDir, trustedFile, "target");
  // This call will still fail overall in a smoke-test environment (no real
  // Codex sandbox wired up here) -- what matters is that it fails for a
  // DIFFERENT reason than the containment check, proving no false positive.
  check(
    "does NOT trigger the containment-check rejection (may still fail later for unrelated reasons)",
    !result.stderr.includes("instruction-file resolves inside"),
    result.stderr
  );
}

console.log("\n=== Prefix-similar but not-actually-nested target path (the isWithin boundary case) ===");
{
  const siblingDir = path.join(tmpDir, "target-extra");
  fs.mkdirSync(siblingDir, { recursive: true });
  const siblingFile = path.join(siblingDir, "reviewer.md");
  fs.writeFileSync(siblingFile, "instructions in a sibling dir whose name happens to share a prefix");
  const result = runBridge(tmpDir, siblingFile, "target");
  check(
    "target-extra/reviewer.md is NOT treated as nested inside target/ (no false positive on prefix match)",
    !result.stderr.includes("instruction-file resolves inside"),
    result.stderr
  );
}

console.log("\n=== CODEX_KIT_REVIEW_MODEL validation ===");
{
  const trustedFile = path.join(tmpDir, "model-test-reviewer.md");
  fs.writeFileSync(trustedFile, "trusted instructions for the model-override check");

  const invalid = runBridge(tmpDir, trustedFile, "target", "smoke-test-model", {
    CODEX_KIT_REVIEW_MODEL: "not a valid model slug!"
  });
  check(
    "an invalid CODEX_KIT_REVIEW_MODEL is rejected before any Codex call",
    !invalid.ok && invalid.stderr.includes("CODEX_KIT_REVIEW_MODEL must match"),
    invalid.stderr
  );

  const valid = runBridge(tmpDir, trustedFile, "target", "smoke-test-model", {
    CODEX_KIT_REVIEW_MODEL: "gpt-5-mini"
  });
  check(
    "a valid CODEX_KIT_REVIEW_MODEL passes the format check (may still fail later for unrelated reasons, e.g. no real Codex CLI in this environment)",
    !valid.stderr.includes("CODEX_KIT_REVIEW_MODEL must match"),
    valid.stderr
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
