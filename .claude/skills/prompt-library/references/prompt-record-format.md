# Prompt Record Format

Pattern: one markdown file per record, YAML frontmatter plus the prompt text as the body. This file is the
single home of the record model; the validator (`scripts/plib_catalog_validate.py`) is the authority that
enforces it, so when the two disagree the validator wins and this file is the one to fix.

## Fields (catalog_version 1)

| Field | Required | Rule |
|---|---|---|
| `name` | yes | Human-readable display name |
| `area` | yes | Human-readable category |
| `slug` | yes | Immutable lineage key `<kebab-area>__<kebab-name>`, each side `[a-z0-9]+(-[a-z0-9]+)*` |
| `internal_id` | yes | Immutable unique ID, lowercase kebab, at most 64 characters (get one from `new-id`) |
| `version` | yes | Positive integer within one slug; contiguous from 1 |
| `short_description` | yes | At most three sentences |
| `status` | yes | `draft`, `active`, `inactive`, `historical` |
| `previous_id` | conditional | Required when `version` > 1; forbidden at version 1 |
| `origin` | yes | `user`, `claude`, `codex`, `session`, `web` |
| `source_ref` | conditional | Required exactly for `session` (`session_id`, `turns`) and `web` (`url`, `retrieved_on`); no other keys, and not allowed for other origins. `turns` is one text value such as `3-5, 8`, not a list |
| `prerequisites`, `boundaries` | no | Text |
| `references`, `attachments` | no | Lists of text; `references` carries any license or attribution note for imported text |
| `verification` | conditional | Required for `active` and `inactive`: `quality`, plus `import` for `session`/`web`; no other keys; each a 64-character lowercase hex SHA-256 that equals the current text's hash |
| `prompt_text` | yes | The markdown body; at most 50 nonblank lines |

Unknown fields are rejected. Frontmatter uses a small YAML subset: scalars, one-level maps of scalars, and
lists of scalars. A bare value that looks like a number, `true`/`false`, `null`/`~` or `[]` is read as that
type (so `name: 2024` fails "name must be text"): quote such values. Do not write frontmatter by hand when
a validator command exists; `draft` and `update-draft` read a record you built and the validator rewrites
it in its canonical form. The template in `assets/` is a minimal record whose `REPLACE` placeholders are deliberately invalid, so an
unedited copy cannot be filed; replace every one, and extend it with `source_ref` for `session`/`web`
origin and with `previous_id` for a successor. These cannot be an `internal_id`: `active` and `catalog`
(the layout's own file names), `claude`, `agents` and `gemini` (file names an agent may load as
instructions) and the Windows device names (`con`, `prn`, `aux`, `nul`, `com0` to `com9`, `lpt0` to
`lpt9`). The validator's `RESERVED_IDS` is the authority if this list ever differs.

## Example frontmatter for an imported record

The required fields:

```yaml
name: Missing tests review
area: review
slug: review__missing-tests
internal_id: p1a2b3c4d5e6
version: 1
short_description: Find changes that lack tests.
status: draft
origin: web
```

A `web` record adds these to the same frontmatter:

```yaml
source_ref:
  url: https://example.com/prompts/review
  retrieved_on: 2026-10-03
references:
  - "License: CC0, from the page above"
```

For `session` origin use `session_id` and `turns` (one text value such as `3-5, 8`) under `source_ref`.

## Hash definition

`verification.quality` (and `import`) is the SHA-256 of the prompt text after normalizing line endings to
LF and dropping leading and trailing newline characters (a line holding only spaces or tabs is kept and
hashed). A Windows and a Linux checkout therefore agree, and any edit to the text makes an earlier hash
stop matching. `... hash <file>` prints it.

A recorded hash means "unchanged since the hash was recorded". It does not prove the text was reviewed: a
change that rewrites both the text and the hash would still match. Review is the user's approval of the
exact text, collected before the hash is recorded and again in the preview before every run.

## Slug and path rules

`name` and `area` never build a path. A slug is reserved when its first record is created and never reused
by another lineage; renaming creates a new lineage with a new slug. The validator enforces slug format
and refuses a second lineage while the slug is in the catalog; it cannot know about a slug retired
outside the catalog, so never reusing one is a policy the people running the library keep.

```text
<catalog-root>/
  catalog.yaml            # catalog_version, scope, snapshot_id, records (listed paths)
  <slug>/
    active.md             # the active record only
    <internal_id>.md      # draft, inactive and historical records
```

`catalog.yaml` lists every record path. A listed path that is missing, or a record file on disk that is
not listed, makes the catalog invalid. Management writes `catalog.yaml` last, after every record move.

## Lifecycle

```text
initial draft --verify (+import review)--> activate --> active <--> inactive
active or inactive --revise--> draft successor (unverified)
finalize successor --> successor active or inactive; predecessor historical
```

A draft, initial or successor, can be edited in place (`update-draft`) until it is activated or finalized.
At most one record per slug is
`active`. A historical record never becomes active again; create a successor instead. All changes need the
user's approval.

## Extension seams

`catalog.yaml` carries `catalog_version` (only `1`) and `scope` (only `repo`). The validator selects its
field list by `catalog_version`, so an added optional field is an additive change with a version bump, and
older catalogs stay valid. Verification hashes cover prompt text only, so a record keeps its verification
if it moves to another catalog.
