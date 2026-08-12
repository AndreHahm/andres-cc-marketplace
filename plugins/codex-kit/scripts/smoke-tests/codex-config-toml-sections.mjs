#!/usr/bin/env node
// Smoke test: scripts/lib/codex-config.mjs's section-aware TOML read/write
//
// Confirms the fix for a real data-corruption risk: a bare regex with no
// [table]-header awareness would match (and, on write, silently overwrite)
// a same-named key inside e.g. [profiles.work] as if it were the global
// root-level default. This test exercises the pure text-transform
// functions (extractTopLevelKey/setOrInsertTopLevelKey) directly against
// in-memory strings only -- it never touches a real ~/.codex/config.toml.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-config-toml-sections.mjs

import { extractTopLevelKey, setOrInsertTopLevelKey } from "../lib/codex-config.mjs";

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

const sectioned = [
  'model_reasoning_effort = "medium"',
  "",
  "[profiles.work]",
  'model = "gpt-5-work-profile"',
  "",
  "[profiles.personal]",
  'model = "gpt-5-personal"',
  ""
].join("\n");

console.log("=== extractTopLevelKey: a root-absent key must not read a same-named key from inside a table ===");
{
  const model = extractTopLevelKey(sectioned, "model");
  check("no root-level 'model' key -> undefined, never the [profiles.work] value", model === undefined, `got ${JSON.stringify(model)}`);

  const effort = extractTopLevelKey(sectioned, "model_reasoning_effort");
  check("a genuine root-level key is still read correctly", effort === "medium", `got ${JSON.stringify(effort)}`);
}

console.log("\n=== setOrInsertTopLevelKey: inserting a new root key must not corrupt any table ===");
{
  const written = setOrInsertTopLevelKey(sectioned, "model", "gpt-5-new-default");
  const rootRegion = written.split("[profiles.work]")[0];
  check(
    "the new root-level 'model' key lands before the first section header, not inside/after it",
    /^model = "gpt-5-new-default"$/m.test(rootRegion),
    written
  );
  check(
    "[profiles.work]'s own model line is byte-identical to the input -- not overwritten",
    written.includes('[profiles.work]\nmodel = "gpt-5-work-profile"'),
    written
  );
  check(
    "[profiles.personal]'s own model line is also untouched",
    written.includes('[profiles.personal]\nmodel = "gpt-5-personal"'),
    written
  );
}

console.log("\n=== setOrInsertTopLevelKey: replacing an existing root key still works (regression check) ===");
{
  const rootOnly = 'model = "old"\neffort = "low"\n';
  const replaced = setOrInsertTopLevelKey(rootOnly, "model", "new");
  check("existing root key value is replaced", replaced.includes('model = "new"') && !replaced.includes("old"), replaced);
}

console.log("\n=== A section-less file (no [table] at all) still round-trips correctly ===");
{
  const bare = "";
  const written = setOrInsertTopLevelKey(bare, "model", "first-value");
  check("inserting into an empty file produces a clean single line", written === 'model = "first-value"\n', JSON.stringify(written));
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
