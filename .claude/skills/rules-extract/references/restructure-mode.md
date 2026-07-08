# Restructure Mode — Complete Procedure

Steps executed when `/rules-extract --restructure` is invoked. Re-analyzes the codebase to determine the optimal file structure, then merges existing rule content into the new structure.

**Note**: Restructure Mode does NOT run the Step U3 staleness check — use `--update` first so stale symbols are flagged for manual review (see the Update Mode operational note for the post-major-version-bump workflow).

## Contents

- Step R1: Load Settings and Snapshot Existing Rules
- Step R2: Re-analyze Codebase
- Step R2.5: Resolve File References
- Step R3: Show Restructure Plan and Confirm
- Step R4: Merge and Write
- Step R4.5: Security Self-Check
- Step R5: Report Summary

## Step R1: Load Settings and Snapshot Existing Rules

1. Load settings (same as Step 1 in `references/full-extraction-mode.md`)
2. Check `output_dir` exists → Error if not: "Run /rules-extract first to initialize rule files."
3. Read and parse all existing rule files: `<output_dir>/**/<name>.md` and `<output_dir>/**/<name>.local.md` (rule files), plus `<examples_output_dir>/**/<name>.examples.md` (examples files). When `examples_output_dir` differs from `output_dir`, also scan `<output_dir>/**/<name>.examples.md` to pick up legacy co-located examples written by older runs; treat such legacy files as candidates to migrate during Step R4.

## Step R2: Re-analyze Codebase

Execute Steps 2–5 from `references/full-extraction-mode.md` to determine the ideal file structure.

## Step R2.5: Resolve File References

Skip this step if `resolve_references` is `false`. Default is `true`.

Scan existing rule content (loaded in R1) for file references (Markdown links, text references like "See `<path>`", `@path` references), resolve them, extract rules from referenced files, and merge into the R1 snapshot. Rules from references are treated as existing rules (take priority on conflict in R4). See `references/resolve-references.md` for detailed processing steps.

## Step R3: Show Restructure Plan and Confirm

Compare old and new file structures, display planned changes (Keep/New/Remove per file), and wait for user confirmation before proceeding. If references were resolved in R2.5, include the number of rules extracted from referenced files in the plan display so the user understands where additional rules came from.

## Step R4: Merge and Write

1. Fresh extraction results as base, route existing rules (including rules extracted from resolved references) to appropriate new files by category/scope/layer/integration
2. **Existing rules take priority** on conflict (respect manual edits, conversation-extracted rules, and reference-extracted rules)
3. Unmatched rules → `project.md` as fallback; preserve custom sections in the most relevant file
4. Apply `split_output` setting (handle hybrid ↔ split transitions), deduplicate
5. **Write new files first**, then remove old files no longer in the new structure
6. **Handle `.examples.md`**: Write `.examples.md` files to `<examples_output_dir>/<name>.examples.md`, following the same structure changes as rule files. When R1 picked up legacy `<output_dir>/<name>.examples.md` files (co-located with rule files from older runs), move them to the new location under `examples_output_dir` and remove the legacy copies after the new file is written. Generate new `.examples.md` for categories that didn't have one (see the pre-loaded `examples-format.md`).

## Step R4.5: Security Self-Check

Using the pre-loaded `security.md` patterns, run the security self-check on all generated files.

## Step R5: Report Summary

Report structural changes, content merge summary, unmatched rules, and reference resolution results. Per the pre-loaded `report-templates.md` § Restructure Mode for format.
