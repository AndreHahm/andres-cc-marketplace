#!/usr/bin/env node
// Build the three fixtures evals.json refers to, in a new private directory under the OS temp
// directory, and print that directory as JSON: { "fixtures": "<dir>" }. Each fixture is
// <dir>/<name>/repo (a git repository with an untracked .claude/reviewadapters-kit.local.json) and
// <dir>/<name>/inputs (instructions.md, diff.patch, targets.txt). Everything is created 0700/0600 so the
// dispatcher's ownership checks pass. Nothing is written inside this checkout.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { enclosingRepoRoot, findBinary } from "../../plugins/reviewadapters-kit/scripts/rva-config.mjs";

// git from a PATH entry outside this checkout, the same way the dispatcher resolves it.
const CHECKOUT = enclosingRepoRoot(path.dirname(fileURLToPath(import.meta.url)));
if (!CHECKOUT) throw new Error("this script must run from inside its checkout");
const GIT = findBinary("git", CHECKOUT);
if (!GIT) throw new Error("git not found on PATH outside this checkout");

const CALC_DIFF = "diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a + b\n+    return a - b\n";
const PEM_DIFF = "diff --git a/deploy.pem b/deploy.pem\nnew file mode 100644\n--- /dev/null\n+++ b/deploy.pem\n@@ -0,0 +1 @@\n+placeholder, not a key\n";
const OTHER_DIFF = "diff --git a/other.py b/other.py\n--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n";
const INSTRUCTIONS = "Review the diff for bugs. Report each with its location and a fix.\n";

// dev_sibling_codex_kit lets the dispatcher use this checkout's codex-kit when it is not installed.
const FIXTURES = {
  "vendor-not-enabled": { local: { dev_sibling_codex_kit: true, vendors: {} }, diff: CALC_DIFF, targets: ["calc.py"] },
  "secret-path": { local: { dev_sibling_codex_kit: true, vendors: { pi: { enabled: true } } }, diff: PEM_DIFF, targets: ["deploy.pem"] },
  "header-not-in-targets": { local: { dev_sibling_codex_kit: true, vendors: { pi: { enabled: true } } }, diff: CALC_DIFF + OTHER_DIFF, targets: ["calc.py"] }
};

function privateDir(dir) {
  fs.mkdirSync(dir, { mode: 0o700 });
  fs.chmodSync(dir, 0o700);
}

function privateFile(file, text) {
  fs.writeFileSync(file, text, { mode: 0o600 });
  fs.chmodSync(file, 0o600);
}

const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "rva-eval-fixtures-")));
fs.chmodSync(root, 0o700);
for (const [name, spec] of Object.entries(FIXTURES)) {
  const base = path.join(root, name);
  privateDir(base);
  const repo = path.join(base, "repo");
  privateDir(repo);
  execFileSync(GIT, ["init", "-q", repo]);
  privateDir(path.join(repo, ".claude"));
  privateFile(path.join(repo, ".claude", "reviewadapters-kit.local.json"), `${JSON.stringify(spec.local)}\n`);
  const inputs = path.join(base, "inputs");
  privateDir(inputs);
  privateFile(path.join(inputs, "instructions.md"), INSTRUCTIONS);
  privateFile(path.join(inputs, "diff.patch"), spec.diff);
  privateFile(path.join(inputs, "targets.txt"), `${spec.targets.join("\n")}\n`);
}
process.stdout.write(`${JSON.stringify({ fixtures: root })}\n`);
