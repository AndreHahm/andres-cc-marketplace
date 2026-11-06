---
name: fmt-json
description: >-
  Pretty-prints and formats JSON files with jq. Use when asked to format, pretty-print, prettify or
  re-indent a JSON file.
allowed-tools: Bash(jq:*) Read
---

# Format JSON

Pretty-print a JSON file by running `jq .` on it.

## Instructions

1. Confirm the target path points at a JSON file. Read it only if the path is unclear.
2. Run `jq . <file>` and show the output. Write it back to the file only when the user asks for an in-place change (write to a temp file first, then replace, because `jq . f > f` truncates the input).
3. If `jq` reports a parse error, show the error (it includes line and column) and stop. Do not guess a repair.

## Gotchas

- `jq . file > file` empties the file before jq reads it; always go through a temp file.
- `jq .` preserves key order but re-indents with 2 spaces; use `--indent N` or `--tab` only if the user asks.
