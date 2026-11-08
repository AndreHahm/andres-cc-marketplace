## Summary
plugin-rulebook R24: add `properties` to `exempt_tags`

## Environment
- **Product/Service**: plugin-devkit, `plugin-rulebook` R24 (fence-language allowlist)
- **Region/Version**: `plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json` (canonical), mirrored at `.claude/skills/plugin-rulebook/assets/settings.json`

## Reproduction Steps
1. Add a fenced block tagged `properties` (for example a `.sonarcloud.properties` example) to a skill reference file.
2. Run a `plugin-rulebook` / `plugin-rulebook-checker` check, or CI's Codex delta review, on it.

## Expected Behavior
A Java `.properties` example is treated as a data-format block, like `ini`, `toml`, `yaml` or `json`, and passes R24.

## Actual Behavior
R24 flags the fence as Major: `properties` is not in `exempt_tags`. Seen in the local CI-parity Codex review of the quality-kit Sonar PR (branch `feature/quality-kit-sonar-mutation`), on `plugins/quality-kit/skills/using-sonarqube-cloud/references/project-setup.md`. Worked around by retagging the fence `ini`.

## Impact
**Low** - cosmetic; the `ini` tag is an acceptable workaround.

## Additional Context
Java `.properties` files (SonarQube, Spring, Gradle) are a common configuration format, so the tag is a legitimate data format rather than an unlisted programming language.

Proposed change:
- Add `"properties"` to `exempt_tags` in the canonical `settings.json` and re-sync the `.claude/` mirror.
- Run the R20 duplicate-fact sweep for any prose restatement of the list (today only the two `settings.json` files hold `exempt_tags`).
- Optionally retag the quality-kit `project-setup.md` fence back to `properties` afterwards.
