# promptlibrary-kit

A project-local prompt library for Claude Code. Keep reusable prompts in a validated catalog, verify and
optimize each one before it can be used, look them up read-only, and run one or more verified prompts in
Claude after a full-text preview and one approval. It exists to stop two habits: turning every repeatable
instruction into a new skill, and pasting unoptimized, unverified prompts into sessions.

## Installation

Requires [`uv`](https://docs.astral.sh/uv/) on your `PATH`: the skills run their validator through it.

```text
/plugin marketplace add AndreHahm/andres-cc-marketplace
/plugin install promptlibrary-kit@andres-cc-marketplace
```

To try it from a local checkout instead:

```bash
claude --plugin-dir /path/to/andres-cc-marketplace/plugins/promptlibrary-kit
```

## Usage

The first time you add a prompt, the skill offers to create the catalog in your project.

- **Save a prompt:** type `/prompt-library add` yourself (a plain request such as "save this as a
  prompt" does not start it, because only you may start a skill that writes to the catalog), then paste the text, point it at turns from the current
  session, or give it a URL. It screens the text for secrets, asks whether the content should be a skill
  instead, files a draft, has `prompt-reviewer` review it, and asks you to approve the exact final text
  before activating it. `/prompt-library revise <slug>` creates a new version without touching the active
  one until you approve it. `/prompt-library discard <slug>` removes a draft you no longer want, after
  showing it; a discarded first draft's slug is never reused. A prompt edited outside the plugin stops
  running on its own, with the reason, while the others keep working: restore it from git, or
  `/prompt-library retire <slug>` ends it for good and keeps its history.
- **Look one up:** ask "show my stored prompt for code review". `prompt-retrieval` only displays prompts;
  it never runs them. A search also finds a phrase inside a prompt's text.
- **Run one or more:** run `/prompt-execution review__missing-tests`. It shows the full text of every
  selected prompt, asks once to approve that exact set and order, then runs them in this session.

## Components

| Component | Type | What it does |
|---|---|---|
| `prompt-retrieval` | Skill | Read-only: find and show a stored prompt or its history |
| `prompt-execution` | Skill | User-invoked: preview, approve once, then run verified prompts in order |
| `prompt-library` | Skill | User-invoked: add (from a session, the web or typed text), review, revise, activate, deactivate, retire, discard a draft |
| `prompt-reviewer` | Agent | Read-only quality review, import review and optimization proposals |

## Language

**Python** (standard library only). The shared validator `scripts/plib_catalog_validate.py` owns catalog
root resolution, validation, hashing, secret screening and lifecycle moves; its fixture tests are
`scripts/plib_test_catalog_validate.py`. Each skill also has a smoke test at
`skills/<skill>/scripts/smoke_test.py`, sharing the helper `scripts/plib_smoke_common.py`. New scripts
added to this plugin stay in Python.

## Catalog

The catalog lives in the project that uses the plugin, not in the plugin (default `.claude/prompts/`):

```text
.claude/prompts/
  catalog.yaml
  <area>__<name>/
    active.md
    <internal_id>.md
```

Prompts are verified by a fingerprint: in a `catalog_version` 3 catalog (what `init` creates) a SHA-256
over the LF-normalized text, the `origin` and every attached file's path and content; in an older catalog
the text alone (`upgrade` moves it to version 3). Execution refuses a prompt whose fingerprint no longer
matches, and only that prompt. A matching fingerprint means "unchanged since it was recorded", not
"reviewed": the user's approval of the exact text and attachments, and the full preview before every run,
are what make it a review. Prompt text and attached files are data everywhere except an explicitly approved
run.

## Safety design

- `prompt-retrieval` and `prompt-execution` pre-approve only the validator's `validate` and `show`
  commands; anything else they might attempt still needs a normal permission prompt. Only `prompt-library`
  pre-approves commands that change the catalog, and only through the validator. Those commands run
  without a permission prompt, so the user-approval steps before a draft, a verification or a status
  change are enforced by the skill's instructions, not by the tool layer: the validator checks hashes
  and record validity but cannot see whether the user was asked. A concurrent writer with the same
  user's access to the catalog folder is outside this design, which defends against content a
  repository or a web page supplies.
- `origin` is a claim recorded at intake, not an attestation. In a version 3 catalog it is part of the
  fingerprint, so a hand-edited `origin` blocks its prompt (restore or retire). In an older catalog a
  hand-edited `origin` still skips the import screen and the import hash.
- Attached files (`attachments`, version 3 only) are project files that load with the prompt. Each must be
  a project-relative path written with `/`, inside the project, never through a link, junction, hard link
  or short name, never in `.git`, `.github`, Claude Code's or Codex's configuration folders, a file directly
  in `.claude` (such as `settings.json`), a `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.override.md`, `GEMINI.md` or `.mcp.json` in any folder, the catalog
  itself or a `.env` file, and UTF-8 text; together at most `attachment_max_kb`. The validator reads each
  one once, checks that the opened file is the one checked, and returns that content: the preview, the run
  and the reviewer all get exactly the fingerprinted content. A changed attachment blocks only its prompt;
  it can be reviewed again as a new version with the same text and origin.
- `prompt-reviewer` has no tools (`tools: []`, checked against Claude Code 2.1.322: it launched and could
  not read a file). It reviews the `review-bundle` output passed inline, so a record cannot point it at
  another file. Claude Code's own agent listing shows such an agent as having all tools; that listing is
  wrong for this case.
- The validator blocks secrets in `session`, `web`, `claude` and `codex` text itself (detect and block,
  never rewrite, never echoed), not just in the skill's step order. `user` text is only warned.
- `record-verification`, `activate` and `finalize` take `--expect-sha256`, the fingerprint the user was
  shown, and refuse if the text changed, and from catalog version 3 on also the origin or an attachment
  (an older catalog's fingerprint is the text hash); `retire` and `discard-draft` take the
  text hash, so they still work when an attachment cannot be read. `discard-draft` deletes only a draft; like
  `discard-orphan`, it has no backing hook, so the validator's own checks are its guard (owner decision
  2026-11-24).
- `hash`, `screen`, `draft` and `update-draft` read their input file only from inside the catalog root
  or the system temp directory (where the session scratchpad usually lives). The temp directory is
  shared with other local processes, so any file in it is readable this way; the user still sees the
  draft's text, origin and hash before anything is filed.
- Every call uses `uv run --isolated --no-project --no-config python`, so a project's own `pyproject.toml`,
  `uv.toml` and `.venv` are not used. Checked against uv 0.9.5: plain `--no-project` was not reliably safe
  (it picked up a repository `.venv` once), and the isolated form always ran in an ephemeral environment.
  The validator itself runs as `python -I` (Python's isolated mode; checked 2026-11-26 that the flag reaches
  the interpreter through `uv run`), so `PYTHONPATH` and other `PYTHON*` variables, the user site folder and
  the script's own folder cannot put a module such as `sitecustomize` in front of it. A `sitecustomize` or
  `.pth` file in the interpreter's own installation still loads.
- `git` is looked up outside the working directory. The catalog root must resolve inside the project
  root and never at, under or below (at any depth) `.git`, `.github` or Claude Code's configuration
  folders under `.claude/` (rules, commands, agents, skills, hooks and similar; the full list is
  `FORBIDDEN_ROOTS` in the validator), so stored prompt text is never loaded as project instructions.
  The name is checked as written as well as after links are resolved, and a path part that ends in a
  dot or space or contains a colon is refused.
- Outside a git repository the working directory is the project root, and the local override is ignored
  with a warning, because there is no way to check whether git tracks it. The override is also ignored
  when git tracks it, when it is reached through a link, or when git fails with anything other than
  "not tracked".
- Records and `catalog.yaml` are written through a randomly named temp file that then replaces the
  target, and a status move that fails partway is rolled back, as are earlier moves of the same command
  if a later move or the `catalog.yaml` write fails, so an interrupted write does not truncate a
  record or leave the catalog out of step with the files. If a rollback step itself fails, the rollback
  stops and `validate` reports the mismatch. Rewritten files keep their file mode (a new file gets the
  umask default), and `validate` warns about temp files a killed write left behind. An `internal_id` cannot be one of the layout's own
  names (`active`, `catalog`), a name an agent may load as instructions (`claude`, `agents`, `gemini`)
  or a Windows device name.

## Configuration

Two settings: the catalog root path and the attachment size limit.

- `promptlibrary-kit.settings.json` (plugin root, git-tracked defaults):
  `{"catalog_root": ".claude/prompts", "attachment_max_kb": 32}`.
- `.claude/promptlibrary-kit.local.json` (optional, untracked, per project): overrides either. The
  `catalog_root` override is honored only when git does not track the file, and the path must resolve
  inside the project root. `attachment_max_kb` is the total for all of one prompt's attachments, `16`, `32`
  or `64`; any other value is ignored with a warning. A copy git tracks, or one outside a git repository,
  may only lower it. A copy reached through a link is ignored entirely.
- This repository keeps a hand-maintained twin of the defaults at `.claude/promptlibrary-kit.settings.json`
  for its own dogfooding. The plugin-root file is canonical; no tooling checks the pair, so copy a change
  to the twin in the same commit and diff them.

The project root is `git rev-parse --show-toplevel`, else the working directory.

## Not included (planned later)

Notion-backed authority and sync, cross-repository (general) prompts, and Codex execution. The catalog
format keeps them additive: `catalog_version` and `scope` fields and an executor named in every approval.
Since version 3 the fingerprint also covers origin and attached files, so a prompt moved to another
project keeps its verification only where its attached files are identical.

## Known limitations

- Attachment checks fail closed: a file with more than one name (a hard link, as some package stores
  create), a path under a network drive, a Windows folder mount (no drive letter), a non-ASCII name that macOS
  stores in another Unicode form, or a platform where the opened file's path cannot be asked for (other
  than Windows, Linux and macOS) is refused. A parent folder swapped for a link to a network share during
  the read still opens that connection before the check refuses the file (review 2026-11-26, accepted).
  On Linux and macOS a mount the user creates inside the project (a bind or network mount) is not a link,
  so a file under it is read like any other project file (PR #914 review, accepted).
- `prerequisites`, `boundaries`, `references` and `name` are not part of the fingerprint: they are shown,
  never run, and can change without blocking a prompt.
- The validator tests run on Windows locally and on Linux (Ubuntu) in the repository's CI, which also runs
  the three file-mode tests that Windows skips. macOS behavior is designed for but unverified.
- Live runs on 2026-10-14 loaded the plugin with `--plugin-dir`, not from a marketplace install. A headless
  pass ran `prompt-retrieval` and the `prompt-reviewer` agent; `prompt-execution` refused at its approval
  question, which a headless session cannot ask. An interactive pass then ran `prompt-execution` (Cancel, and
  one approved run) and `prompt-library`'s add, revise, finalize and deactivate flows. Persisted behavioral
  evals exist under `evals/` (dry-run agents following each skill by hand), but none has been run live.
- In this repository the skills are also mirrored into `.claude/` as project-level skills. A project-level
  skill cannot resolve the plugin-root variable its validator path uses, so those mirror copies' validator
  calls are untested; the plugin installed normally is not affected.
- Importing a session by ID works only when `session-kit` is installed, and relies on its
  `session-detail` skill being listed under that name; pasting the turns always works.
- `prompt-reviewer`'s trigger check has not run: the repository's trigger-test script crashed on this and
  on known-good agents in the environment used. Its behavior (secrets cited by line only, hostile text
  not followed, origin mismatch, a clean record) is covered by dry-run evals in `evals/prompt-reviewer/`.

## Tests

```bash
cd plugins/promptlibrary-kit
uv run --isolated --no-project --no-config python -I scripts/plib_test_catalog_validate.py
```

Each skill's smoke test checks that its tool grants stay within what its body uses, that the files it
references exist, and runs the validator end to end against a throwaway git repository in the system
temp directory. Each exits 0 when every check passes, and was shown to fail on a deliberately broken
copy:

```bash
uv run --isolated --no-project --no-config python -I skills/prompt-retrieval/scripts/smoke_test.py
uv run --isolated --no-project --no-config python -I skills/prompt-execution/scripts/smoke_test.py
uv run --isolated --no-project --no-config python -I skills/prompt-library/scripts/smoke_test.py
```

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
