# R33 check: plugin-devkit

**Gating:** plugin-devkit has status `active` and a registered `prefix` (`pdk`) and `domain_prefix` (`plugindevkit`). It is in scope, and the `null` opt-out does not apply. Every file under root `scripts/`, at any depth, is checked by **basename**. A basename must start with `pdk-` or `plugindevkit-`. A `.py` file may instead use full snake_case, `pdk_` or `plugindevkit_`, with no hyphen anywhere in the name.

| File | Verdict | Reason |
|---|---|---|
| `scripts/pdk-lib.sh` | PASS | The basename starts with `pdk-`, which is the registered prefix in kebab-case. |
| `scripts/helper-utils.sh` | FLAGGED (REQUIRED) | The basename starts with neither `pdk-` nor `plugindevkit-`. It is not a `.py` file, so the snake_case alternative does not apply. Fix: rename to `pdk-helper-utils.sh` or `plugindevkit-helper-utils.sh`. Then update every reference (SKILL.md bodies, hooks.json commands, script invocations, docs, the `.claude/` mirror). |
| `scripts/inventory_common/pdk_models.py` | PASS | The file is `.py` and uses snake_case throughout. It starts with `pdk_` and has no hyphen. The nested directory does not matter, because only the basename is checked. |
| `scripts/inventory_common/__init__.py` | EXEMPT | It is a Python package's `__init__.py` (exact basename) under the root-level `scripts/` directory. That filename is language-mandated. The exemption covers only this basename. The package's other modules, such as `pdk_models.py`, stay in scope. |

**Summary:** 1 flagged (`helper-utils.sh`), 2 pass, 1 exempt. The overall R33 verdict is FAIL, because R33 is a REQUIRED rule.

Source: `plugin-rulebook/SKILL.md` (R33) and `references/component-file-prefix.md`.
