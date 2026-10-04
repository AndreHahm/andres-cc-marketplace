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
  one until you approve it.
- **Look one up:** ask "show my stored prompt for code review". `prompt-retrieval` only displays prompts;
  it never runs them.
- **Run one or more:** run `/prompt-execution review__missing-tests`. It shows the full text of every
  selected prompt, asks once to approve that exact set and order, then runs them in this session.

## Components

| Component | Type | What it does |
|---|---|---|
| `prompt-retrieval` | Skill | Read-only: find and show a stored prompt or its history |
| `prompt-execution` | Skill | User-invoked: preview, approve once, then run verified prompts in order |
| `prompt-library` | Skill | User-invoked: add (from a session, the web or typed text), review, revise, activate, deactivate |
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

Prompts are verified by a SHA-256 of their LF-normalized text; execution refuses a prompt whose text no
longer matches. A matching hash means "unchanged since a hash was recorded", not "reviewed": the user's
approval of the exact text, and the full-text preview before every run, are what make it a review. Prompt
text is data everywhere except an explicitly approved run.

## Safety design

- `prompt-retrieval` and `prompt-execution` pre-approve only the validator's `validate` and `show`
  commands; anything else they might attempt still needs a normal permission prompt. Only `prompt-library`
  pre-approves commands that change the catalog, and only through the validator. Those commands run
  without a permission prompt, so the user-approval steps before a draft, a verification or a status
  change are enforced by the skill's instructions, not by the tool layer: the validator checks hashes
  and record validity but cannot see whether the user was asked. A concurrent writer with the same
  user's access to the catalog folder is outside this design, which defends against content a
  repository or a web page supplies.
- `origin` is a claim recorded at intake, not an attestation: a hand-edited `origin` skips the import
  screen and the import hash.
- The validator blocks secrets in `session`, `web`, `claude` and `codex` text itself (detect and block,
  never rewrite, never echoed), not just in the skill's step order. `user` text is only warned.
- `record-verification`, `activate` and `finalize` take `--expect-sha256`, the hash the user was shown,
  and refuse if the text changed.
- Every call uses `uv run --isolated --no-project --no-config python`, so a project's own `pyproject.toml`,
  `uv.toml` and `.venv` are not used. Checked against uv 0.9.5: plain `--no-project` was not reliably safe
  (it picked up a repository `.venv` once), and the isolated form always ran in an ephemeral environment.
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

One setting, the catalog root path.

- `promptlibrary-kit.settings.json` (plugin root, git-tracked defaults): `{"catalog_root": ".claude/prompts"}`.
- `.claude/promptlibrary-kit.local.json` (optional, untracked, per project): overrides `catalog_root`. It is
  honored only when git does not track it, and the path must resolve inside the project root.
- This repository keeps a hand-maintained twin of the defaults at `.claude/promptlibrary-kit.settings.json`
  for its own dogfooding. No tooling checks the pair, so edit both in the same commit and diff them.

The project root is `git rev-parse --show-toplevel`, else the working directory.

## Not included (planned later)

Notion-backed authority and sync, cross-repository (general) prompts, and Codex execution. The catalog
format keeps them additive: `catalog_version` and `scope` fields, an executor named in every approval, and
verification hashes that cover prompt text only.

## Known limitations

- The catalog-path tests have run on Windows only. Linux and macOS behavior is designed for but unverified,
  and the three file-mode tests are skipped on Windows, so they have not run at all yet.
- Skill flows were checked by following each `SKILL.md` by hand against throwaway catalogs, not by a live
  installed run. Persisted behavioral evals exist under `evals/` (dry-run agents following each skill by hand),
  but none has been run in a live installed session.
- In this repository the skills are also mirrored into `.claude/` as project-level skills. A project-level
  skill cannot resolve the plugin-root variable its validator path uses, so those mirror copies' validator
  calls are untested; the plugin installed normally is not affected.
- Importing a session by ID works only when `session-kit` is installed, and relies on its
  `session-detail` skill being listed under that name; pasting the turns always works.
- `prompt-reviewer`'s trigger check has not run: the repository's trigger-test script crashed on this and
  on known-good agents in the environment used.

## Tests

```bash
cd plugins/promptlibrary-kit
uv run --isolated --no-project --no-config python scripts/plib_test_catalog_validate.py
```

Each skill's smoke test checks that its tool grants stay within what its body uses, that the files it
references exist, and runs the validator end to end against a throwaway git repository in the system
temp directory. Each exits 0 when every check passes, and was shown to fail on a deliberately broken
copy:

```bash
uv run --isolated --no-project --no-config python skills/prompt-retrieval/scripts/smoke_test.py
uv run --isolated --no-project --no-config python skills/prompt-execution/scripts/smoke_test.py
uv run --isolated --no-project --no-config python skills/prompt-library/scripts/smoke_test.py
```

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
