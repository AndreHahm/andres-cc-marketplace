# Contributing

## Preferred Language

This plugin's preferred scripting language is **Python**: collectors, the dedup and plan-hash core,
the config loader and the report chunker are Python 3.11+ scripts with PEP 723 inline dependency
blocks (no third-party dependencies today). New scripts added to this plugin stay in Python rather
than mixing in JavaScript/TypeScript.

## Development Setup

Scripts live in `scripts/` and carry the `wlgr_` file prefix. Run them directly (`uv run <script>` or
`python <script>`); run the persisted tests with:

```bash
python scripts/wlgr_test_core.py
python scripts/wlgr_test_collect.py
python scripts/wlgr_test_pr_report.py
```

Each skill also has a structural smoke test at `skills/<skill>/scripts/smoke_test.py` (frontmatter, referenced files, Bash grants).

## Proposing a Change

1. Branch off `main` using this repository's `<type>/<description>` convention.
2. Make your change; keep the plugin read-only toward GitHub and never add a Linear or Notion
   connector call here. Every write goes through `workmanagement-kit`'s `plugin-integration-intake`.
3. If the change alters a skill's or script's actual behavior, test it (the scripts above, or the
   skill's own Testing & Validation section and its `references/test-scenarios.md`) before committing.
4. A change to the intake payloads, the open-item format or the config trust boundary needs a
   `security-reviewer` pass before it ships.
5. Run `plugin-rulebook` against any new or modified component before finalizing.
