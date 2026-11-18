// Tests for the PreToolUse checkout guard (issue #762). Run with `node --test tests/`.
// The guard trusts only its own location, so each fixture runs a copy placed in its fake installed root.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const GUARD_NAME = "rva-guard-checkout-scripts.mjs";
const GUARD = path.join(PLUGIN, "scripts", GUARD_NAME);

const created = [];
after(() => {
  for (const dir of created) fs.rmSync(dir, { recursive: true, force: true });
});

function tempDir(prefix) {
  const dir = fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(), prefix)));
  created.push(dir);
  return dir;
}

function installAt(root) {
  fs.mkdirSync(path.join(root, "scripts"), { recursive: true });
  fs.copyFileSync(GUARD, path.join(root, "scripts", GUARD_NAME));
  for (const name of ["rva-dispatch.mjs", "rva-prepare.mjs"]) fs.writeFileSync(path.join(root, "scripts", name), "");
  return root;
}

// An installed copy outside any repository (under a directory with a space in its name), and a
// repository holding a .claude/ copy of the scripts.
function fixture() {
  const installed = installAt(path.join(tempDir("rva-installed-"), "with space"));
  const repo = tempDir("rva-repo-");
  fs.mkdirSync(path.join(repo, ".git"));
  installAt(path.join(repo, ".claude"));
  return { installed, repo };
}

function run(stdin, root, extraEnv = {}) {
  const env = { ...process.env, CLAUDE_PLUGIN_ROOT: root };
  delete env.CLAUDE_PROJECT_DIR;
  Object.assign(env, extraEnv);
  const r = spawnSync(process.execPath, [path.join(root, "scripts", GUARD_NAME)], { input: stdin, encoding: "utf8", env, timeout: 30_000 });
  assert.equal(r.status, 0, r.stderr);
  const out = r.stdout.trim();
  return out ? JSON.parse(out).hookSpecificOutput : null;
}

function bash(command, cwd, tool = "Bash") {
  return JSON.stringify({ hook_event_name: "PreToolUse", tool_name: tool, tool_input: { command }, cwd });
}

const denied = (decision) => decision?.permissionDecision === "deny";

test("a command that names none of the scripts is left alone", () => {
  const f = fixture();
  for (const cmd of ["git status && node --test tests/rva-dispatch.test.mjs", "cat foo-rva-dispatch.mjs rva-dispatch.mjs.bak"]) {
    assert.equal(run(bash(cmd, f.repo), f.installed), null, cmd);
  }
});

test("an absolute path into the installed copy is allowed, quoted or escaped, with a space in it", () => {
  const f = fixture();
  const prepare = path.join(f.installed, "scripts", "rva-prepare.mjs");
  const dispatch = path.join(f.installed, "scripts", "rva-dispatch.mjs");
  const commands = [`node "${prepare}" --cwd "$PWD" && node '${dispatch}' --dry-run`];
  // An unquoted backslash escapes the space; a Windows path's own backslashes would be eaten the same way,
  // so there an unquoted path is denied (fail closed) and only POSIX checks this form.
  if (process.platform !== "win32") commands.push(`node ${dispatch.replace(/ /g, "\\ ")} --dry-run`);
  for (const cmd of commands) {
    assert.equal(run(bash(cmd, f.repo), f.installed), null, cmd);
    assert.equal(run(bash(cmd, f.repo, "PowerShell"), f.installed), null, `PowerShell: ${cmd}`);
  }
});

test("a copy inside the repository is denied, by relative or absolute path, in any letter case", () => {
  const f = fixture();
  for (const cmd of [
    "node .claude/scripts/rva-dispatch.mjs --dry-run",
    "node .claude/scripts/RVA-Dispatch.mjs",
    `node "${path.join(f.repo, ".claude", "scripts", "rva-dispatch.mjs")}"`,
    "cd .claude/scripts && node rva-dispatch.mjs",
    `node "${path.join(f.installed, "scripts", "rva-dispatch.mjs")}"; node ./rva-dispatch.mjs`,
    `node .claude/scripts/rva-"dispatch".mjs`
  ]) {
    assert.ok(denied(run(bash(cmd, f.repo), f.installed)), cmd);
  }
});

test("the guard's own script is denied from the repository and allowed from the installed copy", () => {
  const f = fixture();
  const inRepo = `node "${path.join(f.repo, ".claude", "scripts", GUARD_NAME)}"`;
  assert.ok(denied(run(bash(inRepo, f.repo), f.installed)), inRepo);
  const installed = `node "${path.join(f.installed, "scripts", GUARD_NAME)}"`;
  assert.equal(run(bash(installed, f.repo), f.installed), null, installed);
});

test("a variable, substitution or unterminated quote around a script name is denied", () => {
  const f = fixture();
  for (const cmd of [
    'node "${CLAUDE_PLUGIN_ROOT}/scripts/rva-dispatch.mjs"',
    "node $CLAUDE_PLUGIN_ROOT/scripts/rva-dispatch.mjs",
    "node $(pwd)/rva-dispatch.mjs",
    `node "${path.join(f.installed, "scripts", "rva-dispatch.mjs")}`
  ]) {
    assert.ok(denied(run(bash(cmd, f.repo), f.installed)), cmd);
  }
});

test("a path that resolves out of the installed copy through a symbolic link is denied", { skip: process.platform === "win32" && "symlinks need extra rights on Windows" }, () => {
  const f = fixture();
  const link = path.join(f.installed, "scripts", "linked");
  fs.symlinkSync(path.join(f.repo, ".claude", "scripts"), link);
  assert.ok(denied(run(bash(`node "${path.join(link, "rva-dispatch.mjs")}"`, f.repo), f.installed)));
});

test("a missing file under the installed copy is denied", () => {
  const f = fixture();
  assert.ok(denied(run(bash(`node "${path.join(f.installed, "scripts", "rva-run.mjs")}"`, f.repo), f.installed)));
});

test("a CLAUDE_PLUGIN_ROOT that differs from the guard's own location is denied", () => {
  const f = fixture();
  const other = installAt(tempDir("rva-other-"));
  const cmd = `node "${path.join(other, "scripts", "rva-dispatch.mjs")}"`;
  const decision = run(bash(cmd, f.repo), f.installed, { CLAUDE_PLUGIN_ROOT: other });
  assert.ok(denied(decision));
  assert.match(decision.permissionDecisionReason, /does not match the guard's own location/);
});

test("a plugin root inside the open repository is denied even for its own scripts", () => {
  const f = fixture();
  const inRepo = path.join(f.repo, ".claude");
  const cmd = `node ${path.join(inRepo, "scripts", "rva-dispatch.mjs")}`;
  const decision = run(bash(cmd, f.repo), inRepo);
  assert.ok(denied(decision));
  assert.match(decision.permissionDecisionReason, /inside the repository this session has open/);
  // The same through CLAUDE_PROJECT_DIR, when the hook's cwd lies elsewhere.
  const elsewhere = tempDir("rva-elsewhere-");
  assert.ok(denied(run(bash(cmd, elsewhere), inRepo, { CLAUDE_PROJECT_DIR: f.repo })));
});

test("unparseable input is denied only when it names a script", () => {
  const f = fixture();
  assert.ok(denied(run("{not json rva-dispatch.mjs", f.installed)));
  assert.equal(run("{not json", f.installed), null);
});
