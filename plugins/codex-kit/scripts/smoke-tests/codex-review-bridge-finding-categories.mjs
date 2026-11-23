#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms --finding-categories (issue #862) adds a required `category` enum to
// the schema of that call only, leaves the default envelope unchanged, and
// rejects a malformed list. The CLI part runs with a throwaway `codex` stub on
// PATH in --dry-run, so no installed Codex CLI is needed (skipped on Windows).
//
// Runnable from any cwd: node plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-finding-categories.mjs

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { findSchemaViolation } from "../lib/codex-exec.mjs";
import { ENVELOPE_SCHEMA, semanticallyValidate, withFindingCategories } from "../../skills/codex-review-bridge/scripts/bridge-invoke.mjs";

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

function envelope(extra) {
  return {
    contract_version: "1",
    dispatch: { id: "d", reviewer: "r", backend: "codex", target_paths: ["a"] },
    provenance: { provider: "p", model: "m", cli_version: "c", execution_profile: "read-only" },
    findings: [{ id: "M1", severity: "major", axis: "a", location: "a", evidence: "e", finding: "f", fix: "x", confidence: "high", components: null, ...extra }],
    verdict: "fail",
    inspection_limits: []
  };
}

const before = JSON.stringify(ENVELOPE_SCHEMA);
const schema = withFindingCategories(ENVELOPE_SCHEMA, ["grant", "other"]);
const items = schema.properties.findings.items;

check("the variant requires category", items.required.includes("category"));
check("every property is required (strict structured output)", Object.keys(items.properties).every((k) => items.required.includes(k)));
check("the default schema is unchanged", JSON.stringify(ENVELOPE_SCHEMA) === before && !before.includes('"category"'));
check("a named category conforms", !findSchemaViolation(envelope({ category: "other" }), schema));
check("a missing category violates the variant", Boolean(findSchemaViolation(envelope({}), schema)));
check("an unnamed category violates the variant", Boolean(findSchemaViolation(envelope({ category: "else" }), schema)));
check("the default schema still accepts no category", !findSchemaViolation(envelope({}), ENVELOPE_SCHEMA));

const semanticRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-category-semantic-"));
try {
  for (const name of ["a.md", "b.md", "c.md"]) fs.writeFileSync(path.join(semanticRoot, name), name);
  const grant = { category: "grant" };
  const categoryAfter = (components, extra = grant) => {
    const data = envelope({ location: "a.md:1", components, ...extra });
    const result = semanticallyValidate(data, { targetPaths: ["a.md", "b.md"], dispatchId: "d", reviewerType: "r", repoRoot: semanticRoot });
    return result.ok ? data.findings[0].category : result;
  };
  check("no components keeps the category", categoryAfter(null) === "grant");
  check("kept components keep the category", categoryAfter(["b.md:2"]) === "grant");
  check("an out-of-scope component clears it", categoryAfter(["c.md:2"]) === null);
  check("a nonexistent component clears it", categoryAfter(["b.md", "missing.md"]) === null);
  check("a malformed component clears it", categoryAfter(["b.md:20-30"]) === null);
  check("an empty component clears it", categoryAfter([""]) === null);
  check("a finding without a category gains none", categoryAfter(["c.md"], {}) === undefined);
} finally {
  fs.rmSync(semanticRoot, { recursive: true, force: true });
}

if (process.platform === "win32") {
  console.log("SKIP  CLI checks (the codex stub is a POSIX script)");
} else {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-review-bridge-categories-smoke-"));
  try {
    fs.mkdirSync(path.join(tmpDir, "target"));
    fs.mkdirSync(path.join(tmpDir, "bin"));
    fs.writeFileSync(path.join(tmpDir, "bin", "codex"), "#!/bin/sh\nexit 1\n", { mode: 0o755 });
    const instructionFile = path.join(tmpDir, "reviewer.md");
    fs.writeFileSync(instructionFile, "trusted instructions");
    const run = (args) =>
      spawnSync(
        process.execPath,
        [BRIDGE_INVOKE, "--reviewer-type", "r", "--instruction-file", instructionFile, "--target-paths", "target", "--execution-profile", "read-only", "--dispatch-id", "smoke", "--cwd", tmpDir, "--dry-run", "true", ...args],
        { encoding: "utf8", env: { ...process.env, PATH: `${path.join(tmpDir, "bin")}${path.delimiter}${process.env.PATH}` } }
      );

    for (const [label, args] of [
      ["no flag", []],
      ["one value", ["--finding-categories", "other"]],
      ["two values", ["--finding-categories", "allowed-tools-grant,other"]]
    ]) {
      const result = run(args);
      check(`accepted: ${label}`, result.status === 0, result.stderr);
    }
    for (const [label, args] of [
      ["empty value", ["--finding-categories", ""]],
      ["empty entry", ["--finding-categories", "a,,b"]],
      ["padded entry", ["--finding-categories", "a, b"]],
      ["duplicate entry", ["--finding-categories", "a,a"]],
      ["given twice", ["--finding-categories", "a", "--finding-categories", "b"]],
      ["the = form", ["--finding-categories=a"]],
      ["a case variant", ["--Finding-Categories", "a"]],
      ["no value", ["--finding-categories"]],
      ["another flag as its value", ["--finding-categories", "--model"]]
    ]) {
      const result = run(args);
      check(`rejected: ${label}`, result.status === 1 && result.stderr.includes("--finding-categories"), result.stderr || result.stdout.slice(0, 120));
    }
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
