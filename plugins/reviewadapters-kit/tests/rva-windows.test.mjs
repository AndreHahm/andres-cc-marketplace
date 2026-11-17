// Windows support (issue #770): the DACL decision rule on synthetic ACLs (every platform), and on Windows
// live checks against real ACLs, the process-tree kill, the .exe-only binary lookup and a prepare, dry-run
// dispatch and cleanup round trip. Live fixtures sit in a directory under the user profile made private
// with icacls, since a default %TEMP% may grant other accounts access (see the README).
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const PLUGIN = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CODEX_KIT = path.resolve(PLUGIN, "..", "codex-kit");
const acl = await import(pathToFileURL(path.join(PLUGIN, "scripts", "rva-winacl.mjs")).href);
const WINDOWS_ONLY = process.platform !== "win32" && "Windows only";

const ME = "S-1-5-21-1-2-3-1001";
const OTHER = "S-1-5-21-1-2-3-1004";
const rule = (sid, rights, extra = {}) => ({ allow: true, sid, rights, inheritOnly: false, inherits: false, ...extra });

test("the DACL rule: owner, trusted principals, rights and inheritance", () => {
  const own = (rules, owner = ME) => ({ owner, rules });
  assert.equal(acl.aclProblem(own([rule(ME, 0x1f01ff), rule("S-1-5-18", 0x1f01ff), rule("S-1-5-32-544", 0x1f01ff)]), ME), null);
  assert.match(acl.aclProblem(own([], "S-1-5-32-544"), ME), /not owned by the current user/);
  assert.equal(acl.aclProblem(own([], "S-1-5-32-544"), ME, { owner: "trusted" }), null);
  assert.match(acl.aclProblem(own([], OTHER), ME, { owner: "trusted" }), /owned by another user/);
  // Read and execute for others is fine; modify, delete alone, or WRITE_DAC is not.
  assert.equal(acl.aclProblem(own([rule(OTHER, 0x1200a9)]), ME), null);
  for (const rights of [0x1301bf, 0x10000, 0x40000, 0x80000, 0x10000000]) {
    assert.match(acl.aclProblem(own([rule(OTHER, rights)]), ME), /another account/, `rights ${rights.toString(16)}`);
  }
  // AppContainer capability SIDs count as other accounts.
  assert.match(acl.aclProblem(own([rule("S-1-15-3-1-2-3", 0x1f01ff)]), ME), /another account/);
  // A deny rule does not cancel an allow rule (fail closed), and a deny rule alone is no problem.
  assert.match(acl.aclProblem(own([rule(OTHER, 0x2), { ...rule(OTHER, 0x2), allow: false }]), ME), /another account/);
  // An inherit-only rule counts only where entries will be created (inheritable).
  const io = own([rule(OTHER, 0x1301bf, { inheritOnly: true, inherits: true })]);
  assert.equal(acl.aclProblem(io, ME), null);
  assert.match(acl.aclProblem(io, ME, { inheritable: true }), /another account/);
  // Above the temp directory, adding entries is allowed, deleting or replacing one is not.
  assert.equal(acl.aclProblem(own([rule("S-1-5-11", 0x4)], "S-1-5-18"), ME, { owner: "trusted", rights: acl.REPLACE_RIGHTS }), null);
  assert.match(acl.aclProblem(own([rule("S-1-5-11", 0x40)], "S-1-5-18"), ME, { owner: "trusted", rights: acl.REPLACE_RIGHTS }), /another account/);
  // An unreadable ACL fails closed.
  assert.match(acl.aclProblem({ error: true }, ME), /could not be read/);
});

test("the ACL output parser fails closed on anything but plain allow and deny entries", () => {
  const ok = acl.parseAclOutput(`ME ${ME}\nITEM ${ME} 0\nACE 0 0 ${OTHER} 1179817 3\nACE 1 0 ${OTHER} 2 0\n`);
  assert.equal(ok.me, ME);
  assert.deepEqual(ok.items[0].rules.map((r) => [r.allow, r.inherits, r.inheritOnly]), [[true, true, false], [false, false, false]]);
  // A negative mask (a high bit set) is read as unsigned.
  assert.equal(acl.parseAclOutput(`ME ${ME}\nITEM ${ME} 0\nACE 0 0 ${OTHER} -536805376 8\n`).items[0].rules[0].rights, 0xe0010000 >>> 0);
  // No DACL, a callback entry, another entry type, a bad SID or mask: that item fails closed.
  for (const body of [`ITEM ${ME} 1`, `ITEM ${ME} 0\nACE 0 1 ${OTHER} 2 0`, `ITEM ${ME} 0\nACE OTHER`, `ITEM ${ME} 0\nACE 0 0 Everyone 2 0`, `ITEM ${ME} 0\nACE 0 0 ${OTHER} two 0`, "ITEM ERROR"]) {
    assert.equal(acl.parseAclOutput(`ME ${ME}\n${body}\n`).items[0].error, true, body);
  }
  // Output that is not the expected shape at all throws.
  for (const text of ["", "garbage", `ME ${ME}\nACE 0 0 ${OTHER} 2 0`, `ME ${ME}\nITEM what`]) {
    assert.throws(() => acl.parseAclOutput(text), /unexpected output/, text);
  }
});

// ---- Live checks (Windows only) ----

const created = [];
after(() => {
  for (const dir of created) fs.rmSync(dir, { recursive: true, force: true });
});

function icacls(...args) {
  execFileSync(path.join(process.env.SystemRoot, "System32", "icacls.exe"), args, { stdio: "ignore" });
}

// A directory under the profile with a protected DACL: the current user, SYSTEM and Administrators only.
function privateDir(prefix) {
  const dir = fs.realpathSync.native(fs.mkdtempSync(path.join(os.homedir(), prefix)));
  created.push(dir);
  const me = acl.currentUserSid();
  icacls(dir, "/inheritance:r", "/grant:r", `*${me}:(OI)(CI)F`, "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F");
  return dir;
}

function fresh() {
  // Each test reads ACLs it just changed: run the check in a child process so no cached result is reused.
  return (code) => {
    const r = spawnSync(process.execPath, ["--input-type=module", "-e", code], { encoding: "utf8" });
    assert.equal(r.status, 0, r.stderr);
    return JSON.parse(r.stdout.trim());
  };
}

test("a private temp directory passes; one another account can modify does not", { skip: WINDOWS_ONLY }, () => {
  const tmp = privateDir(".rva-test-tmp-");
  const check = fresh();
  const url = JSON.stringify(new URL("../scripts/rva-codex-kit.mjs", import.meta.url).href);
  const probe = `const m = await import(${url}); console.log(JSON.stringify(m.unsafeTempDir(${JSON.stringify(tmp)})));`;
  assert.equal(check(probe), false);
  icacls(tmp, "/grant", "*S-1-1-0:(OI)(CI)M");
  assert.equal(check(probe), true);
});

test("ownedAndPrivate reads the file's DACL and refuses a grant to Authenticated Users", { skip: WINDOWS_ONLY }, () => {
  const dir = privateDir(".rva-test-file-");
  const file = path.join(dir, "local.json");
  fs.writeFileSync(file, "{}");
  const check = fresh();
  const url = JSON.stringify(new URL("../scripts/rva-codex-kit.mjs", import.meta.url).href);
  const probe = `import fs from "node:fs"; const m = await import(${url}); const f = ${JSON.stringify(file)}; console.log(JSON.stringify(m.ownedAndPrivate(fs.statSync(f), f)));`;
  assert.equal(check(probe), true);
  icacls(file, "/grant", "*S-1-5-11:(M)");
  assert.equal(check(probe), false);
});

test("a private file under a directory another account may delete entries in is refused (path swap)", { skip: WINDOWS_ONLY }, () => {
  const dir = privateDir(".rva-test-anc-");
  const sub = path.join(dir, "sub");
  fs.mkdirSync(sub);
  const file = path.join(sub, "local.json");
  fs.writeFileSync(file, "{}");
  // The file itself stays private: the grant is on the directory above it only, not inherited.
  icacls(sub, "/inheritance:r", "/grant:r", `*${acl.currentUserSid()}:(OI)(CI)F`, "*S-1-5-18:(OI)(CI)F");
  const check = fresh();
  const url = JSON.stringify(new URL("../scripts/rva-codex-kit.mjs", import.meta.url).href);
  const probe = `import fs from "node:fs"; const m = await import(${url}); const f = ${JSON.stringify(file)}; console.log(JSON.stringify(m.ownedAndPrivate(fs.statSync(f), f)));`;
  assert.equal(check(probe), true);
  icacls(dir, "/grant", "*S-1-1-0:(DC)");
  assert.equal(check(probe), false);
});

test("makePrivateDir leaves only the user, SYSTEM and Administrators on a directory under a shared one", { skip: WINDOWS_ONLY }, () => {
  const shared = privateDir(".rva-test-mpd-");
  icacls(shared, "/grant", "*S-1-5-32-545:(OI)(CI)RX");
  const dir = path.join(shared, "run");
  fs.mkdirSync(dir);
  const check = fresh();
  const url = JSON.stringify(new URL("../scripts/rva-winacl.mjs", import.meta.url).href);
  const sids = check(`const m = await import(${url}); const d = ${JSON.stringify(dir)}; m.makePrivateDir(d); const [i] = m.readAcls([d]); console.log(JSON.stringify(i.rules.map((r) => r.sid)));`);
  assert.ok(sids.length > 0);
  assert.deepEqual(sids.filter((sid) => !["S-1-5-18", "S-1-5-32-544", acl.currentUserSid()].includes(sid)), [], "another account can still read the run directory");
});

test("findBinary takes only an .exe or .com and names a .cmd shim", { skip: WINDOWS_ONLY }, async () => {
  const { findBinary, onlyShimFound } = await import(pathToFileURL(path.join(PLUGIN, "scripts", "rva-config.mjs")).href);
  const bin = privateDir(".rva-test-bin-");
  const untrusted = privateDir(".rva-test-repo-");
  fs.writeFileSync(path.join(bin, "rvafake.cmd"), "@echo off\r\n");
  const saved = process.env.PATH;
  process.env.PATH = `${bin}${path.delimiter}${saved}`;
  try {
    assert.equal(findBinary("rvafake", untrusted), null);
    assert.equal(onlyShimFound("rvafake", untrusted), true);
    fs.copyFileSync(path.join(bin, "rvafake.cmd"), path.join(bin, "rvafake.exe"));
    assert.equal(findBinary("rvafake", untrusted), path.join(bin, "rvafake.exe"));
  } finally {
    process.env.PATH = saved;
  }
});

function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function waitFor(file) {
  for (let i = 0; i < 100 && !fs.existsSync(file); i += 1) await new Promise((resolve) => setTimeout(resolve, 100));
  return Number(fs.readFileSync(file, "utf8"));
}

test("the timeout kills the vendor's whole process tree, and a normal exit ends a helper it left", { skip: WINDOWS_ONLY }, async () => {
  const { runVendor } = await import(pathToFileURL(path.join(PLUGIN, "scripts", "rva-run.mjs")).href);
  const dir = privateDir(".rva-test-run-");
  // A vendor stand-in that starts a helper living far longer than any timeout here, writes the helper's
  // pid, then hangs as long or exits at once. Only a kill can end either within the time checked below.
  const helper = `const { spawn } = require("node:child_process"); const fs = require("node:fs");
    const c = spawn(process.execPath, ["-e", "setTimeout(() => {}, 600000)"], { stdio: "ignore" });
    fs.writeFileSync(process.argv[1], String(c.pid));
    if (process.argv[2] === "hang") setTimeout(() => {}, 600000); else process.exit(0);`;
  const env = { SystemRoot: process.env.SystemRoot, PATH: process.env.PATH };
  const hangPid = path.join(dir, "hang.pid");
  let started = Date.now();
  const hung = await runVendor({ command: process.execPath, args: ["-e", helper, hangPid, "hang"], cwd: dir, env, timeoutMs: 3000 });
  assert.equal(hung.timedOut, true);
  assert.ok(Date.now() - started < 30_000, "the timed-out vendor was not killed");
  const hungHelper = await waitFor(hangPid);
  leftovers.push(hungHelper);
  assert.equal(alive(hungHelper), false, "the helper of a timed-out vendor is still running");

  const exitPid = path.join(dir, "exit.pid");
  started = Date.now();
  const done = await runVendor({ command: process.execPath, args: ["-e", helper, exitPid, "exit"], cwd: dir, env, timeoutMs: 120_000 });
  assert.equal(done.timedOut, false);
  assert.ok(Date.now() - started < 60_000, "the finished vendor's run did not end");
  const leftHelper = await waitFor(exitPid);
  leftovers.push(leftHelper);
  assert.equal(alive(leftHelper), false, "a helper left by a finished vendor is still running");
});

// A helper a failing run left behind is ended here, not left running for ten minutes.
const leftovers = [];
after(() => {
  for (const pid of leftovers) {
    if (alive(pid)) process.kill(pid);
  }
});

test("prepare, a dry-run dispatch and cleanup run end to end on Windows", { skip: WINDOWS_ONLY }, () => {
  const base = privateDir(".rva-test-e2e-");
  // Installed copies of both plugins, outside any repository, recorded in a profile's plugin registry.
  const installed = path.join(base, "cache", "reviewadapters-kit");
  const codexKit = path.join(base, "cache", "codex-kit");
  fs.cpSync(PLUGIN, installed, { recursive: true });
  fs.cpSync(CODEX_KIT, codexKit, { recursive: true });
  const home = path.join(base, "home");
  fs.mkdirSync(path.join(home, ".claude", "plugins"), { recursive: true });
  fs.writeFileSync(path.join(home, ".claude", "plugins", "installed_plugins.json"),
    JSON.stringify({ version: 2, plugins: { "codex-kit@andres-cc-marketplace": [{ scope: "user", installPath: codexKit }] } }));
  const tmp = path.join(base, "tmp");
  fs.mkdirSync(tmp);
  const repo = path.join(base, "repo");
  fs.mkdirSync(repo);
  const git = (...args) => execFileSync("git", ["-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", ...args], { encoding: "utf8" });
  git("init", "-q");
  fs.writeFileSync(path.join(repo, "calc.py"), "def add(a, b):\n    return a + b\n");
  git("add", "calc.py");
  git("commit", "-q", "-m", "init");
  fs.writeFileSync(path.join(repo, "calc.py"), "def add(a, b):\n    return a - b\n");
  fs.mkdirSync(path.join(repo, ".claude"));
  fs.writeFileSync(path.join(repo, ".claude", "reviewadapters-kit.local.json"), JSON.stringify({ vendors: { pi: { enabled: true } } }));
  // An empty pi.exe: the dry run only looks it up and never starts it.
  const bin = path.join(base, "bin");
  fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, "pi.exe"), "");
  const env = { ...process.env, USERPROFILE: home, HOME: home, TMP: tmp, TEMP: tmp, PATH: `${bin}${path.delimiter}${process.env.PATH}` };
  const node = (script, args) => {
    const r = spawnSync(process.execPath, [path.join(installed, "scripts", script), ...args], { encoding: "utf8", env });
    return JSON.parse(r.stdout.trim().split("\n").pop());
  };

  const prepared = node("rva-prepare.mjs", ["--cwd", repo]);
  assert.equal(prepared.ok, true, JSON.stringify(prepared));
  for (const key of ["dir", "diff_file", "instruction_file", "target_paths_file"]) assert.doesNotMatch(prepared[key], /\\/, `${key} keeps a backslash`);
  const dry = node("rva-dispatch.mjs", ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", prepared.dispatch_id,
    "--instruction-file", prepared.instruction_file, "--diff-file", prepared.diff_file, "--target-paths-file", prepared.target_paths_file,
    "--cwd", repo, "--dry-run"]);
  assert.equal(dry.ok, true, JSON.stringify(dry));
  assert.equal(dry.dryRun, true);
  const cleaned = node("rva-prepare.mjs", ["--cleanup", prepared.dir, prepared.token]);
  assert.equal(cleaned.ok, true, JSON.stringify(cleaned));
  assert.equal(fs.existsSync(prepared.dir), false);

  // The same dry run with a temp directory Everyone can modify is refused before anything is written.
  icacls(tmp, "/grant", "*S-1-1-0:(OI)(CI)M");
  const refused = node("rva-prepare.mjs", ["--cwd", repo]);
  assert.equal(refused.ok, false);
  assert.match(refused.detail, /temp directory/);
  // And a local file Authenticated Users can modify enables nothing.
  icacls(tmp, "/remove", "*S-1-1-0");
  icacls(path.join(repo, ".claude", "reviewadapters-kit.local.json"), "/grant", "*S-1-5-11:(M)");
  const again = node("rva-prepare.mjs", ["--cwd", repo]);
  assert.equal(again.ok, true, JSON.stringify(again));
  const blocked = node("rva-dispatch.mjs", ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", again.dispatch_id,
    "--instruction-file", again.instruction_file, "--diff-file", again.diff_file, "--target-paths-file", again.target_paths_file,
    "--cwd", repo, "--dry-run"]);
  assert.equal(blocked.category, "vendor_not_allowed", JSON.stringify(blocked));
  node("rva-prepare.mjs", ["--cleanup", again.dir, again.token]);
});
