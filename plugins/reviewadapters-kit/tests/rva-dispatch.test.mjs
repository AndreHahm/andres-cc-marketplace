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
const { openInCheckedDir, LocalFileRefused } = await import(path.join(PLUGIN, "scripts", "rva-config.mjs"));
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

// A fixture repository (git init, nothing committed) with one changed file and the dispatch inputs. The
// fake vendors report an unprobed version, so the fixture allows it unless a test says otherwise.
function fixture({ enable = ["pi", "devin", "agy"], changed = "calc.py", local = {}, unprobed = true, piModels } = {}) {
  const repo = tempDir("rva-test-repo-");
  execFileSync("git", ["init", "-q", repo]);
  fs.writeFileSync(path.join(repo, "calc.py"), "def add(a, b):\n    return a - b\n");
  fs.mkdirSync(path.join(repo, ".claude"), { mode: 0o700 });
  fs.chmodSync(path.join(repo, ".claude"), 0o700);
  const vendors = Object.fromEntries(enable.map((v) => [v, unprobed ? { enabled: true, allow_unprobed_version: true } : { enabled: true }]));
  if (piModels && vendors.pi) vendors.pi.models = piModels;
  fs.writeFileSync(path.join(repo, ".claude", "reviewadapters-kit.local.json"), JSON.stringify({ vendors, ...local }), { mode: 0o600 });
  fs.chmodSync(path.join(repo, ".claude", "reviewadapters-kit.local.json"), 0o600);
  const inputs = tempDir("rva-test-in-");
  fs.writeFileSync(path.join(inputs, "instr.md"), "Review it.\n");
  fs.writeFileSync(path.join(inputs, "diff.patch"), changed === "calc.py" ? DIFF : `diff --git a/${changed} b/${changed}\n`);
  fs.writeFileSync(path.join(inputs, "changed.txt"), `${changed}\n`);
  // Private like a real caller's files, whatever the umask and primary group of the test machine.
  for (const name of ["instr.md", "diff.patch", "changed.txt"]) fs.chmodSync(path.join(inputs, name), 0o600);
  return { repo, inputs };
}

// Fake vendor binaries: each records its arguments, environment and stdin, then prints FAKE_OUT, sleeps,
// or exits non-zero, per FAKE_MODE.
function fakeBin() {
  const dir = tempDir("rva-test-bin-");
  const script = `#!/bin/sh
if [ "$1" = "--version" ]; then if [ -n "$FAKE_VERSION_SLEEP" ]; then sleep "$FAKE_VERSION_SLEEP"; fi; echo "fake 1.0"; exit 0; fi
if [ -n "$FAKE_ARGS" ]; then printf '%s\\n' "$@" > "$FAKE_ARGS"; env > "$FAKE_ARGS.env"; cat > "$FAKE_ARGS.stdin"; fi
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
// agy's stream-json output (shape from a live agy 1.5.9 probe, references/vendors.md): an init event,
// step updates, then the result event.
const agyStream = (result) => [
  JSON.stringify({ event: "init", init: { cwd: "/tmp/x" } }),
  JSON.stringify({ event: "step_update", step_update: { step_index: 0, state: "DONE", step_type: "user_input" } }),
  JSON.stringify({ event: "result", result })
].join("\n");

test("a vendor missing from the local allow-list, or a pi --model the local file does not allow, is refused", () => {
  const r = dispatch(fixture({ enable: ["devin"] }), "pi");
  assert.equal(r.code, 2);
  assert.equal(r.out.category, "vendor_not_allowed");
  // pi's model picks who receives the diff, so a caller's --model must be the configured model or one the
  // local file lists; a bare id or another id on the same provider prefix is not enough.
  const f = fixture();
  for (const model of ["openai/gpt-x", "nvidia", "nvidia/another-model"]) {
    const refused = dispatch(f, "pi", ["--model", model, "--dry-run"]);
    assert.equal(refused.out.category, "vendor_not_allowed", `${model}: ${JSON.stringify(refused.out)}`);
  }
  const listed = dispatch(fixture({ piModels: ["nvidia/another-model"] }), "pi", ["--model", "nvidia/another-model", "--dry-run"]);
  assert.equal(listed.out.dryRun, true, JSON.stringify(listed.out));
  assert.equal(listed.out.model, "nvidia/another-model");
});

test("a git-tracked local file, or one writable by others, cannot enable a vendor", () => {
  const f = fixture();
  // -f: a global gitignore may ignore .claude/; force-adding is how a tracked copy would arise anyway.
  execFileSync("git", ["-C", f.repo, "add", "-f", ".claude/reviewadapters-kit.local.json"]);
  const r = dispatch(f, "pi");
  assert.equal(r.out.category, "vendor_not_allowed");
  assert.match(r.out.detail, /tracked/);
  const open = fixture();
  fs.chmodSync(path.join(open.repo, ".claude", "reviewadapters-kit.local.json"), 0o666);
  const w = dispatch(open, "pi", ["--dry-run"]);
  assert.equal(w.out.category, "vendor_not_allowed", JSON.stringify(w.out));
  assert.match(w.out.detail, /writable by others/);
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
    agy: { must: ["--input-format", "stream-json", "--mode", "plan", "--sandbox", "--json-schema", "-p="], mustNot: ["-p", "--print"] }
  };
  for (const [vendor, { must, mustNot }] of Object.entries(expectations)) {
    const f = fixture();
    const record = path.join(f.inputs, `${vendor}.args`);
    const out = vendor === "agy" ? agyStream({ status: "SUCCESS", structured_output: JSON.parse(GOOD) }) : marked(GOOD);
    const r = dispatch(f, vendor, [], { FAKE_ARGS: record, FAKE_OUT: out }, { env: { RVA_TEST_UNRELATED_TOKEN: "leak", XDG_RUNTIME_DIR: "/run/user/rva-test" } });
    assert.equal(r.code, 0, `${vendor}: ${JSON.stringify(r.out)}`);
    const args = fs.readFileSync(record, "utf8").split("\n");
    for (const flag of must) assert.ok(args.includes(flag), `${vendor} lacks ${flag}`);
    for (const flag of mustNot) assert.ok(!args.includes(flag), `${vendor} has ${flag}`);
    const env = fs.readFileSync(`${record}.env`, "utf8");
    assert.doesNotMatch(env, /RVA_TEST_UNRELATED_TOKEN/, `${vendor} received an unrelated variable`);
    assert.doesNotMatch(env, /^XDG_RUNTIME_DIR=/m, `${vendor} received XDG_RUNTIME_DIR`);
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
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: "not json" }).out.category, "invalid_json");
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: JSON.stringify({ event: "result", result: null }) }).out.category, "invalid_json");
  // Events without a result event: the run ended without an outcome.
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: "null" }).out.category, "missing_final_message");
});

test("agy SUCCESS with no output and denied actions is tool_denied, not a clean pass", () => {
  const out = agyStream({ status: "SUCCESS", response: "", denied_actions: [{ action: "read_file" }] });
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: out }).out.category, "tool_denied");
  const ok = agyStream({ status: "SUCCESS", structured_output: JSON.parse(GOOD) });
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: ok }).code, 0);
  // A result that is not SUCCESS may be partial, so its structured_output is not used.
  const partial = agyStream({ status: "ERROR", structured_output: JSON.parse(GOOD) });
  assert.equal(dispatch(fixture(), "agy", [], { FAKE_OUT: partial }).out.category, "missing_final_message");
});

test("agy's prompt travels on stdin from the private prompt file, never on the command line, so a large diff is not refused", () => {
  const f = fixture();
  // The trailing text is outside any hunk, so the header check passes; it used to exceed the argv cap.
  // It also carries U+2028 and U+2029, which must not break the stdin line.
  fs.appendFileSync(path.join(f.inputs, "diff.patch"), `${String.fromCharCode(0x2028)}${String.fromCharCode(0x2029)}${"x".repeat(130_000)}`);
  const record = path.join(f.inputs, "agy-stdin.args");
  const r = dispatch(f, "agy", [], { FAKE_ARGS: record, FAKE_OUT: agyStream({ status: "SUCCESS", structured_output: JSON.parse(GOOD) }) });
  assert.equal(r.code, 0, JSON.stringify(r.out));
  assert.doesNotMatch(fs.readFileSync(record, "utf8"), /return a - b/, "the diff must not travel in agy's argv");
  const raw = fs.readFileSync(`${record}.stdin`, "utf8");
  assert.doesNotMatch(raw, new RegExp(`[${String.fromCharCode(0x2028, 0x2029)}]`), "a Unicode line separator reached stdin unescaped");
  const lines = raw.trim().split("\n");
  assert.equal(lines.length, 1);
  const message = JSON.parse(lines[0]);
  assert.equal(message.event, "user");
  assert.match(message.message.content, /return a - b/);
  assert.ok(message.message.content.includes(String.fromCharCode(0x2028)), "the escaped separator must decode back to the same text");
  assert.match(message.message.content, /x{130000}/);
});

test("--dry-run runs the five gates and spawns nothing", () => {
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
  // Outside a plugins/ directory (like this repository's .claude/ mirror) the opt-in finds no sibling,
  // even when a codex-kit directory sits next to the plugin.
  const elsewhere = path.join(tempDir("rva-test-mirror-"), "notplugins");
  fs.cpSync(PLUGIN, path.join(elsewhere, "reviewadapters-kit"), { recursive: true });
  fs.cpSync(CODEX_KIT, path.join(elsewhere, "codex-kit"), { recursive: true });
  const mirrored = path.join(elsewhere, "reviewadapters-kit", "scripts", "rva-dispatch.mjs");
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(opted.inputs, "instr.md"),
    "--diff-file", path.join(opted.inputs, "diff.patch"), "--target-paths-file", path.join(opted.inputs, "changed.txt"), "--cwd", opted.repo, "--dry-run"];
  assert.match(runNode(mirrored, args, { home: homeWithCodexKit(null) }).out.detail, /was not found/);
  // Nor from a .claude/ mirror inside a checkout whose own directory is named plugins: the sibling would
  // be <checkout>/codex-kit, which no plugin occupies.
  const checkout = path.join(tempDir("rva-test-mirror-"), "plugins");
  fs.cpSync(PLUGIN, path.join(checkout, ".claude"), { recursive: true });
  fs.cpSync(CODEX_KIT, path.join(checkout, "codex-kit"), { recursive: true });
  const inMirror = path.join(checkout, ".claude", "scripts", "rva-dispatch.mjs");
  assert.match(runNode(inMirror, args, { home: homeWithCodexKit(null) }).out.detail, /was not found/);
});

test("a models list in the shipped settings never widens pi's allowed models; only the local file can", () => {
  const root = path.join(tempDir("rva-test-shipped-"), "plugins");
  fs.cpSync(PLUGIN, path.join(root, "reviewadapters-kit"), { recursive: true });
  const settings = path.join(root, "reviewadapters-kit", "reviewadapters-kit.settings.json");
  const shipped = JSON.parse(fs.readFileSync(settings, "utf8"));
  shipped.vendors.pi.models = ["openai/gpt-x"];
  fs.writeFileSync(settings, JSON.stringify(shipped));
  const f = fixture();
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(f.inputs, "instr.md"),
    "--diff-file", path.join(f.inputs, "diff.patch"), "--target-paths-file", path.join(f.inputs, "changed.txt"), "--cwd", f.repo,
    "--model", "openai/gpt-x", "--dry-run"];
  const r = runNode(path.join(root, "reviewadapters-kit", "scripts", "rva-dispatch.mjs"), args);
  assert.equal(r.out?.category, "vendor_not_allowed", r.raw.stdout + r.raw.stderr);
});

test("a .claude directory that is a symbolic link, or writable by others, cannot enable a vendor", () => {
  const linked = fixture();
  const real = path.join(tempDir("rva-test-realdir-"), "claude");
  fs.renameSync(path.join(linked.repo, ".claude"), real);
  fs.symlinkSync(real, path.join(linked.repo, ".claude"));
  assert.equal(dispatch(linked, "pi", ["--dry-run"]).out.category, "vendor_not_allowed");
  const open = fixture();
  fs.chmodSync(path.join(open.repo, ".claude"), 0o777);
  const r = dispatch(open, "pi", ["--dry-run"]);
  assert.equal(r.out.category, "vendor_not_allowed", JSON.stringify(r.out));
  assert.match(r.out.detail, /writable by others/);
});

// A .claude directory holding a local file, and a private replacement that would enable something else.
function swappableClaudeDir() {
  const repo = tempDir("rva-test-swap-");
  for (const [dir, body] of [[".claude", '{"original":true}'], ["planted", '{"planted":true}']]) {
    fs.mkdirSync(path.join(repo, dir), { mode: 0o700 });
    fs.chmodSync(path.join(repo, dir), 0o700);
    fs.writeFileSync(path.join(repo, dir, "reviewadapters-kit.local.json"), body, { mode: 0o600 });
    fs.chmodSync(path.join(repo, dir, "reviewadapters-kit.local.json"), 0o600);
  }
  const file = path.join(repo, ".claude", "reviewadapters-kit.local.json");
  const swap = () => {
    fs.renameSync(path.join(repo, ".claude"), path.join(repo, "moved"));
    fs.renameSync(path.join(repo, "planted"), path.join(repo, ".claude"));
  };
  return { file, swap };
}

test("the local file is read from the .claude directory that was checked, even if it is swapped before the open", { skip: process.platform !== "linux" && "the handle-based open is Linux only" }, () => {
  const { file, swap } = swappableClaudeDir();
  const fd = openInCheckedDir(file, { afterDirCheck: swap });
  try {
    assert.deepEqual(JSON.parse(fs.readFileSync(fd, "utf8")), { original: true });
  } finally {
    fs.closeSync(fd);
  }
});

test("on the by-path fallback, a .claude directory swapped before the open is refused", () => {
  const { file, swap } = swappableClaudeDir();
  assert.throws(() => openInCheckedDir(file, { byPath: true, afterDirCheck: swap }), (error) => error instanceof LocalFileRefused && /changed/.test(error.message));
  // Without a swap the fallback reads the file.
  const plain = swappableClaudeDir();
  const fd = openInCheckedDir(plain.file, { byPath: true });
  fs.closeSync(fd);
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

test("an unprobed version is noted for pi and refused for devin and agy unless the local file allows it", () => {
  const f = fixture({ unprobed: false });
  const r = dispatch(f, "pi", [], { FAKE_OUT: marked(GOOD) });
  assert.match(r.out.inspection_limits.join("\n"), /differs from the probed 1\.5\.0/);
  for (const vendor of ["devin", "agy"]) {
    const record = path.join(f.inputs, `${vendor}-unprobed.args`);
    const refused = dispatch(f, vendor, [], { FAKE_ARGS: record, FAKE_OUT: marked(GOOD) });
    assert.equal(refused.out.category, "unsupported_cli_version", `${vendor}: ${JSON.stringify(refused.out)}`);
    assert.equal(fs.existsSync(record), false, `${vendor} was spawned with the diff`);
  }
});

test("a timeout above the configured limit is clamped to it, not raised", () => {
  const r = dispatch(fixture(), "pi", ["--timeout-ms", String(SHIPPED_TIMEOUT + 1), "--dry-run"]);
  assert.equal(r.out.dryRun, true, JSON.stringify(r.out));
});

test("a --version probe that hangs never outlasts a timeout below the probe's own 15 s limit", () => {
  const f = fixture();
  const record = path.join(f.inputs, "slow-version.args");
  const started = Date.now();
  const r = dispatch(f, "pi", ["--timeout-ms", "1000"], { FAKE_VERSION_SLEEP: "30", FAKE_ARGS: record, FAKE_OUT: marked(GOOD) });
  const elapsed = Date.now() - started;
  assert.equal(r.out.category, "timeout", JSON.stringify(r.out));
  assert.match(r.out.detail, /nothing was sent/);
  assert.equal(fs.existsSync(record), false, "the vendor was spawned with the diff");
  assert.ok(elapsed < 10_000, `the dispatcher took ${elapsed} ms for a 1000 ms budget`);
});

test("Windows is refused before anything is written or sent, dry run included", () => {
  const f = fixture();
  const forceWin32 = "data:text/javascript,Object.defineProperty(process,'platform',{value:'win32'})";
  const args = ["--vendor", "pi", "--reviewer-type", "t", "--dispatch-id", "d1", "--instruction-file", path.join(f.inputs, "instr.md"),
    "--diff-file", path.join(f.inputs, "diff.patch"), "--target-paths-file", path.join(f.inputs, "changed.txt"), "--cwd", f.repo];
  for (const extra of [[], ["--dry-run"]]) {
    const record = path.join(f.inputs, `win32${extra.length}.args`);
    const bin = fakeBin();
    const r = spawnSync(process.execPath, ["--import", forceWin32, DISPATCH, ...args, ...extra], { encoding: "utf8", env: { ...process.env, HOME: homeWithCodexKit(), PATH: `${bin}${path.delimiter}${process.env.PATH}`, FAKE_ARGS: record } });
    assert.equal(r.status, 2, r.stderr);
    assert.equal(JSON.parse(r.stdout.trim()).category, "unsupported_platform");
    assert.equal(fs.existsSync(record), false, "a vendor was spawned on win32");
  }
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
