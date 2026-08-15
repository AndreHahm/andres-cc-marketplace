#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's findSchemaViolation
//
// Confirms union-type (`type: [...]`) support, added after a real CI
// regression: ENVELOPE_SCHEMA's `components` field was made nullable
// (`type: ["array", "null"]`) to satisfy OpenAI's strict structured-output
// mode, which requires every `properties` key to also appear in `required`
// -- "optional" has to be expressed as nullable, not omission. Before this
// fix, findSchemaViolation only matched a bare string `schema.type`, so a
// union-typed field silently skipped local validation instead of being
// checked against either listed type.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-schema-validation.mjs

import { findSchemaViolation } from "../lib/codex-exec.mjs";

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

const nullableArraySchema = { type: "object", additionalProperties: false, required: ["items"], properties: { items: { type: ["array", "null"], items: { type: "string" } } } };

console.log("=== Union type [\"array\", \"null\"]: null value passes ===");
{
  const violation = findSchemaViolation({ items: null }, nullableArraySchema);
  check("null matches a union type that lists \"null\"", violation === null, violation);
}

console.log("\n=== Union type [\"array\", \"null\"]: a valid array passes ===");
{
  const violation = findSchemaViolation({ items: ["a", "b"] }, nullableArraySchema);
  check("an array of strings matches the \"array\" branch", violation === null, violation);
}

console.log("\n=== Union type [\"array\", \"null\"]: a wrong-shaped array is still rejected ===");
{
  const violation = findSchemaViolation({ items: [1, 2] }, nullableArraySchema);
  check("an array of numbers fails the items:{type:string} check", violation !== null, JSON.stringify(violation));
}

console.log("\n=== Union type [\"array\", \"null\"]: a non-array, non-null value is rejected ===");
{
  const violation = findSchemaViolation({ items: "not an array" }, nullableArraySchema);
  check("a bare string matches neither \"array\" nor \"null\"", violation !== null, JSON.stringify(violation));
}

console.log("\n=== Pre-existing bare-string-type behavior is unchanged ===");
{
  const stringSchema = { type: "object", additionalProperties: false, required: ["name"], properties: { name: { type: "string" } } };
  const missing = findSchemaViolation({}, stringSchema);
  const wrongType = findSchemaViolation({ name: 42 }, stringSchema);
  const valid = findSchemaViolation({ name: "ok" }, stringSchema);
  check("missing required string property is still rejected", missing !== null, missing);
  check("wrong-typed string property is still rejected", wrongType !== null, wrongType);
  check("a valid string property still passes", valid === null, valid);
}

console.log("\n=== additionalProperties: false rejects an unrequested extra property ===");
{
  const stringSchema = { type: "object", additionalProperties: false, required: ["name"], properties: { name: { type: "string" } } };
  const extra = findSchemaViolation({ name: "ok", injected: "padding" }, stringSchema);
  const clean = findSchemaViolation({ name: "ok" }, stringSchema);
  check("an object with a key not in properties is rejected", extra !== null, extra);
  check("an object with only declared keys still passes", clean === null, clean);
}

console.log("\n=== additionalProperties unset (not false) still permits extra keys ===");
{
  const permissiveSchema = { type: "object", required: ["name"], properties: { name: { type: "string" } } };
  const violation = findSchemaViolation({ name: "ok", extra: "fine" }, permissiveSchema);
  check("no additionalProperties constraint means extra keys are not checked", violation === null, violation);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
