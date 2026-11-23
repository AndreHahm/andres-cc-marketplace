#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms --isolate-project true (issue #862) adds the project-isolation
// config overrides to the `codex exec` arguments, that nothing else does, and
// that a malformed flag is rejected. Runs the real CLI in --dry-run with a
// throwaway `codex` stub on PATH (skipped on Windows).
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-isolate-project.mjs

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { PROJECT_ISOLATION_ARGS } from "../lib/codex-exec.mjs";
import { neutralizeSkillMentions } from "../../skills/codex-review-bridge/scripts/bridge-invoke.mjs";

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

if (process.platform === "win32") {
  console.log("SKIP  the codex stub is a POSIX script");
  process.exit(0);
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-isolate-smoke-"));
try {
  fs.mkdirSync(path.join(tmpDir, "target"));
  fs.mkdirSync(path.join(tmpDir, "bin"));
  fs.writeFileSync(path.join(tmpDir, "bin", "codex"), "#!/bin/sh\nexit 1\n", { mode: 0o755 });
  const instructionFile = path.join(tmpDir, "reviewer.md");
  fs.writeFileSync(instructionFile, "Quote `$VAR`, not $$x or \\$y; ${Z} and $(date) cost 5 $ each.");
  const run = (args) =>
    spawnSync(
      process.execPath,
      [BRIDGE_INVOKE, "--reviewer-type", "r", "--instruction-file", instructionFile, "--target-paths", "target", "--execution-profile", "read-only", "--dispatch-id", "smoke", "--cwd", tmpDir, "--dry-run", "true", ...args],
      { encoding: "utf8", env: { ...process.env, PATH: `${path.join(tmpDir, "bin")}${path.delimiter}${process.env.PATH}` } }
    );
  const codexArgs = (args) => {
    const result = run(args);
    return result.status === 0 ? JSON.parse(result.stdout).wouldRun.args.join(" ") : `FAILED: ${result.stderr}`;
  };
  const promptOf = (args) => JSON.parse(run(args).stdout).wouldRun.prompt;
  const mention = /\$[A-Za-z0-9_$-]/;

  for (const [label, text, want] of [
    ["a name", "$VAR", "$\u200bVAR"],
    ["a doubled sigil", "$$x", "$\u200b$\u200bx"],
    ["a non-ASCII name", "$\u00e9", "$\u200b\u00e9"],
    ["nothing to split", "${Z} $(date) 5 $ $", "${Z} $(date) 5 $ $"],
    ["already split text", "$\u200bVAR", "$\u200b\u200bVAR"]
  ]) {
    check(`mentions: ${label}`, neutralizeSkillMentions(text) === want, JSON.stringify(neutralizeSkillMentions(text)));
  }
  const isolated = promptOf(["--isolate-project", "true"]);
  check("true leaves no mention in the prompt", !mention.test(isolated) && isolated.includes("$\u200bVAR"));
  check("true keeps the other dollar forms", isolated.includes("${Z} and $(date) cost 5 $ each"));
  check("no flag leaves the prompt alone", promptOf([]).includes("`$VAR`, not $$x"));

  const isolation = PROJECT_ISOLATION_ARGS.join(" ");

  check("the overrides are the two known ones", isolation === "-c project_doc_max_bytes=0 -c skills.include_instructions=false", isolation);
  check("true adds the overrides", codexArgs(["--isolate-project", "true"]).includes(isolation));
  for (const [label, args] of [["no flag", []], ["false", ["--isolate-project", "false"]]]) {
    const got = codexArgs(args);
    check(`${label} adds none`, got.startsWith("exec ") && !got.includes("project_doc_max_bytes"), got);
  }
  for (const [label, args] of [
    ["another value", ["--isolate-project", "yes"]],
    ["an upper-case value", ["--isolate-project", "TRUE"]],
    ["an empty value", ["--isolate-project", ""]],
    ["given twice", ["--isolate-project", "true", "--isolate-project", "false"]],
    ["the = form", ["--isolate-project=true"]],
    ["a case variant", ["--Isolate-Project", "true"]],
    ["no value", ["--isolate-project"]],
    ["another flag as its value", ["--isolate-project", "--model"]]
  ]) {
    const result = run(args);
    check(`rejected: ${label}`, result.status === 1 && result.stderr.includes("--isolate-project"), result.stderr || result.stdout.slice(0, 120));
  }
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
