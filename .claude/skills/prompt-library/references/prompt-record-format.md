# Prompt Record Format

Pattern: one markdown file per record, YAML frontmatter plus the prompt text as the body. This file is the
single home of the record model; the validator (`scripts/plib_catalog_validate.py`) is the authority that
enforces it, so when the two disagree the validator wins and this file is the one to fix.

## Fields (catalog_version 1, 2 and 3)

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
| `references` | no | List of text; carries any license or attribution note for imported text |
| `attachments` | no | List of project files loaded with the prompt; version 3 only (stored but never loaded before). Rules below |
| `verification` | conditional | Required for `active` and `inactive`: `quality`, plus `import` for `session`/`web`, plus `core` in version 3; no other keys; each a 64-character lowercase hex SHA-256: `quality` and `import` equal the current fingerprint, `core` the hash of text and origin alone |
| `prompt_text` | yes | The markdown body; at most 50 nonblank lines |

Unknown fields are rejected. Frontmatter uses a small YAML subset: scalars, one-level maps of scalars, and
lists of scalars. A bare value that looks like a number, `true`/`false`, `null`/`~` or `[]` is read as that
type (so `name: 2024` fails "name must be text"): quote such values. Do not write frontmatter by hand when
a validator command exists; `draft` and `update-draft` read a record you built and the validator rewrites
it in its canonical form. The template in `assets/` is a minimal record. Its `slug`, `internal_id` and `origin` placeholders are
deliberately invalid, so an unedited copy cannot be filed, but a leftover `name`, `area` or body passes
validation; replace every `REPLACE` value and the body, and extend it with `source_ref` for `session`/`web`
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

## Attachments (catalog_version 3)

Each entry is a path relative to the project root, written with `/`: no leading `/`, drive letter,
backslash, empty, `.` or `..` part, no character Windows refuses or part ending in a dot or space, and no
Windows device name. It must resolve inside the project, never through a link, junction or hard link, and
never at or under `.git`, `.github`, a Claude Code or Codex configuration folder (`FORBIDDEN_ROOTS`), the
catalog root, or a file named `.env` or `.env.*`. The file must be UTF-8 text without NUL characters, and
all of one prompt's attachments together must fit `attachment_max_kb` (16, 32 or 64 KB, default 32). A
draft that breaks a rule is refused with the reason before anything is filed. Order matters: it is the
order they are shown and loaded in, and it is part of the fingerprint.

## Hash definition

The text hash is the SHA-256 of the prompt text after normalizing line endings to LF and dropping leading
and trailing newline characters (a line holding only spaces or tabs is kept and hashed). A Windows and a
Linux checkout therefore agree, and any edit to the text makes an earlier hash stop matching.
`... hash <file>` prints it.

The fingerprint that `verification.quality` (and `import`) holds is the text hash in version 1 and 2. In
version 3 it is a SHA-256 over a tagged JSON object binding `core` (the hash of the text hash and the
`origin`) and the list of attachments, each as its path and the text hash of its content. So an edited
text, a relabelled origin, an edited, added, removed or reordered attachment, or one that is missing,
unreadable or over the limit, all change it; line endings alone never do. `validate`, `show`, `draft` and
`update-draft` report it as `fingerprint`.

An `active` or `inactive` record whose fingerprint no longer matches is blocked on its own: `validate`
lists it under `blocked` and stays `ok` while the other prompts work. When `core` still matches, only an
attachment changed (`attachment_change: true`): the prompt can be revised into a successor with the same
text and origin that takes the new attachment content, and the validator refuses a successor that changes
the text or origin. Otherwise every change to that prompt except `retire` is refused.

A recorded fingerprint means "unchanged since it was recorded". It does not prove the content was
reviewed: a change that rewrites both the content and the fingerprint would still match. Review is the
user's approval of the exact text and attachments, collected before the fingerprint is recorded and again
in the preview before every run.

## Slug and path rules

`name` and `area` never build a path. A slug is reserved when its first record is created and never reused
by another lineage; renaming creates a new lineage with a new slug. The validator enforces slug format
and refuses a second lineage while the slug is in the catalog or in `reserved_slugs`, where
`discard-draft` puts the slug of a discarded version 1 draft; it cannot know about a slug retired
outside the catalog, so never reusing one is a policy the people running the library keep.

```text
<catalog-root>/
  catalog.yaml            # catalog_version, scope, snapshot_id, records (listed paths),
                          # and in version 2 reserved_slugs (at least one)
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
draft (never active) --discard--> removed; a version 1 draft's slug stays reserved
finalize successor --> successor active or inactive; predecessor historical
prompt changed since its approval --retire--> historical (never runs again; slug stays taken)
```

A draft, initial or successor, can be edited in place (`update-draft`) until it is activated or finalized.
At most one record per slug is
`active`. A historical record never becomes active again; create a successor instead. All changes need the
user's approval.

## Extension seams

`catalog.yaml` carries `catalog_version` and `scope` (only `repo`). `init` creates version 3. Version 1 is
the original format; a version 1 catalog moves to 2 when a slug is reserved; version 3 binds origin and
attachments into the fingerprint and accepts `reserved_slugs` as optional. An older plugin version refuses
a newer catalog. `upgrade` moves a version 1 or 2 catalog to 3: it lists each approved prompt with its
origin and a `listing_id`, and `upgrade --expect-listing <listing_id>` rebinds every approved record whose
text still matches; it refuses while a prompt is blocked or any record lists attachments. The validator
selects its field list by `catalog_version`, so an added optional field is an additive change with a
version bump, and older catalogs stay valid. A record keeps its verification if it moves to another
catalog only where its attached files are identical there.
