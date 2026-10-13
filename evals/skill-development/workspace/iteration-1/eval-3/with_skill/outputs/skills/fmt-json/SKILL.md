---
name: fmt-json
description: >-
  Pretty-print and format JSON files with jq. Use when asked to "format JSON", "pretty-print JSON",
  "prettify a JSON file", "indent this .json file", or to make minified JSON readable. Prints to
  stdout and does not modify the file unless the user asks.
allowed-tools: Bash(jq:*)
---

# Format JSON

Format a JSON file for readability with `jq .`.

## Instructions

1. Run `jq . <file>` and show the output. `jq .` prints to stdout and leaves the file untouched.
2. To change the file itself, only do so when the user asks: write to a temp file, then move it over the
   original. Do not redirect to the input file directly (`jq . f > f` truncates `f` before jq reads it).
3. If `jq` reports a parse error, report the line/column it gives and stop. Do not guess a repair.

## Gotchas

- Very large integers and some float forms can be altered by other jq builds (checked here: jq printed
  `100000000000000000001` and `1.0` unchanged, but older builds round to double precision). Tell the user
  if exact numeric fidelity matters.
- A multi-document file (several top-level values) prints each value in turn; that is expected.

## Testing & Validation

**Verify this skill activates on:** "format this JSON file", "pretty-print config.json", "prettify data.json".

**Verify it does NOT activate on:** "validate this JSON against a schema", "convert JSON to YAML".

**Quality gates:** `jq . sample.json` output is indented and the source file is byte-identical afterward.
