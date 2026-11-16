// Behaviour tests for rva-dispatch.mjs and rva-prepare.mjs against fake vendor binaries. No real vendor
// is called. Every run gets a temporary HOME whose installed_plugins.json points at this checkout's
// codex-kit, so the tests never import a codex-kit installed on the machine.
// Run: node --test plugins/reviewadapters-kit/tests/
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CODEX_KIT = fs.realpathSync(path.resolve(PLUGIN, "..", "codex-kit"));
const DISPATCH = path.join(PLUGIN, "scripts", "rva-dispatch.mjs");
const { diffHeaderPaths } = await import(DISPATCH);
const SHIPPED_TIMEOUT = JSON.parse(fs.readFileSync(path.join(PLUGIN, "reviewadapters-kit.settings.json"), "utf8")).timeout_ms;
const PREPARE = path.join(PLUGIN, "scripts", "rva-prepare.mjs");
const GOOD = JSON.stringify({
  findings: [{ id: "F1", severity: "major", axis: "correctness", location: "calc.py:2", evidence: "e", finding: "f", fix: "x", confidence: "high" }],
  verdict: "fail",
  inspection_limits: []
});
const DIFF = "diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a + b\n+    return a - b\n";

const created = [];
after(() => {
  for (const dir of created) fs.rmSync(dir, { recursive: true, force: true });
});

function tempDir(prefix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  created.push(dir);
  return dir;
}

// A HOME whose plugin registry records this checkout's codex-kit as installed from the marketplace.
function homeWithCodexKit(installPath = CODEX_KIT) {
  const home = tempDir("rva-test-home-");
  fs.mkdirSync(path.join(home, ".claude", "plugins"), { recursive: true });
  const plugins = installPath ? { "codex-kit@andres-cc-marketplace": [{ scope: "user", installPath }] } : {};
  fs.writeFileSync(path.join(home, ".claude", "plugins", "installed_plugins.json"), JSON.stringify({ version: 2, plugins }));
  return home;
}

function git(repo, ...args) {
  return execFileSync("git", ["-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", ...args], { encoding: "utf8" });
}

// A fixture repository (git init, nothing committed) with one changed file and the dispatch inputs.
function fixture({ enable = ["pi", "devin", "agy"], changed = "calc.py", local = {} } = {}) {
  const repo = tempDir("rva-test-repo-");
  execFileSync("git", ["init", "-q", repo]);
  fs.writeFileSync(path.join(repo, "calc.py"), "def add(a, b):\n    return a - b\n");
  fs.mkdirSync(path.join(repo, ".claude"));
  const vendors = Object.fromEntries(enable.map((v) => [v, { enabled: true }]));
  fs.writeFileSync(path.join(repo, ".claude", "reviewadapters-kit.local.json"), JSON.stringify({ vendors, ...local }));
  const inputs = tempDir("rva-test-in-");
  fs.writeFileSync(path.join(inputs, "instr.md"), "Review it.\n");
  fs.writeFileSync(path.join(inputs, "diff.patch"), changed === "calc.py" ? DIFF : `diff --git a/${changed} b/${changed}\n`);
  fs.writeFileSync(path.join(inputs, "changed.txt"), `${changed}\n`);
  // Private like a real caller's files, whatever the umask and primary group of the test machine.
  for (const name of ["instr.md", "diff.patch", "changed.txt"]) fs.chmodSync(path.join(inputs, name), 0o600);
  return { repo, inputs };
}

// Fake vendor binaries: each records its arguments and environment, then prints FAKE_OUT, sleeps, or
// exits non-zero, per FAKE_MODE.
function fakeBin() {
  const dir = tempDir("rva-test-bin-");
  const script = `#!/bin/sh
if [ "$1" = "--version" ]; then echo "fake 1.0"; exit 0; fi
if [ -n "$FAKE_ARGS" ]; then printf '%s\\n' "$@" > "$FAKE_ARGS"; env > "$FAKE_ARGS.env"; fi
case "$FAKE_MODE" in
  sleep) sh -c 'echo $$ > "$FAKE_PIDFILE"; sleep 60' & sleep 60 ;;
  fail) echo "boom" >&2; exit 3 ;;
  helper) sleep 60 & printf '%s\\n' "$FAKE_OUT"; exit 0 ;;
  *) printf '%s\\n' "$FAKE_OUT" ;;
esac
`;
  for (const name of ["pi", "devin", "agy"]) {
    fs.writeFileSync(path.join(dir, name), script, { mode: 0o755 });
  }
  return dir;
}

function runNode(script, args, { env = {}, home = homeWithCodexKit(), bin = fakeBin() } = {}) {
  const run = spawnSync(process.execPath, [script, ...args], { encoding: "utf8", env: { ...process.env, HOME: home, PATH: `${bin}${path.delimiter}${process.env.PATH}`, ...env }, timeout: 60_000 });
  const last = run.stdout.trim().split("\n").pop();
  return { code: run.status, out: last ? JSON.parse(last) : null, raw: run };
}

function dispatch({ repo, inputs }, vendor, extra = [], fake = {}, options = {}) {
  const bin = fakeBin();
  // The dispatcher passes the vendor a minimal environment, so the fake's controls are baked into a
  // wrapper rather than passed as environment variables.
  for (const name of ["pi", "devin", "agy"]) {
    const exports = Object.entries(fake).map(([k, v]) => `${k}='${String(v).replace(/'/g, "'\\''")}'; export ${k}`).join("\n");
    const body = fs.readFileSync(path.join(bin, name), "utf8").replace("#!/bin/sh\n", `#!/bin/sh\n${exports}\n`);
    fs.writeFileSync(path.join(bin, name), body, { mode: 0o755 });
  }
  const args = ["--vendor", vendor, "--reviewer-type", "t", "--dispatch-id", "d1",
    "--instruction-file", options.instruction ?? path.join(inputs, "instr.md"), "--diff-file", path.join(inputs, "diff.patch"),
    "--target-paths-file", path.join(inputs, "changed.txt"), "--cwd", repo, ...extra];
  return runNode(DISPATCH, args, { bin, ...options });
}

const marked = (body) => `banner line\nFINDINGS BEGIN\n${body}\nFINDINGS END\n`;

test("a vendor missing from the local allow-list is refused", () => {
  const r = dispatch(fixture({ enable: ["devin"] }), "pi");
  assert.equal(r.code, 2);
  assert.equal(r.out.category, "vendor_not_allowed");
});

test("a git-tracked local file cannot enable a vendor", () => {
  const f = fixture();
  // -f: a global gitignore may ignore .claude/; force-adding is how a tracked copy would arise anyway.
  execFileSync("git", ["-C", f.repo, "add", "-f", ".claude/reviewadapters-kit.local.json"]);
  const r = dispatch(f, "pi");
  assert.equal(r.out.category, "vendor_not_allowed");
  assert.match(r.out.detail, /tracked/);
});

test("a secret-named target path needs --secret-paths-confirmed", () => {
  const f = fixture({ changed: "secrets.env" });
  assert.equal(dispatch(f, "pi").out.category, "secret_paths_unconfirmed");
  const dry = dispatch(f, "pi", ["--secret-paths-confirmed", "--dry-run"]);
  assert.equal(dry.out.dryRun, true);
});

test("a diff header naming a file missing from the target list is refused", () => {
  const f = fixture();
  fs.appendFileSync(path.join(f.inputs, "diff.patch"), "diff --git a/.env b/.env\ndeleted file mode 100644\n--- a/.env\n+++ /dev/null\n@@ -1 +0,0 @@\n-TOKEN=x\n");
  const r = dispatch(f, "pi");
  assert.equal(r.code, 1);
  assert.match(r.out.detail, /not in --target-paths-file/);
  // A removed line that looks like a header is hunk content, not a header.
  fs.writeFileSync(path.join(f.inputs, "diff.patch"), "diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n@@ -1 +1 @@\n--- a/other.py\n+x\n");
  assert.equal(dispatch(f, "pi", ["--dry-run"]).out.dryRun, true);
});

test("an instruction file inside a target path is a usage error", () => {
  const f = fixture();
  fs.writeFileSync(path.join(f.inputs, "changed.txt"), "calc.py\n.claude\n");
  fs.copyFileSync(path.join(f.inputs, "instr.md"), path.join(f.repo, ".claude", "instr.md"));
  const r = dispatch(f, "pi", [], {}, { instruction: path.join(f.repo, ".claude", "instr.md") });
  assert.equal(r.code, 1);
  assert.match(r.out.detail, /inside a target path/);
});

test("input files writable by others, and a --cwd below the repository root, are usage errors", () => {
  const f = fixture();
  fs.chmodSync(path.join(f.inputs, "diff.patch"), 0o666);
  assert.match(dispatch(f, "pi").out.detail, /writable by others/);
  fs.chmodSync(path.join(f.inputs, "diff.patch"), 0o600);
  const r = dispatch({ ...f, repo: path.join(f.repo, ".claude") }, "pi");
  assert.equal(r.code, 1);
  assert.match(r.out.detail, /top-level directory/);
});

test("malformed flags, an unknown vendor and a timeout above the cap are usage errors", () => {
  const f = fixture();
  for (const extra of [["--model", "x", "--model", "y"], ["--model=x"], ["--bogus"], ["--model"], ["--timeout-ms", "1e3"], ["--model", "-x"]]) {
    const r = dispatch(f, "pi", extra);
    assert.equal(r.code, 1, `${extra.join(" ")}: ${JSON.stringify(r.out)}`);
    assert.equal(r.out.category, "usage");
  }
  assert.equal(dispatch(f, "__proto__").out.category, "usage");
});

test("a vendor CLI missing from PATH is cli_unavailable", () => {
  const f = fixture();
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(f.inputs, "instr.md"),
    "--diff-file", path.join(f.inputs, "diff.patch"), "--target-paths-file", path.join(f.inputs, "changed.txt"), "--cwd", f.repo];
  // A PATH holding only git, so an installed pi elsewhere cannot make the test pass by accident.
  const only = tempDir("rva-test-onlygit-");
  fs.symlinkSync(execFileSync("sh", ["-c", "command -v git"], { encoding: "utf8" }).trim(), path.join(only, "git"));
  const r = spawnSync(process.execPath, [DISPATCH, ...args], { encoding: "utf8", env: { HOME: homeWithCodexKit(), PATH: only } });
  assert.equal(JSON.parse(r.stdout).category, "cli_unavailable");
});

test("each vendor runs with its isolation flags, the diff inline and a minimal environment", () => {
  const expectations = {
    pi: { must: ["--no-tools", "--no-extensions", "--no-mcp", "--no-context-files", "--offline"], mustNot: ["--tools", "--append-system-prompt"] },
    devin: { must: ["--prompt-file", "--config", "auto", "--respect-workspace-trust"], mustNot: ["--"] },
    agy: { must: ["--mode", "plan", "--sandbox", "--json-schema"], mustNot: [] }
  };
  for (const [vendor, { must, mustNot }] of Object.entries(expectations)) {
    const f = fixture();
    const record = path.join(f.inputs, `${vendor}.args`);
    const out = vendor === "agy" ? JSON.stringify({ structured_output: JSON.parse(GOOD) }) : marked(GOOD);
    const r = dispatch(f, vendor, [], { FAKE_ARGS: record, FAKE_OUT: out }, { env: { RVA_TEST_UNRELATED_TOKEN: "leak" } });
    assert.equal(r.code, 0, `${vendor}: ${JSON.stringify(r.out)}`);
    const args = fs.readFileSync(record, "utf8").split("\n");
    for (const flag of must) assert.ok(args.includes(flag), `${vendor} lacks ${flag}`);
    for (const flag of mustNot) assert.ok(!args.includes(flag), `${vendor} has ${flag}`);
    const env = fs.readFileSync(`${record}.env`, "utf8");
    assert.doesNotMatch(env, /RVA_TEST_UNRELATED_TOKEN/, `${vendor} received an unrelated variable`);
    assert.match(r.out.inspection_limits.join("\n"), /differs from the probed/);
  }
});

test("devin's config denies read, and the diff reaches it only through the prompt file", () => {
  const config = JSON.parse(fs.readFileSync(path.join(PLUGIN, "assets", "rva-devin-config.json"), "utf8"));
  for (const tool of ["read", "grep", "glob", "find_file_by_name", "exec", "edit", "write"]) assert.ok(config.permissions.deny.includes(tool), tool);
  assert.deepEqual(config.permissions.allow, []);
  const f = fixture();
  const r = dispatch(f, "devin", ["--dry-run"]);
  assert.ok(r.out.command.includes("--prompt-file"));
  assert.ok(!r.out.command.some((arg) => arg.includes("return a - b")), "the diff must not travel in devin's argv");
});

test("a vendor past the timeout is killed with its process group", () => {
  const f = fixture();
  const pidfile = path.join(f.inputs, "child.pid");
  const r = dispatch(f, "pi", ["--timeout-ms", "1500"], { FAKE_MODE: "sleep", FAKE_PIDFILE: pidfile });
  assert.equal(r.out.category, "timeout");
  const pid = Number(fs.readFileSync(pidfile, "utf8"));
  // The orphaned helper is reaped asynchronously, so poll for up to 3 s before deciding it survived.
  const deadline = Date.now() + 3000;
  let alive = true;
  while (alive && Date.now() < deadline) {
    try {
      process.kill(pid, 0);
      spawnSync("sleep", ["0.1"]);
    } catch {
      alive = false;
    }
  }
  assert.equal(alive, false, "the vendor's helper process outlived the timeout");
});

test("a helper that keeps stdout open does not turn a finished run into a timeout", () => {
  const f = fixture();
  const out = marked(GOOD);
  // The leader prints and exits while a background helper holds the pipe for 60 s.
  const r = dispatch(f, "pi", ["--timeout-ms", "20000"], { FAKE_MODE: "helper", FAKE_OUT: out });
  assert.equal(r.code, 0, JSON.stringify(r.out));
});

test("pi and devin envelopes are extracted from the last marked block and validated", () => {
  for (const vendor of ["pi", "devin"]) {
    const r = dispatch(fixture(), vendor, [], { FAKE_OUT: marked(GOOD) });
    assert.equal(r.code, 0, JSON.stringify(r.out));
    assert.equal(r.out.dispatch.backend, vendor);
    assert.equal(r.out.findings[0].components, null);
  }
});

test("missing, malformed and out-of-scope output become typed failures", () => {
  const f = fixture();
  assert.equal(dispatch(f, "pi", [], { FAKE_OUT: "no markers" }).out.category, "missing_final_message");
  assert.equal(dispatch(f, "pi", [], { FAKE_OUT: marked("{not json") }).out.category, "invalid_json");
  assert.equal(dispatch(f, "pi", [], { FAKE_OUT: marked('{"findings":[{"file":"calc.py"}],"verdict":"x","inspection_limits":[]}') }).out.category, "schema_validation_failure");
  const outside = GOOD.replace("calc.py:2", "other.py:1");
  assert.equal(dispatch(f, "pi", [], { FAKE_OUT: marked(outside) }).out.category, "semantic_validation_failure");
  assert.equal(dispatch(f, "pi", [], { FAKE_MODE: "fail" }).out.category, "non_zero_exit");
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: "null" }).out.category, "invalid_json");
});

test("agy SUCCESS with no output and denied actions is tool_denied, not a clean pass", () => {
  const out = JSON.stringify({ status: "SUCCESS", response: "", denied_actions: [{ action: "read_file" }] });
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: out }).out.category, "tool_denied");
  const ok = JSON.stringify({ status: "SUCCESS", structured_output: JSON.parse(GOOD) });
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: ok }).code, 0);
});

test("a prompt over agy's argument cap is refused before anything runs", () => {
  const f = fixture();
  fs.appendFileSync(path.join(f.inputs, "diff.patch"), "x".repeat(130_000));
  // The trailing text is outside any hunk, so the header check passes and the size gate decides.
  assert.equal(dispatch(f, "agy").out.category, "input_too_large");
});

test("--dry-run runs every gate and spawns nothing", () => {
  const f = fixture();
  const pidfile = path.join(f.inputs, "child.pid");
  const r = dispatch(f, "devin", ["--dry-run"], { FAKE_MODE: "sleep", FAKE_PIDFILE: pidfile });
  assert.equal(r.out.dryRun, true);
  assert.equal(r.out.recipient, "Cognition (Devin)");
  assert.equal(fs.existsSync(pidfile), false);
});

test("codex-kit not installed, or writable by others, is codex_kit_unavailable; the sibling needs the opt-in", () => {
  const f = fixture();
  assert.equal(dispatch(f, "pi", ["--dry-run"], {}, { home: homeWithCodexKit(null) }).out.category, "codex_kit_unavailable");
  assert.equal(dispatch(f, "pi", ["--dry-run"], {}, { home: homeWithCodexKit("relative/codex-kit") }).out.category, "codex_kit_unavailable");
  const opted = fixture({ local: { dev_sibling_codex_kit: true } });
  assert.equal(dispatch(opted, "pi", ["--dry-run"], {}, { home: homeWithCodexKit(null) }).out.dryRun, true);
  const copy = path.join(tempDir("rva-test-ck-"), "codex-kit");
  fs.cpSync(CODEX_KIT, copy, { recursive: true });
  fs.chmodSync(path.join(copy, "scripts", "lib", "codex-exec.mjs"), 0o666);
  assert.match(dispatch(f, "pi", ["--dry-run"], {}, { home: homeWithCodexKit(copy) }).out.detail, /writable by others/);
});

test("the dispatcher runs from a plugin path with a space and a non-ASCII character", () => {
  const root = path.join(tempDir("rva-test-path-"), "plugins dir ü");
  fs.cpSync(PLUGIN, path.join(root, "reviewadapters-kit"), { recursive: true });
  const f = fixture();
  const copied = path.join(root, "reviewadapters-kit", "scripts", "rva-dispatch.mjs");
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(f.inputs, "instr.md"),
    "--diff-file", path.join(f.inputs, "diff.patch"), "--target-paths-file", path.join(f.inputs, "changed.txt"), "--cwd", f.repo, "--dry-run"];
  const r = runNode(copied, args);
  assert.equal(r.out?.dryRun, true, r.raw.stdout + r.raw.stderr);
});

test("prepare lists deleted files and both rename sides, and refuses unsupported names", () => {
  const repo = tempDir("rva-test-prep-");
  execFileSync("git", ["init", "-q", repo]);
  fs.writeFileSync(path.join(repo, ".env"), "TOKEN=x\n");
  fs.writeFileSync(path.join(repo, "a.txt"), "one\ntwo\nthree\n");
  // -f: a global gitignore may ignore .env.
  git(repo, "add", "-f", ".env", "a.txt");
  git(repo, "commit", "-q", "-m", "init");
  fs.rmSync(path.join(repo, ".env"));
  git(repo, "mv", "a.txt", "b.txt");
  const r = runNode(PREPARE, ["--cwd", repo]);
  assert.equal(r.out.ok, true, JSON.stringify(r.out));
  created.push(r.out.dir);
  assert.deepEqual(fs.readFileSync(r.out.target_paths_file, "utf8").trim().split("\n").sort(), [".env", "a.txt", "b.txt"]);
  assert.deepEqual(r.out.secret_paths, [".env"]);
  assert.equal(fs.statSync(r.out.dir).mode & 0o777, 0o700);
  fs.writeFileSync(path.join(repo, "b.txt"), "changed\n");
  fs.writeFileSync(path.join(repo, "my file.txt"), "x\n");
  git(repo, "add", "my file.txt");
  const bad = runNode(PREPARE, ["--cwd", repo]);
  assert.equal(bad.out.ok, false);
  assert.match(bad.out.detail, /names outside/);
});

test("prepare refuses an empty diff", () => {
  const repo = tempDir("rva-test-prep-");
  execFileSync("git", ["init", "-q", repo]);
  fs.writeFileSync(path.join(repo, "a.txt"), "x\n");
  git(repo, "add", "-A");
  git(repo, "commit", "-q", "-m", "init");
  const r = runNode(PREPARE, ["--cwd", repo]);
  assert.equal(r.out.ok, false);
  assert.match(r.out.detail, /no reviewable changes/);
});

test("a tracked local file, under any letter case, cannot enable a vendor or the sibling codex-kit", () => {
  const opted = fixture({ local: { dev_sibling_codex_kit: true } });
  execFileSync("git", ["-C", opted.repo, "add", "-f", ".claude/reviewadapters-kit.local.json"]);
  assert.equal(dispatch(opted, "pi", ["--dry-run"], {}, { home: homeWithCodexKit(null) }).out.category, "codex_kit_unavailable");
  const f = fixture();
  fs.writeFileSync(path.join(f.repo, ".claude", "ReviewAdapters-Kit.local.json"), "{}");
  execFileSync("git", ["-C", f.repo, "add", "-f", ".claude/ReviewAdapters-Kit.local.json"]);
  const r = dispatch(f, "pi");
  assert.equal(r.out.category, "vendor_not_allowed");
  assert.match(r.out.detail, /tracked/);
});

test("diffHeaderPaths reads headers and refuses malformed hunks", () => {
  assert.deepEqual(diffHeaderPaths("diff --git a/x b/x\ndeleted file mode 100644\n--- a/x\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n\\ No newline at end of file\n").paths, ["x"]);
  assert.deepEqual(diffHeaderPaths("diff --git a/a b/b\nsimilarity index 90%\nrename from a\nrename to b\n").paths.sort(), ["a", "b"]);
  // A blank context line (diff.suppressBlankEmpty) counts as context.
  assert.deepEqual(diffHeaderPaths("--- a/x\n+++ b/x\n@@ -1,3 +1,3 @@\n a\n\n-b\n+c\n").paths, ["x"]);
  assert.match(diffHeaderPaths('diff --git "a/x y" "b/x y"\n').error, /quoted/);
  assert.match(diffHeaderPaths("--- a/x\n+++ b/x\n@@ -1,2 +1,2 @@\n a\n").error, /ends inside a hunk/);
  // Header lines hidden inside a hunk whose new side is already used up: "+++ b/.env" would be a third
  // "+" line in a hunk that declares one, so it is refused instead of read as content.
  assert.match(diffHeaderPaths("--- a/x\n+++ b/x\n@@ -1,2 +1 @@\n+x\n--- a/.env\n+++ b/.env\n").error, /more lines/);
  // After a complete hunk, the same lines are real headers and are reported.
  assert.deepEqual(diffHeaderPaths("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n--- a/.env\n+++ b/.env\n").paths, ["x", ".env"]);
  assert.match(diffHeaderPaths("hello\n").error, /names no file/);
  assert.match(diffHeaderPaths("--- x\n+++ y\n").error, /no a\/ or b\/ prefix/);
});

test("a version other than the probed one is matched as a whole token", () => {
  const f = fixture();
  const r = dispatch(f, "pi", [], { FAKE_OUT: marked(GOOD) });
  assert.match(r.out.inspection_limits.join("\n"), /differs from the probed 1\.5\.0/);
});

test("a timeout above the configured limit is clamped to it, not raised", () => {
  const r = dispatch(fixture(), "pi", ["--timeout-ms", String(SHIPPED_TIMEOUT + 1), "--dry-run"]);
  assert.equal(r.out.dryRun, true, JSON.stringify(r.out));
});

test("a vendor binary inside the reviewed repository is never run", () => {
  const f = fixture();
  const inside = path.join(f.repo, "bin");
  fs.mkdirSync(inside);
  fs.writeFileSync(path.join(inside, "pi"), "#!/bin/sh\necho planted\n", { mode: 0o755 });
  const only = tempDir("rva-test-onlygit-");
  fs.symlinkSync(execFileSync("sh", ["-c", "command -v git"], { encoding: "utf8" }).trim(), path.join(only, "git"));
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(f.inputs, "instr.md"),
    "--diff-file", path.join(f.inputs, "diff.patch"), "--target-paths-file", path.join(f.inputs, "changed.txt"), "--cwd", f.repo, "--dry-run"];
  const r = spawnSync(process.execPath, [DISPATCH, ...args], { encoding: "utf8", env: { HOME: homeWithCodexKit(), PATH: `${inside}${path.delimiter}${only}` } });
  assert.equal(JSON.parse(r.stdout).category, "cli_unavailable");
});
