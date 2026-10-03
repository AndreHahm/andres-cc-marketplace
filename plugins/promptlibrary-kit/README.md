# promptlibrary-kit

A project-local prompt library for Claude Code. Keep reusable prompts in a validated catalog, verify and
optimize each one before it can be used, look them up read-only, and run one or more verified prompts in
Claude after a full-text preview and one approval. It exists to stop two habits: turning every repeatable
instruction into a new skill, and pasting unoptimized, unverified prompts into sessions.

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
`scripts/plib_test_catalog_validate.py`. New scripts added to this plugin stay in Python.

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

- `prompt-retrieval` and `prompt-execution` can run only the validator's `validate` and `show` commands.
  Only `prompt-library` can change the catalog, and only through the validator.
- The validator blocks secrets in `session`, `web` and `claude` text itself (detect and block, never
  rewrite, never echoed), not just in the skill's step order. `user` and `codex` text is only warned.
- Lifecycle commands take `--expect-sha256`, the hash the user was shown, and refuse if the text changed.
- Every call uses `uv run --isolated --no-project --no-config python`, so a project's own `pyproject.toml`,
  `uv.toml` and `.venv` are not used. Checked against uv 0.9.5: plain `--no-project` was not reliably safe
  (it picked up a repository `.venv` once), and the isolated form always ran in an ephemeral environment.
- `git` is looked up outside the working directory, and the catalog root must resolve inside the project
  root and never at or under `.git`, `.github` or Claude Code's `.claude/` rules, commands, agents, skills
  or hooks folders, so stored prompt text is never loaded as project instructions. Outside a git repository the working directory is the root and an untracked local override is
  honored without a tracking check, so only point that override at a path you control.

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

## Tests

```bash
python scripts/plib_test_catalog_validate.py
```
