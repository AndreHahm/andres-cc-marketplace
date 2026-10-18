#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs --target-paths-file (issue #611)
//
// A reviewer's --target-paths is one comma-joined argument, and one over the operating system's
// limit cannot be started (a 4,500-path diff failed every reviewer with "Argument list too long").
// --target-paths-file reads the same entries from a file instead, one per line, so the list has no
// argument limit and every call keeps its full scope. Confirms: the file's entries get exactly the
// same validation as --target-paths entries; exactly one of the two flags is required; the file
// must be a readable regular file under a size cap; and a list far over the argument limit is
// accepted and reaches the prompt whole.
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-target-paths-file.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE_INVOKE = path.join(SCRIPT_DIR, "..", "..", "skills", "codex-review-bridge", "scripts", "bridge-invoke.mjs");
const ENTRY_ERROR = "target-paths entry is invalid";

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

function runBridge(tmpDir, instructionFile, pathArgs) {
  try {
    const stdout = execFileSync(
      "node",
      [
        BRIDGE_INVOKE,
        "--reviewer-type", "test-reviewer",
        "--instruction-file", instructionFile,
        ...pathArgs,
        "--execution-profile", "read-only",
        "--dispatch-id", "smoke-test",
        "--cwd", tmpDir,
        "--dry-run", "true"
      ],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 256 * 1024 * 1024 }
    );
    return { ok: true, stdout, stderr: "" };
  } catch (e) {
    return { ok: false, stdout: e.stdout?.toString() ?? "", stderr: e.stderr?.toString() ?? "" };
  }
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-paths-file-smoke-"));
const instructionFile = path.join(tmpDir, "reviewer.md");
fs.writeFileSync(instructionFile, "trusted instructions, outside the reviewed scope");

function pathsFile(name, content) {
  const file = path.join(tmpDir, name);
  fs.writeFileSync(file, content);
  return file;
}

try {
  console.log("\n=== Accepted ===");
  let result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("two.txt", "alpha/one.py\nbeta/two.py\n")]);
  check("two entries with a trailing newline are accepted", result.ok, result.stderr);
  check("the prompt names both entries", result.stdout.includes("alpha/one.py, beta/two.py"), result.stdout.slice(0, 300));

  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("nonl.txt", "alpha/one.py\nbeta/two.py")]);
  check("a file without a trailing newline is accepted", result.ok, result.stderr);

  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("one.txt", "alpha/one.py\n")]);
  check("a single entry is accepted", result.ok, result.stderr);

  // About 12 MiB would be silly; 5,000 entries of ~60 characters is ~300 KB, well over the
  // ~128 KiB a single argument may carry on Linux, so this fails on the argument path.
  const many = Array.from({ length: 5000 }, (_, i) => `pkg${i % 7}/module${Math.floor(i / 7)}/some_long_file_name_${i}.py`);
  const joinedLength = many.join(",").length;
  check("the fixture really exceeds the single-argument limit", joinedLength > 200000, String(joinedLength));
  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("many.txt", many.join("\n") + "\n")]);
  check("a list over the argument limit is accepted", result.ok, result.stderr.slice(0, 300));
  check("every entry reaches the prompt", result.stdout.includes(many[0]) && result.stdout.includes(many[many.length - 1]), "");

  console.log("\n=== Rejected: same entry check as --target-paths ===");
  const badEntries = [
    ["a padded entry", "alpha/one.py\n beta/two.py\n"],
    ["a trailing-space entry", "alpha/one.py \n"],
    ["an empty line in the middle", "alpha/one.py\n\nbeta/two.py\n"],
    ["two trailing newlines (an empty last entry)", "alpha/one.py\n\n"],
    ["a CRLF line ending", "alpha/one.py\r\nbeta/two.py\r\n"],
    ["an empty file", ""],
    ["a lone newline", "\n"],
    ["a comma inside an entry", "alpha/one.py,beta/two.py\n"],
    ["a character outside the path charset", "alpha/o ne.py\n"]
  ];
  for (const [label, content] of badEntries) {
    result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("bad.txt", content)]);
    check(`${label}: rejected by the entry check`, !result.ok && result.stderr.includes(ENTRY_ERROR), result.stderr.slice(0, 300));
  }

  console.log("\n=== Rejected: bytes that must never be normalized ===");
  const rawBytes = [
    ["a NUL byte", Buffer.from("alpha/one.py\0\n")],
    ["a UTF-8 byte order mark", Buffer.from("﻿alpha/one.py\n", "utf8")],
    ["invalid UTF-8 (an overlong encoding of a slash)", Buffer.from([0x61, 0xc0, 0xaf, 0x62, 0x0a])]
  ];
  for (const [label, bytes] of rawBytes) {
    result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("raw.txt", bytes)]);
    check(`${label}: rejected by the entry check`, !result.ok && result.stderr.includes(ENTRY_ERROR), result.stderr.slice(0, 300));
  }

  console.log("\n=== A rejected entry is echoed capped ===");
  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("long.txt", "a".repeat(6000) + " b\n")]);
  check("a 6,000-character invalid entry is rejected", !result.ok && result.stderr.includes(ENTRY_ERROR), result.stderr.slice(0, 200));
  check("the error does not echo the whole entry", result.stderr.length < 1000, String(result.stderr.length));

  console.log("\n=== Rejected: not a regular file ===");
  if (process.platform !== "win32") {
    const fifo = path.join(tmpDir, "paths.fifo");
    execFileSync("mkfifo", [fifo]);
    result = runBridge(tmpDir, instructionFile, ["--target-paths-file", fifo]);
    check("a FIFO is rejected without blocking", !result.ok && result.stderr.includes("target-paths-file is not a readable regular file"), result.stderr.slice(0, 300));

    const deviceLink = path.join(tmpDir, "paths.link");
    fs.symlinkSync("/dev/null", deviceLink);
    result = runBridge(tmpDir, instructionFile, ["--target-paths-file", deviceLink]);
    check("a symlink to a device is rejected", !result.ok && result.stderr.includes("target-paths-file is not a readable regular file"), result.stderr.slice(0, 300));
  }

  console.log("\n=== Rejected: flag and file handling ===");
  result = runBridge(tmpDir, instructionFile, ["--target-paths", "alpha", "--target-paths-file", pathsFile("both.txt", "alpha/one.py\n")]);
  check("both flags together are rejected", !result.ok && result.stderr.includes("mutually exclusive"), result.stderr.slice(0, 300));

  result = runBridge(tmpDir, instructionFile, []);
  check("neither flag is rejected, naming both", !result.ok && result.stderr.includes("--target-paths-file"), result.stderr.slice(0, 300));

  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", path.join(tmpDir, "does-not-exist.txt")]);
  check("a missing file is rejected", !result.ok && result.stderr.includes("target-paths-file is not a readable regular file"), result.stderr.slice(0, 300));

  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", tmpDir]);
  check("a directory is rejected", !result.ok && result.stderr.includes("target-paths-file is not a readable regular file"), result.stderr.slice(0, 300));

  const big = pathsFile("big.txt", "");
  fs.truncateSync(big, 9 * 1024 * 1024);
  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", big]);
  check("a file over the size cap is rejected before it is read", !result.ok && result.stderr.includes("target-paths-file is larger than"), result.stderr.slice(0, 300));

  console.log("\n=== Containment still applies to file entries ===");
  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("escape.txt", "../../etc/passwd\n")]);
  check("an entry resolving outside the repository root is rejected", !result.ok && result.stderr.includes("resolves outside the repository root"), result.stderr.slice(0, 300));

  result = runBridge(tmpDir, instructionFile, ["--target-paths-file", pathsFile("self.txt", "reviewer.md\n")]);
  check("the instruction file listed as a target is rejected", !result.ok && result.stderr.includes("instruction-file resolves inside one of target-paths"), result.stderr.slice(0, 300));
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
