#!/usr/bin/env node
// Smoke test: scripts/lib/fs.mjs's writeJsonFile (atomic temp-file-then-rename)
//
// Confirms the fix for a real reliability gap: state.json/broker.json/job
// files used to be written directly via fs.writeFileSync, so a process
// killed mid-write (e.g. a hook hitting its own timeout -- see
// hooks.json's SessionEnd budget) could leave truncated/partial JSON that
// a later reader's try/catch would silently treat as absent. Runs entirely
// against a scratch temp directory -- never touches real plugin state.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/fs-atomic-write.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { writeJsonFile } from "../lib/fs.mjs";

const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-kit-fs-atomic-smoke-"));

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

console.log("=== writeJsonFile: round-trip and temp-file cleanup ===");
{
  const target = path.join(scratchDir, "state.json");
  writeJsonFile(target, { version: 1, jobs: [] });
  const written = JSON.parse(fs.readFileSync(target, "utf8"));
  check("a successful write round-trips the given value", written.version === 1 && Array.isArray(written.jobs), JSON.stringify(written));

  const leftoverTempFiles = fs.readdirSync(scratchDir).filter((name) => name.includes(".tmp-"));
  check("no leftover .tmp-<pid> file survives a successful write", leftoverTempFiles.length === 0, leftoverTempFiles.join(","));

  writeJsonFile(target, { version: 2, jobs: [{ id: "job-1" }] });
  const overwritten = JSON.parse(fs.readFileSync(target, "utf8"));
  check("a second write correctly replaces the first (not appended)", overwritten.version === 2, JSON.stringify(overwritten));
}

console.log("\n=== writeJsonFile: a failed write never corrupts the existing file ===");
{
  const target = path.join(scratchDir, "protected.json");
  writeJsonFile(target, { safe: "original" });
  const before = fs.readFileSync(target, "utf8");

  const circular = {};
  circular.self = circular;
  let threw = false;
  try {
    writeJsonFile(target, circular);
  } catch {
    threw = true;
  }
  check("JSON.stringify failure on the new value throws (never silently succeeds)", threw);

  const after = fs.readFileSync(target, "utf8");
  check(
    "the original file is byte-identical after a failed write attempt -- the failure never reaches fs.renameSync",
    before === after,
    `before=${before} after=${after}`
  );

  const leftoverTempFiles = fs.readdirSync(scratchDir).filter((name) => name.includes(".tmp-") && name.includes("protected"));
  check("no orphaned temp file for the failed write either (writeFileSync itself never ran)", leftoverTempFiles.length === 0, leftoverTempFiles.join(","));
}

console.log("\n=== writeJsonFile: mode preservation (POSIX only) ===");
{
  if (process.platform === "win32") {
    console.log("SKIP  mode-bit check -- Windows does not implement POSIX file permission bits the same way; broker-lifecycle.mjs's own comment already documents this as a POSIX-only guarantee.");
  } else {
    const target = path.join(scratchDir, "broker.json");
    writeJsonFile(target, { token: "test-token" }, { mode: 0o600 });
    const actualMode = fs.statSync(target).mode & 0o777;
    check("a file written with { mode: 0o600 } has that mode on disk", actualMode === 0o600, actualMode.toString(8));
  }
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
