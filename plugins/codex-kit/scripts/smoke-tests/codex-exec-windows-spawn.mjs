#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's Windows npm-shim spawning fix
//
// `spawn("codex", args, { shell: false })` fails ENOENT on win32 (Node's
// CreateProcess-based lookup doesn't try PATHEXT extensions for a bare
// command name). Spawning the resolved `.cmd` path directly, still with
// `shell: false`, instead throws a *synchronous* EINVAL (Node refuses to
// launch a `.bat`/`.cmd` file without a shell -- CVE-2024-27980 hardening).
// `shell: true` on its own is not safe either: confirmed live (2026-08-17)
// that Node does not escape array arguments against cmd.exe metacharacters
// under `shell: true` -- an embedded `&` in an argument was interpreted as
// a command separator and actually executed a second command.
//
// The fix ports `cross-spawn`'s algorithm (escape.js + parse.js's
// `parseNonShell`, fetched from github.com/moxystudio/node-cross-spawn and
// verified against the real npm package's own behavior on the same
// adversarial input, 2026-08-17 -- not reimplemented from memory). This
// test exercises the ported functions directly: PATHEXT-based resolution,
// the escaping algorithm's injection-resistance, and the platform-gated
// invocation builder (using the injectable `platform` param so this runs
// identically on any CI runner, not just a real Windows machine).
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-windows-spawn.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { buildSpawnInvocation, escapeWindowsArgument, escapeWindowsCommand, resolveWindowsExecutable } from "../lib/codex-exec.mjs";

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

console.log("=== resolveWindowsExecutable: PATHEXT-based resolution ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-windows-spawn-"));
  const savedPath = process.env.PATH;
  const savedPathExt = process.env.PATHEXT;
  try {
    fs.writeFileSync(path.join(scratchDir, "mytool.cmd"), "@echo off\n");
    process.env.PATH = scratchDir + path.delimiter + (savedPath || "");
    process.env.PATHEXT = ".COM;.EXE;.BAT;.CMD";

    const resolved = resolveWindowsExecutable("mytool");
    check("finds a .cmd shim on PATH", resolved === path.join(scratchDir, "mytool.cmd"), resolved);
    check("returns null for a command that doesn't exist anywhere on PATH", resolveWindowsExecutable("this-tool-does-not-exist-anywhere") === null);
  } finally {
    process.env.PATH = savedPath;
    process.env.PATHEXT = savedPathExt;
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== escapeWindowsArgument: no bare shell metacharacter survives ===");
{
  const META_CHARS = ["(", ")", "%", "!", "^", '"', "<", ">", "&", "|", ";", ",", " ", "*", "?"];
  const evil = "foo & echo INJECTED > injected.txt & echo bar";
  const escaped = escapeWindowsArgument(evil);
  // Walk the string treating `^X` as one consumed, already-escaped pair (the
  // caret itself is the escape marker, not something requiring its own
  // escape) -- any metacharacter reached *outside* such a pair is bare and
  // would let cmd.exe interpret it as a real command separator/operator.
  let allEscaped = true;
  let i = 0;
  while (i < escaped.length) {
    if (escaped[i] === "^") {
      i += 2;
      continue;
    }
    if (META_CHARS.includes(escaped[i])) {
      allEscaped = false;
      break;
    }
    i += 1;
  }
  check("every metacharacter in the escaped output is caret-prefixed", allEscaped, escaped);
  check("the escaped output still contains the literal payload text (not stripped, just neutralized)", escaped.includes("INJECTED"), escaped);
}

console.log("\n=== escapeWindowsArgument: embedded double quote ===");
{
  const escaped = escapeWindowsArgument('a"b');
  // Per the ported algorithm: the embedded quote gets backslash-escaped
  // first (quote-with-preceding-backslashes rule), then the whole thing is
  // wrapped in quotes, then meta-chars (including both the wrapping quotes
  // and the escaped inner quote) get caret-prefixed.
  check("matches the ported cross-spawn algorithm's known output shape", escaped === '^"a\\^"b^"', escaped);
}

console.log("\n=== escapeWindowsArgument: plain argument round-trips predictably ===");
{
  const escaped = escapeWindowsArgument("--sandbox");
  check("a metachar-free argument is just quote-wrapped and caret-escaped", escaped === '^"--sandbox^"', escaped);
}

console.log("\n=== escapeWindowsCommand: meta-char escaping only, no quoting ===");
{
  const escaped = escapeWindowsCommand("C:\\tools\\my app\\codex.cmd");
  check("a space in the resolved path is caret-escaped", escaped.includes("my^ app"), escaped);
  check("path separators are left untouched", escaped.includes("C:\\tools\\"), escaped);
}

console.log("\n=== buildSpawnInvocation: non-Windows platform passes through unchanged ===");
{
  const inv = buildSpawnInvocation("codex", ["exec", "--sandbox", "read-only"], { cwd: "/tmp" }, "linux");
  check("resolved is true", inv.resolved === true);
  check("command is unchanged", inv.command === "codex", inv.command);
  check("args are unchanged", JSON.stringify(inv.args) === JSON.stringify(["exec", "--sandbox", "read-only"]), JSON.stringify(inv.args));
  check("options are passed through without shell/windowsVerbatimArguments added", !("shell" in inv.options) && !("windowsVerbatimArguments" in inv.options), JSON.stringify(inv.options));
}

console.log("\n=== buildSpawnInvocation: Windows, directly-executable target (.exe) ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-windows-spawn-"));
  const savedPath = process.env.PATH;
  const savedPathExt = process.env.PATHEXT;
  try {
    fs.writeFileSync(path.join(scratchDir, "mytool.exe"), "");
    process.env.PATH = scratchDir + path.delimiter + (savedPath || "");
    process.env.PATHEXT = ".COM;.EXE;.BAT;.CMD";

    const inv = buildSpawnInvocation("mytool", ["--flag"], {}, "win32");
    check("resolved is true", inv.resolved === true);
    check("spawns the .exe directly, not through cmd.exe", inv.command === path.join(scratchDir, "mytool.exe"), inv.command);
    check("args are passed through unescaped (a real .exe gets Node's own normal argv quoting)", JSON.stringify(inv.args) === JSON.stringify(["--flag"]), JSON.stringify(inv.args));
    check("shell is explicitly false", inv.options.shell === false);
  } finally {
    process.env.PATH = savedPath;
    process.env.PATHEXT = savedPathExt;
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== buildSpawnInvocation: Windows, .cmd shim target ===");
{
  const scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-exec-windows-spawn-"));
  const savedPath = process.env.PATH;
  const savedPathExt = process.env.PATHEXT;
  try {
    fs.writeFileSync(path.join(scratchDir, "mytool.cmd"), "@echo off\n");
    process.env.PATH = scratchDir + path.delimiter + (savedPath || "");
    process.env.PATHEXT = ".COM;.EXE;.BAT;.CMD";

    const inv = buildSpawnInvocation("mytool", ["exec", "foo & bar"], {}, "win32");
    check("resolved is true", inv.resolved === true);
    check("routes through cmd.exe, not the .cmd file directly (avoids the synchronous EINVAL)", /cmd\.exe$/i.test(inv.command), inv.command);
    check("windowsVerbatimArguments is set (tells Node not to re-quote our already-escaped command line)", inv.options.windowsVerbatimArguments === true);
    check("shell is explicitly false (we build the command line ourselves, not via shell: true)", inv.options.shell === false);
    check("the dangerous argument's & is caret-escaped inside the built command line, not bare", inv.args[3].includes("^&") && !/[^^]&/.test(inv.args[3]), inv.args[3]);
  } finally {
    process.env.PATH = savedPath;
    process.env.PATHEXT = savedPathExt;
    fs.rmSync(scratchDir, { recursive: true, force: true });
  }
}

console.log("\n=== buildSpawnInvocation: Windows, command not found anywhere on PATH ===");
{
  const inv = buildSpawnInvocation("this-tool-does-not-exist-anywhere", ["--version"], {}, "win32");
  check("resolved is false", inv.resolved === false);
  check("no command/args leak through on a failed resolution", inv.command === undefined && inv.args === undefined);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
