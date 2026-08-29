# import-grading with a component-mode report: what happens and why

## Setup

`marketplace-inventory` is a `plugin-devkit` skill whose CLI lives at
`plugins/plugin-devkit/skills/marketplace-inventory/scripts/marketplace-inventory.py`. One of its
subcommands is:

```
import-grading  <repo_root> <inventory_path> <report_path> <target> <target_type>
```

Its SKILL.md (`plugins/plugin-devkit/skills/marketplace-inventory/SKILL.md`, "Import Grading" section)
states:

> `target_type` is always `plugin` for this inventory's own records — the script itself rejects any
> other value outright, since a component-level report belongs in `plugin-inventory`'s own
> `import-grading` instead.

A component-mode `plugin-grader` report (`target_type: "skill"`) for the `marketplace-inventory` skill
inside `plugin-devkit` is exactly the case this line describes.

## Live reproduction

Built a synthetic component-mode report (`component-report.json`, alongside this file):

```json
{
  "target": "marketplace-inventory",
  "target_type": "skill",
  "final_score": 8.7,
  "graded_at": "2026-08-29T00:00:00Z",
  "grader_schema_version": 2,
  "dimensions": { "structure": 9.0, "safety_risk_handling": 8.5 }
}
```

Recorded the real repo's `.claude-plugin/marketplace-inventory.json` MD5 before the attempt
(`5d319242f290d49d910504fdbc35758d`), then ran:

```
python marketplace-inventory.py import-grading \
  C:/Dev/Repos/andres-cc-marketplace \
  C:/Dev/Repos/andres-cc-marketplace/.claude-plugin/marketplace-inventory.json \
  <scratch>/component-report.json \
  plugin-devkit \
  skill
```

Output:

```
marketplace-inventory only imports whole-plugin reports (target_type='plugin'); got target_type='skill' -- a component-level report belongs in plugin-inventory's own import-grading instead
EXIT CODE: 1
```

Re-checked the inventory file's MD5 afterward: unchanged (`5d319242f290d49d910504fdbc35758d`), and
`git status --porcelain` on that path reported nothing — zero side effects, confirmed against the real
file rather than a scratch copy.

## What happens, mechanically

In `cmd_import_grading` (marketplace-inventory.py, ~line 368):

```python
def cmd_import_grading(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.repo_root, INVENTORY_FILENAME
    )
    if args.target_type != "plugin":
        raise SystemExit(
            f"marketplace-inventory only imports whole-plugin reports (target_type='plugin'); "
            f"got target_type={args.target_type!r} -- a component-level report belongs in "
            f"plugin-inventory's own import-grading instead"
        )
```

The `target_type` check runs immediately after the scope-path check and **before** the report file or
the inventory file's contents are ever read/parsed (report/inventory JSON loading happens later, inside
`reconcile.cmd_import_grading_for_record`, which this code path never reaches). So the rejection is a
hard, fail-closed `SystemExit` with exit code 1 — no inventory mutation, no partial write, no
score/history change, regardless of whether the report file itself is well-formed.

## Why the skill's docs say this must be rejected, not imported

1. **Ownership split between the two inventories.** `marketplace-inventory` tracks one record per
   *plugin*; `plugin-inventory` tracks one record per *component* (skill/agent/command/hook) inside a
   single plugin. A `target_type: "skill"` report describes a component, which is `plugin-inventory`'s
   record type, not `marketplace-inventory`'s. Feeding it here would attach a component's score to the
   wrong granularity of record.

2. **Rollup fields are import-only and single-authority.** Per `references/reconciliation.md`'s "Rollup
   Fields Are Import-Only" section, a marketplace plugin record's `score`/`security_score` are populated
   *only* from a completed **whole-plugin** `plugin-grader` report's `plugin_final_score`/
   `plugin_security_score` fields — never derived or backed into from that plugin's own component-level
   scores. Doing so would duplicate `plugin-grader`'s own whole-plugin rollup math, which the docs call
   out as a violation of "plugin-grader is the sole quality- and security-scoring authority" (see
   `inventory_common/grading.py`'s module docstring). Accepting a `skill`-level report here is exactly
   the shortcut that guard exists to prevent.

3. **The two report shapes are structurally different, not just differently labeled.** A component-mode
   report carries `final_score`/`dimensions.safety_risk_handling`; a whole-plugin report carries
   `plugin_final_score`/`plugin_security_score`. Silently accepting the wrong `target_type` risks
   reading/misreading the wrong fields rather than failing cleanly — rejecting on `target_type` up front
   avoids that ambiguity entirely.

4. **Symmetric guard on the other side.** `plugin-inventory.py`'s own `cmd_import_grading` has the
   mirror-image check: it raises `SystemExit` if `args.target_type == "plugin"` ("a whole-plugin report
   belongs in marketplace-inventory's own inventory, not a single component's record"). The two scripts
   are deliberately partitioned so each only ever writes its own record granularity; a report headed for
   the wrong one is rejected on both ends rather than silently accepted by either.

The skill's own Quality Gates checklist states this directly: "`import-grading` always rejects a
`target_type` other than `plugin`" — and that a component-level report for `marketplace-inventory` (a
skill inside `plugin-devkit`) belongs instead in `plugin-inventory`'s own `import-grading`, using
`plugin-devkit`'s `plugin-inventory.json` and matching by `name` + `type` (`skill`) rather than by bare
plugin name.

## Files
- `component-report.json` — the synthetic component-mode (`target_type: "skill"`) report used in the
  live test.
- This file — the reproduction steps and analysis.
