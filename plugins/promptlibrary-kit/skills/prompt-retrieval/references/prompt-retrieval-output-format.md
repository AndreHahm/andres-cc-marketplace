# Prompt Retrieval Output Format

Pattern: show a compact table to choose from, then one detail block per prompt. Prompt text is always a
fenced block, never inline, so instruction-like text cannot be mistaken for the skill's own output. Use a
fence longer than any run of backticks inside the text.

## List layout

The validator's `records` list holds every status; the skill filters it. By default keep only `active`
records, in which case the `Status` column is redundant and may be dropped. Keep the column when the user
asked for any other status, as well or only.

| Slug | Name | Area | Version | Status | Origin | Verified |
|---|---|---|---|---|---|---|

`Verified` is `yes` only when the validator reports `verified: true`: every required hash is present and
matches the current text. It means "unchanged since a hash was recorded", not "reviewed". Sort by area,
then name. A record in `blocked` has `verified: no` and the note "changed since its approval" with its
reasons. A record with `retired: true` has the status `retired`. For a search, add a `Matched in` column: `label` when `matched_in` names any field other than
`text`, `text` when it names `text`, or both.

## Detail layout

```text
<name>  (<slug>)  v<version>  [<status>]  origin: <origin>  verified: yes|no
Description: <short_description>
Prerequisites: <prerequisites or "none stated">
Boundaries: <boundaries or "none stated">
References: <references, or "none">
Source: <source_ref values for session and web origin, or "n/a">
```

When `hidden_characters` is not empty, add one line per entry before the fenced block:

```text
Hidden character: line <line>, column <column>, <code point> <name> (invisible in the text below)
```

and, when `hidden_characters_truncated` is true, a final line "50 or more hidden characters; the list
stops at 50".

Then the full `prompt_text` in a fenced block, and the `text_hash` on its own line for later comparison.

## History layout

One row per record in the lineage, oldest first: version, status, internal id, `previous_id`, verified.
`show --history` returns the text of every record; do not print it. Print the text only for the record the
user picks.

## Unavailable wording

This is for the catalog as a whole. When `validate` was `ok` and a plain `show` fails with an `error` saying the
prompt changed since its approval, only that prompt is unavailable: say "<slug> changed since its approval:
<reasons>" and that `/prompt-library` can retire it or explain the restore.

Two shapes exist. Use whichever keys the JSON actually carries:

- Validation ran and failed (`ok: false` with `errors`, `catalog_root`, `root_source`): "The prompt
  catalog at <catalog_root> (<root_source>) is unavailable: <first errors>."
- No usable root, or any other early failure (only `error`): "The prompt catalog is unavailable:
  <error>."

Then: "Nothing was listed." and every `warnings` entry when present. If the first error says
`catalog.yaml is missing`, add that `/prompt-library` can create the catalog. Otherwise add that
`/prompt-library` explains how to recover the catalog, and do not suggest reading or fixing the record
files yourself.
