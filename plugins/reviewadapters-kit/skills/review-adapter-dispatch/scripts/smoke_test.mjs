#!/usr/bin/env node
// Structural self-test for review-adapter-dispatch. Makes no network call and spawns no vendor CLI:
// the only process it starts is the dispatcher with no flags, which stops at the usage check.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = path.resolve(SKILL, "..", "..");
const SCRIPTS = ["rva-codex-kit.mjs", "rva-config.mjs", "rva-dispatch.mjs", "rva-prepare.mjs", "rva-run.mjs", "rva-vendors.mjs"];
const DISPATCH_GRANT = 'Bash(node "${CLAUDE_PLUGIN_ROOT}/scripts/rva-dispatch.mjs":*)';
const PREPARE_GRANT = 'Bash(node "${CLAUDE_PLUGIN_ROOT}/scripts/rva-prepare.mjs":*)';
// Step 1's plugin-root check, granted exactly (no wildcard): `pwd; pwd -P; (cd -- "<root>" && pwd -P)`.
const STEP1_GRANTS = ['Bash(pwd)', 'Bash(pwd -P)', 'Bash(cd -- "${CLAUDE_PLUGIN_ROOT}")'];

function frontmatter(text) {
  const match = /^---\n([\s\S]*?)\n---\n/.exec(text);
  return match ? match[1] : "";
}

function field(head, name) {
  const match = new RegExp(`^${name}:[ \\t]*(.*)$`, "m").exec(head);
  return match ? match[1].trim() : undefined;
}

function main() {
  const errors = [];
  try {
    const skill = fs.readFileSync(path.join(SKILL, "SKILL.md"), "utf8");
    const head = frontmatter(skill);
    if (field(head, "name") !== "review-adapter-dispatch") errors.push("SKILL.md: wrong name");
    if (field(head, "disable-model-invocation") !== "true") errors.push("SKILL.md: disable-model-invocation is not true");
    if (!(field(head, "allowed-tools") ?? "").includes(DISPATCH_GRANT)) errors.push("SKILL.md: dispatcher grant missing");
    const references = [...new Set(skill.match(/references\/[a-z0-9-]+\.md/g) ?? [])];
    if (references.length === 0) errors.push("SKILL.md: no references named");
    for (const relative of references) {
      if (!fs.statSync(path.join(SKILL, relative), { throwIfNoEntry: false })?.isFile()) errors.push(`missing ${relative}`);
    }
    for (const name of SCRIPTS) {
      if (!fs.statSync(path.join(ROOT, "scripts", name), { throwIfNoEntry: false })?.isFile()) errors.push(`missing scripts/${name}`);
    }

    const settings = JSON.parse(fs.readFileSync(path.join(ROOT, "reviewadapters-kit.settings.json"), "utf8"));
    if (settings.timeout_ms !== 600000) errors.push("settings: timeout_ms is not 600000");
    const vendors = Object.keys(settings.vendors ?? {}).sort((a, b) => a.localeCompare(b)).join(",");
    if (vendors !== "agy,devin,pi") errors.push(`settings: vendors are ${vendors}`);
    for (const [name, vendor] of Object.entries(settings.vendors ?? {})) {
      if (vendor.enabled !== false) errors.push(`settings: ${name} is not disabled`);
    }

    const command = fs.readFileSync(path.join(ROOT, "commands", "rva-review-diff.md"), "utf8");
    const grants = (field(frontmatter(command), "allowed-tools") ?? "").match(/Bash\([^)]*\)[^,]*/g) ?? [];
    const expected = [DISPATCH_GRANT, PREPARE_GRANT, ...STEP1_GRANTS];
    const unexpected = grants.map((grant) => grant.trim()).filter((grant) => !expected.includes(grant));
    if (grants.length !== expected.length || unexpected.length > 0) errors.push(`rva-review-diff.md: unexpected Bash grants ${JSON.stringify(unexpected)}`);

    const run = spawnSync(process.execPath, [path.join(ROOT, "scripts", "rva-dispatch.mjs")], { encoding: "utf8", timeout: 30000 });
    let output;
    try {
      output = JSON.parse(run.stdout);
    } catch {
      output = undefined;
    }
    if (run.status !== 1 || output?.ok !== false || output?.category !== "usage") {
      errors.push(`rva-dispatch.mjs with no flags: exit ${run.status}, stdout ${JSON.stringify(run.stdout.slice(0, 200))}`);
    }
  } catch (error) {
    errors.push(error.message);
  }
  console.log(errors.join("\n") || "ok");
  return errors.length ? 1 : 0;
}

process.exitCode = main();
