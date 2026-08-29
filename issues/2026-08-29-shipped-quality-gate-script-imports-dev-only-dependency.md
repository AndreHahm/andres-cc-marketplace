## Summary
A mandatory quality-gate script shipped with a plugin (`smoke_test.py`) imported PyYAML, a dependency only present in the authoring repo's own dev environment — not installed when the plugin ships standalone into a downstream project, so the "mandatory" gate crashes with `ModuleNotFoundError` outside this repo.

## Environment
- **Product/Service**: `plugin-devkit` plugin — `rule-development`'s `scripts/smoke_test.py`
- **Region/Version**: this repo, found during PR #164 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Install the `plugin-devkit` marketplace plugin into an ordinary project (not this marketplace repo itself), with no PyYAML installed.
2. Run the mandatory quality gate: `python ${CLAUDE_SKILL_DIR}/scripts/smoke_test.py`.
3. The script's `import yaml` fails immediately with `ModuleNotFoundError: No module named 'yaml'`, since PyYAML is only declared under this repo's own `[dependency-groups].dev` in `pyproject.toml` (`dependencies = []`), not shipped with the plugin.

## Expected Behavior
A script shipped as part of an installable plugin should not import a dependency that's only present in the authoring repo's own dev/test environment — a mandatory quality-gate script needs to work using only the standard library (or dependencies genuinely bundled with the plugin) when run from an arbitrary downstream installation.

## Actual Behavior
The mandatory gate was unusable outside this repo's own dev environment. Verified this was the only `smoke_test.py` of roughly 48 across the whole repo with this import.

## Impact
[Severity: Medium] A "mandatory" check that can't run at all in the actual deployment environment (a downstream project with the plugin installed) defeats its own purpose. Fixed in `plugin-devkit`'s PR #164 (commit `c617f90`): replaced YAML parsing with a dependency-free bracket-balance check (`[`/`]` and `{`/`}` counts), live-tested against the exact malformed-frontmatter case (an unclosed `[` after `allowed-tools:`) the original fix was addressing — still correctly caught, smoke test re-run 4/4 pass.

## Additional Context
Mined from PR #164's own review history (`chatgpt-codex-connector[bot]`; 11 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #164` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This connects to `.claude/rules/require-declared-plugin-language.md`'s theme (a plugin should stay internally consistent about its toolchain) with a distinct, more specific instance: a dependency scoped to the *authoring repo's* dev environment leaking into a script the plugin ships to its own downstream installs.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/164#discussion_r3880870477
