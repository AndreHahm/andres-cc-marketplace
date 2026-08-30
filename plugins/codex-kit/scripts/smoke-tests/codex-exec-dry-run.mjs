#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's `dryRun` mode
//
// runCodexExec's `dryRun` option lets a caller (codex-review-bridge's
// bridge-invoke.mjs, codex-windows-guardrails' guarded-dispatch.mjs) build
// the real prompt, resolve the real `codex` invocation (Windows shim
// resolution / POSIX PATH lookup), and confirm every pre-flight guard fires
// correctly -- without ever spawning `codex`. This test proves three things
// the two callers' own smoke tests can't: (1) a dry run never spawns a
// process even when a real, executable `codex` stub is on PATH -- the
// stub writes a sentinel file if it's ever actually run, and this test
// asserts that file never appears; (2) `resolveDryRunInvocation`'s win32
// branch delegates to the same `buildSpawnInvocation` a real dispatch would
// use (via the injectable `platform` param, so this runs identically on any
// CI runner); (3) the returned `wouldRun.prompt` is redacted the same way a
// real failure's `detail` already is.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-dry-run.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runCodexExec, resolveDryRunInvocation, buildSpawnInvocation } from "../lib/codex-exec.mjs";

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

// process.env coerces every assigned value to a string, so restoring an
// originally-unset var with `process.env.X = undefined` would leave it set
// to the literal string "undefined" instead of unset (same helper
// codex-exec-windows-spawn.mjs's own smoke test already uses).
function restoreEnv(key, value) {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

const schema = { type: "object", additionalProperties: false, required: ["ok"], properties: { ok: { type: "boolean" } } };

console.log("=== resolveDryRunInvocation: win32 branch delegates to buildSpawnInvocation ===");
{
  const args = ["exec", "--sandbox", "read-only"];
  const cwd = process.cwd();
  const viaDryRun = resolveDryRunInvocation("codex", args, cwd, "win32");
  const viaReal = buildSpawnInvocation("codex", args, { cwd, stdio: ["pipe", "pipe", "pipe"] }, "win32");
  check(
    "dry-run resolution matches what a real win32 dispatch would build",
    JSON.stringify(viaDryRun) === JSON.stringify(viaReal),
    `dryRun=${JSON.stringify(viaDryRun)} real=${JSON.stringify(viaReal)}`
  );
}

console.log("\n=== resolveDryRunInvocation: non-win32 branch finds an executable on PATH ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-dry-run-"));
  const savedPath = process.env.PATH;
  const stubPath = path.join(scratchDir, "codex");
  try {
    fs.writeFileSync(stubPath, "#!/bin/sh\necho stub\n");
    fs.chmodSync(stubPath, 0o755);
    process.env.PATH = scratchDir + path.delimiter + (savedPath || "");

    const resolved = resolveDryRunInvocation("codex", ["exec"], scratchDir, "linux");
    check("finds an executable stub on PATH", resolved.resolved === true && resolved.command === stubPath, JSON.stringify(resolved));

    const notFound = resolveDryRunInvocation("this-tool-does-not-exist-anywhere", ["exec"], scratchDir, "linux");
    check("reports not_found for a command that doesn't exist anywhere on PATH", notFound.resolved === false && notFound.reason === "not_found", JSON.stringify(notFound));
  } finally {
    restoreEnv("PATH", savedPath);
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== runCodexExec({ dryRun: true }): resolves and redacts, never spawns ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-dry-run-"));
  const savedPath = process.env.PATH;
  const sentinelFile = path.join(scratchDir, "SPAWNED");
  const stubName = process.platform === "win32" ? "codex.cmd" : "codex";
  const stubPath = path.join(scratchDir, stubName);
  try {
    // A real, executable stub that proves it was actually invoked by
    // writing a sentinel file -- if runCodexExec's dryRun branch ever
    // spawned this (instead of just resolving its path), this file would
    // exist afterward.
    if (process.platform === "win32") {
      fs.writeFileSync(stubPath, `@echo off\r\necho spawned> "${sentinelFile}"\r\n`);
    } else {
      fs.writeFileSync(stubPath, `#!/bin/sh\necho spawned > "${sentinelFile}"\n`);
      fs.chmodSync(stubPath, 0o755);
    }
    process.env.PATH = scratchDir + path.delimiter + (savedPath || "");

    const result = await runCodexExec({
      prompt: "test prompt containing AKIA1234567890ABCDEF, a secret-shaped token",
      schema,
      sandbox: "read-only",
      cwd: scratchDir,
      dispatchId: "smoke-dry-run",
      dryRun: true
    });

    check("dry run reports ok: true", result.ok === true, JSON.stringify(result));
    check("dry run reports dryRun: true", result.dryRun === true, JSON.stringify(result));
    check("wouldRun resolves to the stub on PATH", result.wouldRun && (result.wouldRun.command === stubPath || result.wouldRun.args.some((a) => String(a).includes(stubName))), JSON.stringify(result.wouldRun));
    check("wouldRun.prompt redacts the secret-shaped token", result.wouldRun && !result.wouldRun.prompt.includes("AKIA1234567890ABCDEF"), result.wouldRun && result.wouldRun.prompt);
    check("wouldRun carries the real sandbox/dispatchId/promptLength", result.wouldRun.sandbox === "read-only" && result.wouldRun.dispatchId === "smoke-dry-run" && typeof result.wouldRun.promptLength === "number");
    check("the stub was never actually spawned", !fs.existsSync(sentinelFile));
  } finally {
    restoreEnv("PATH", savedPath);
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== runCodexExec({ dryRun: true }): still reports CLI_UNAVAILABLE when codex isn't on PATH ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-dry-run-empty-"));
  const savedPath = process.env.PATH;
  try {
    process.env.PATH = scratchDir;

    const result = await runCodexExec({
      prompt: "test",
      schema,
      sandbox: "read-only",
      cwd: scratchDir,
      dispatchId: "smoke-dry-run-missing",
      dryRun: true
    });

    check("reports ok: false", result.ok === false, JSON.stringify(result));
    check("category is cli_unavailable", result.category === "cli_unavailable", JSON.stringify(result));
  } finally {
    restoreEnv("PATH", savedPath);
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== runCodexExec({ dryRun: true }): scratch schema dir is cleaned up, not left behind ===");
{
  const result = await runCodexExec({
    prompt: "test",
    schema,
    sandbox: "read-only",
    cwd: process.cwd(),
    dispatchId: "smoke-dry-run-cleanup",
    dryRun: true
  });
  const leftoverDirs = fs.readdirSync(os.tmpdir()).filter((name) => name.includes("codex-kit-exec-smoke-dry-run-cleanup"));
  check("dry run resolved successfully (precondition for the cleanup check below)", result.ok === true, JSON.stringify(result));
  check("no scratch directory survives a dry run", leftoverDirs.length === 0, JSON.stringify(leftoverDirs));
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
