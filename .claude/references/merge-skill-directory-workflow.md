# Merge Skill Directory — Workflow Steps

Detailed step-by-step instructions for `/merge-skill-directory`.

---

## Step 0 — Guard Checks

1. Verify `skill-a` and `skill-b` directories exist. If either is missing, stop and report.
2. Verify each directory contains a `SKILL.md`. If either is missing, stop and report.
3. Set `run_dir`:
   - If provided, use as-is.
   - If auto, read the `name` field from `skill-a/SKILL.md` frontmatter and derive: `.claude/output/merge-skill-<name>-<YYYY-MM-DD>/`.
4. If `run_dir` already exists and contains a `manifest.md`, apply auto-resume (Step 0.1).
5. If `dry_run=true`, run Steps 0.2–3 only and stop after the confirmation gate (or after Step 0.2 for SKILL.md-only B). Do not write to `output`.

### Step 0.1 — Auto-Resume Detection

If `run_dir` exists and `manifest.md` is present:

- Read the step completion table.
- For each step already marked `✅ complete`, skip automatically.
- Report all auto-skipped steps at the start.

### Step 0.2 — SKILL.md-Only B Fast-Path

After guard checks, scan `skill-b` for non-SKILL.md files (any file that is not `SKILL.md` at any depth).

If `skill-b` contains **only** `SKILL.md`:

- Set `b_skill_only=true`.
- Write a minimal `directory-manifest.md` to `run_dir` noting the fast-path:
  ```
  B contains only SKILL.md — Steps 1–3 skipped (no non-SKILL.md files to classify or copy).
  ```
- **Skip Steps 1, 2, and 3 entirely.** Jump to Step 4.

If `b_skill_only=false`, continue normally through Steps 1–3.

### Step 0.3 — Pre-Merge Orphan Scan

Scan A's current SKILL.md for references to files that do not yet exist on disk.

1. Read `<skill-a>/SKILL.md`.
2. Locate all file path references in the Reference Guide / Additional Resources table and any inline `${CLAUDE_SKILL_DIR}/` references.
3. For each path, check whether the file exists at `<skill-a>/<path>`.
4. Record any missing files as **pre-existing orphans** in `directory-manifest.md`:

```markdown
## Pre-Existing Orphans in A

| Reference | Status |
|---|---|
| `references/foo.md` | ⚠ missing before merge |
```

5. If no pre-existing orphans are found, record `Pre-existing orphans: 0` in `directory-manifest.md`.

Pre-existing orphans are not caused by this workflow. In Step 6, distinguish:

- **Pre-existing orphan** (in A's SKILL.md before the merge began — listed here): warn but do not block.
- **Merge-caused unresolved reference** (a path added to SKILL.md during the merge that was never copied): warn and flag for action.

---

## Step 1 — Directory Scan

Use `find_by_name` with `Pattern: *` and `Type: file` to enumerate all files in `skill-a` and `skill-b` recursively. **Do not use `list_dir`** — it silently drops files that exist on disk but are not tracked by git (local-only files). Exclude `SKILL.md` from the results (delegated to `/merge-pipeline` in Step 4).

For each file found, record:

| Column | Value |
|---|---|
| Relative path | Path relative to skill root (e.g., `references/auth-checklist.md`) |
| File type | `markdown`, `script`, `binary`, `other` |
| In A | `yes` / `no` |
| In B | `yes` / `no` |
| Dir conflict | `yes` if same logical purpose but different directory names (e.g., `references/` vs `reference/`) |

**File type classification:**

| Type | Extensions |
|---|---|
| `markdown` | `.md`, `.mdx` |
| `script` | `.py`, `.sh`, `.js`, `.ts`, `.rb`, `.ps1`, `.bash` |
| `binary` | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.ico`, `.pdf`, `.zip`, and any other non-text format |
| `other` | `.yaml`, `.yml`, `.json`, `.toml`, `.txt`, `.csv`, and all remaining text formats |

Write `directory-manifest.md` to `run_dir` as a draft. It will be finalized after Step 2.

---

## Step 2 — Classify Files

For each file in the directory manifest, assign a merge action:

| Condition | Action |
|---|---|
| Exists in A only | `copy-from-a` |
| Exists in B only — associated SKILL.md content is being integrated | `copy-from-b` |
| Exists in B only — associated SKILL.md content is **not** being integrated | `skip` (required: `reason` field) |
| Exists in both — identical content | `copy-any` (copy from A; no merge needed) |
| Exists in both — `markdown` — different content | `merge-md` |
| Exists in both — `script` — different content | `copy-both-with-suffix` + `⚠ manual review` |
| Exists in both — `binary` — different content | `copy-both-with-suffix` + `⚠ manual review` |
| Exists in both — `other` — different content | `copy-both-with-suffix` + `⚠ manual review` |
| Different names — `markdown` — ≥ 50 % heading overlap (cross-file scan) | `merge-md-cross` + user confirm |

#### `skip` Decision Rule

Use `skip` when a B-only file's associated SKILL.md content is explicitly **not** being integrated into the merged SKILL.md — for example, because the feature was out of scope, too niche, or contradicts the merge goal.

A `skip` entry requires a `reason` field in `directory-manifest.md`:

```
| `references/foo.md` | markdown | no | yes | — | `skip` | B's foo workflow not integrated — excluded from merge scope |
```

`skip` files are excluded from `copy-manifest.txt` and are not copied to output. They are preserved in B's backup (Step 7) but not referenced in the merged SKILL.md. This prevents the validate-frontmatter hook from flagging them as orphans.

### Directory Name Normalization

If A and B use different names for the same logical directory (e.g., `references/` vs `reference/`):

1. Determine the canonical name from the `reference_dir` parameter (default: `references`).
2. Remap all files from the non-canonical directory to the canonical path in the output.
3. Record the remapping in `directory-manifest.md`.
4. The SKILL.md reference table will be updated in Step 6 to reflect the new paths.

Example:
- A: `reference/sast-tools.md` → output: `references/sast-tools.md`
- B: `references/auth-checklist.md` → output: `references/auth-checklist.md` (unchanged)

### Cross-File Overlap Scan (Markdown Only)

Scan all `copy-from-a` and `copy-from-b` markdown files for cross-source content overlap:

1. For each A–B pair with **different** relative paths:
   a. Strip fenced code block content before extracting headings (track ` ``` ` / `~~~` open and close; headings inside code blocks are not real section headings).
   b. Extract all `##` headings from the non-fenced content.
2. Compute overlap ratio: `matched headings / max(headings in A, headings in B)`.
3. If ≥ 50 %: flag as `merge-md-cross` candidate. Record file paths, overlap %, matched headings, and a proposed canonical output filename (derived from shared topic).
4. If < 50 %: leave `copy-from-a` / `copy-from-b` unchanged.
5. Do not scan scripts, binaries, or `other` files.

Update `directory-manifest.md` with finalized actions and normalization decisions.

### Build Copy Manifest

After all actions are finalized, write `<run_dir>/copy-manifest.txt` with every `copy-from-a`, `copy-from-b`, and `copy-any` pair — one per line in `src -> dst` format:

```
# copy-manifest.txt — generated by Step 2
<source-file-1> -> <output>/<normalized-relative-path-1>
<source-file-2> -> <output>/<normalized-relative-path-2>
...
```

Omit in-place no-ops (`output = skill-a` files already at their destination). Omit `merge-md`, `merge-md-cross`, and `copy-both-with-suffix` entries — those are handled separately in Steps 5b–5d.

If there are no copy actions (e.g., fast-path or all-in-place), write an empty manifest with only the comment header.

---

## Step 3 — Confirmation Gate

**Pause. Present the full `directory-manifest.md` to the user before writing anything.**

Present the manifest grouped into four sections:

1. **Clean copies** — `copy-from-a`, `copy-from-b`, `copy-any` (count)
2. **Same-name merges** — `merge-md` (count)
3. **Content-overlap pairs** — `merge-md-cross` candidates (list each pair: file A, file B, overlap %, proposed output filename)
4. **Manual review items** — `copy-both-with-suffix` (count)

Also include: directory name normalizations (if any) and output directory.

For each content-overlap pair in section 3, the user may:
- Accept `merge-md-cross` (default) and confirm or rename the proposed output filename.
- Override to `copy-both` — both files are copied as-is with suffix; no merge performed.

The user must explicitly confirm before proceeding to Step 4.

- `dry_run=true`: stop here. Report the manifest only.
- User rejects: stop. Do not modify any files.
- User requests changes to action assignments: update `directory-manifest.md` and re-present before continuing.

---

## Step 3.5 — Pre-Copy B-Only Files (in-place merges only)

Only when `output = skill-a` (in-place merge) **and** `b_skill_only=false`.

Execute all `copy-from-b` and `copy-any` actions from the copy manifest **before** the SKILL.md merge. This prevents the `validate-frontmatter` hook from flagging broken references when SKILL.md is edited to add entries for B's files — those files are already on disk by the time the hook fires.

```
python .claude/scripts/copy_files.py --manifest <run_dir>/copy-manifest.txt
```

If the script exits 1 (destination already existed), report which were skipped. If it exits 2, report the error and stop.

Record the result in `directory-manifest.md`. In Step 5a, **skip re-executing copy-from-b and copy-any actions** — they were already completed here.

Skip this step when:

- `output ≠ skill-a` (standard merge — B files are copied after SKILL.md is written to the separate output directory; no hook fires on A's existing SKILL.md)
- `b_skill_only=true` (no non-SKILL.md files in B)

---

## Step 4 — SKILL.md Merge (delegate to `/merge-pipeline`)

Invoke `/merge-pipeline` with:

```text
files:
  - <skill-a>/SKILL.md
  - <skill-b>/SKILL.md
target_type:          skill
merge_strategy:       <merge_strategy>
merge_goal:           <merge_goal>
preferred_style:      <preferred_style>
strictness:           <strictness>
documentation_depth:  <documentation_depth>
skip_review:          <skip_review>
skip_document:        <skip_document>
skip_backup:          <skip_backup>
skip_assess:          <skip_assess>
skip_self_critique:   true
output_path:          <output>/SKILL.md
run_dir:              <run_dir>/skill-md-pipeline/
```

`skip_self_critique: true` — the outer workflow runs its own self-critique in Step 8.

The nested pipeline writes its artifacts to `<run_dir>/skill-md-pipeline/`. The merged `SKILL.md` is written to `<output>/SKILL.md`.

The nested `/merge-pipeline` pauses at its own assessment step for user confirmation as usual.

### Step 4.5 — Post-Merge Diff

After `/merge-pipeline` completes and the merged `<output>/SKILL.md` is written, present the actual diff to the user:

```
git diff HEAD -- <output>/SKILL.md
```

Report the summary: lines added, lines removed, sections changed. This shows what was actually written, not just what was planned — making regressions and unexpected changes visible before Step 5 runs.

If the file is new or untracked (no prior `HEAD` version), present the frontmatter block and a section list (all `##` headings) instead of a diff.

---

## Step 5 — Directory Contents Execution

Execute classified actions from `directory-manifest.md`. Run copies first, then merges.

### 5a — Copy Actions (`copy-from-a`, `copy-from-b`, `copy-any`)

Skip if `b_skill_only=true` (no non-SKILL.md files exist in B; nothing to copy beyond what A already has at output).

Skip `copy-from-b` and `copy-any` entries if Step 3.5 already ran (in-place merge — those copies were executed before the SKILL.md merge to prevent hook timing conflicts).

Otherwise, execute all copy actions using the manifest built in Step 2:

```
python .claude/scripts/copy_files.py --manifest <run_dir>/copy-manifest.txt
```

If the script exits 1 (one or more destinations already existed), report which were skipped. If it exits 2, report the error and stop.

### 5b — Merge Actions (`merge-md`)

For each same-named markdown pair, invoke `/merge-md-context`:

```text
files:
  - <skill-a>/<relative-path>
  - <skill-b>/<relative-path>
target_type:      reference
merge_strategy:   <merge_strategy>
preferred_style:  <preferred_style>
strictness:       <strictness>
output_path:      <output>/<normalized-relative-path>
run_dir:          <run_dir>/reference-merges/<filename>/
```

Write the merged file to `<output>/<normalized-relative-path>`.
Write a brief merge summary to `<run_dir>/reference-merges/<filename>/merge-report.md`.

### 5c — Conflict Actions (`copy-both-with-suffix`)

- Copy A's version as the primary output:
  ```
  python .claude/scripts/copy_files.py <skill-a>/<relative-path> <output>/<normalized-relative-path>
  ```
- Copy B's version with suffix:
  ```
  python .claude/scripts/copy_files.py <skill-b>/<relative-path> <output>/<basename>-from-b.<ext>
  ```
- Record both paths in `directory-manifest.md` under `Manual Review Required`.

### 5d — Cross-File Merge Actions (`merge-md-cross`)

For each content-overlap pair confirmed in Step 3, invoke `/merge-md-context` with the same parameters as **5b**, substituting the two different-named source files and the canonical output name confirmed by the user:

```text
output_path: <output>/<canonical-output-name>
run_dir:     <run_dir>/reference-merges/<canonical-output-name>/
```

Write a brief merge summary to `<run_dir>/reference-merges/<canonical-output-name>/merge-report.md`.

---

## Step 6 — Reference Table Integrity Check

### Canonical Reference Files Table Format

The merged SKILL.md must use the `${CLAUDE_SKILL_DIR}/` path prefix for all file references. This is the platform-supported substitution that resolves correctly at runtime. Relative markdown link syntax (`[text](path)`) may display locally but does not resolve at runtime.

Canonical format:

```markdown
## Additional Resources

| File | Purpose | When to Read |
|---|---|---|
| `${CLAUDE_SKILL_DIR}/references/foo.md` | What it covers | When to load it |
| `${CLAUDE_SKILL_DIR}/scripts/bar.py` | What it does | When to run it |
```

During the merge, normalize all reference paths to this format. Update any entries that use raw relative paths or markdown links.

After all files are written:

1. Read the merged `<output>/SKILL.md`.
2. Locate the Reference Guide table — any `## Reference` or `## Additional Resources` section containing a table with file paths.
3. For each path entry in the table:
   - Check if the file exists at `<output>/<path>`.
   - If the path uses a pre-normalization directory name, update it to the `reference_dir` value.
   - If the file is still missing after all copy/merge actions:
     - Cross-reference the pre-existing orphan list from Step 0.3.
     - If the path was already missing before the merge: flag as `⚠ pre-existing orphan` (not caused by this workflow).
     - If the path is new (added during the SKILL.md merge) and missing: flag as `⚠ merge-caused unresolved reference` — investigate.
4. If any paths were updated: apply the edits to `<output>/SKILL.md` and record the changes.
5. Write results to `<run_dir>/reference-integrity.md`:
   - Resolved paths (count)
   - Updated paths (old → new, with rationale)
   - Pre-existing orphans (list — present before merge; not caused by this workflow)
   - Merge-caused unresolved references (list with suggested action)

If unresolved references remain: warn, record in the final report, but do not block.

---

## Step 7 — Backup Source Directories

Skip if `skip_backup=true`.

This step runs **after** Step 4 (SKILL.md merge is complete) so the inner pipeline's own backup has already captured the pre-merge SKILL.md for skill-a. Outer backup covers the directory-level snapshot; it does not duplicate the inner pipeline's SKILL.md backup.

### When `output = skill-a` (in-place merge)

**Skip backing up skill-a entirely.** At this point skill-a's SKILL.md is the merged output — copying it would only duplicate the merge result. The pre-merge SKILL.md is preserved by the inner pipeline at:

```
<run_dir>/skill-md-pipeline/backup/<skill-a-dirname>--SKILL.md
```

Back up skill-b only:

```
python .claude/scripts/copy_files.py <skill-b>/ <run_dir>/backup/<skill-b-dirname>/
```

### When `output ≠ skill-a` (standard merge)

skill-a is unmodified (all writes went to `<output>`). Back up both source directories:

```
python .claude/scripts/copy_files.py <skill-a>/ <run_dir>/backup/<skill-a-dirname>/
python .claude/scripts/copy_files.py <skill-b>/ <run_dir>/backup/<skill-b-dirname>/
```

The script skips existing destinations (exit 1) — report the skip.

> **Directory support:** `copy_files.py` handles directory sources natively — when `src` is a directory it copies recursively using `shutil.copytree`. No `--recursive` flag or inline workaround is needed. If the destination already exists, the script exits 1 (skip); pass `--overwrite` to replace it.

Record in `manifest.md`:

```markdown
## Source Directory Backup

| Directory | Backup Path | Date | Notes |
|---|---|---|---|
| `<skill-b>` | `<run_dir>/backup/<skill-b-dirname>/` | YYYY-MM-DD | — |
| `<skill-a>/SKILL.md` (pre-merge) | `<run_dir>/skill-md-pipeline/backup/<skill-a-dirname>--SKILL.md` | YYYY-MM-DD | inner pipeline |
```

For standard merges, add the skill-a row with its backup path.

---

## Step 8 — Self-Critique

Skip if `skip_self_critique=true`.

Invoke `/merge-pipeline-self-critique` with `run_dir=<run_dir>`.

The self-critique covers the outer workflow run: directory scan, classification, copy/merge execution, and reference integrity. The nested `/merge-pipeline` artifacts in `<run_dir>/skill-md-pipeline/` are read as supporting evidence.

---

## Step 9 — Archive Source Directories

Only if `archive_sources=true`.

Move `skill-a` and `skill-b` directories to `<run_dir>/backup/` using `--move`:

```
python .claude/scripts/copy_files.py <skill-a>/ <run_dir>/backup/<skill-a-dirname>/ --move
python .claude/scripts/copy_files.py <skill-b>/ <run_dir>/backup/<skill-b-dirname>/ --move
```

Do not delete source directories automatically unless `archive_sources=true` is explicitly set.

---

## Step 10 — Report Pipeline Complete

Report level controlled by `verbosity`. Normal / Verbose:

```text
Pipeline complete: .claude/output/merge-skill-<name>-<YYYY-MM-DD>/

  backup/                        ✅  (or skipped)
  directory-manifest.md          ✅
  reference-integrity.md         ✅  (or skipped)
  skill-md-pipeline/             ✅
    assessment.md
    merge-report.md
    review-report.md             (or skipped)
    documentation.md             (or skipped)
  reference-merges/              ✅  (or skipped)
  self-critique.md               ✅  (or skipped)
  manifest.md                    ✅

Merged skill: <output>/
  SKILL.md                       ✅  merged
  README.md                         (copied / merged / absent)
  references/                    ✅
    <file>.md                       (copied / merged)
  assets/                           (copied / absent)
  scripts/                          (copied / ⚠ manual review / absent)

Content-overlap merges: <count>
Unresolved references:  <count>     (⚠ if > 0)
Manual review items:    <count>     (⚠ if > 0)
```
