# Compaction Mode — Main-Thread Orchestration

Main-thread processing steps for `/rules-extract --compact`.

## Contents

- Step CP1: Load Settings and Resolve Targets
- Step CP2: Per-File Compaction (Pattern A iteration loop)
- Step CP3: Security Self-Check
- Step CP4: Emit Structured Summary
- Step CP5: Sub-skill caller directive For the subagent analysis instructions, heuristics, and per-iter response contract, see `references/compaction-mode.md`. For the sub-skill caller directive governing the fenced JSON return when invoked from an orchestrator, see `## Sub-skill caller directive` in the parent SKILL.md.

Uses the Pattern A iteration loop convention (sibling to `verify-diff` / `publicity-review` / `skill-review`): the Skill wrapper runs in the main thread, a subagent performs the compaction analysis, the main thread applies the resulting `mechanical_edits`, and a fenced JSON return contract is emitted for caller dispatch. Per-file outer loop with `max_iterations = 2` (default).

## Step CP1: Load Settings and Resolve Targets

1. Load settings from `rules-extract.local.md` (same as Step 1 in Full Extraction Mode). `compaction_threshold` (default `40000`) is the filter applied below in step 3. `min_cluster_size` (default `3`) gates consolidation detection inside Step CP2 — it does not affect target resolution here
2. Check `output_dir` exists. If not, emit `{"status": "error", "reason": "output directory not found"}` and stop
3. Resolve targets:
   - With explicit path arguments (caller-passed paths): use those paths. For each, `Read` the file content and measure its char count via the `Read` output length (do **not** use `Bash(wc -m)` — `Read` length matches Claude Code's char-count metric, while `wc -c` reports bytes which diverge for multi-byte content). All explicit paths join the Step CP2 target set, regardless of char count: under-threshold paths still enter Step CP2 so the consolidation pass can run on them — `mechanical_edits` will be empty for under-threshold files (the convergence check at (d) terminates them immediately), but `consolidation_proposals` may still be emitted. The widened `skipped-below-threshold` status (set at Step CP2 (d), not here — (f) merely records what (d) chose) labels these files. Explicit-paths mode accepts paths under either `output_dir` or `examples_output_dir` — callers needing to compact `.examples.md` files when `examples_output_dir != output_dir` must use this mode
   - Without arguments: `Glob <output_dir>/**/*.md` (covers `.md` / `.local.md` uniformly — and also `.examples.md` if any are still co-located under `output_dir` from legacy runs, since the glob does not distinguish by extension). For each file, `Read` and measure its char count; collect entries with char count `> compaction_threshold` into the target set. **Note**: discovery mode does **not** surface sub-threshold files in `files_processed` (they are silently filtered out). This asymmetry is intentional: an unargumented `--compact` invocation reports only files that actually crossed the threshold, while caller-passed paths report every path the caller named so the caller can correlate input to output. **Trade-off**: clusters inside small (under-threshold) files are not detected by discovery mode; to scan them for consolidation, invoke `--compact <path>` (or `--compact <path1> <path2> ...`) with explicit paths. **Discovery scope**: this branch scans `output_dir` only — when `examples_output_dir` differs from `output_dir` (including the default `.claude/rules-extras` configuration), `.examples.md` files under `examples_output_dir` are **not** discovered automatically. Rationale: `.examples.md` files outside `.claude/rules/**` are already exempt from Claude Code auto-load, so they do not consume session-start context and the compaction priority is correspondingly lower; the explicit-paths route preserves the ability to compact them on demand

   Cache the per-file `Read` content keyed by path for reuse in Step CP2 (a) iter 1's dispatch payload — avoids a second `Read` of the same file before the first subagent dispatch
4. If the target set is empty (no paths resolved at all — empty explicit-paths argument or zero discovery hits), emit `{"status": "no-actionable", "compaction_threshold": <int>, "min_cluster_size": <int>, "files_processed": [], "reason": "no targets resolved"}` and stop

## Step CP2: Per-File Compaction (Pattern A iteration loop)

**Pre-register per-file TodoWrite items** — before entering the per-file outer loop, create one TodoWrite row per file in the target set (e.g. `compact: <path>`); the target set now includes both over-threshold and under-threshold explicit paths (under-threshold paths enter the loop so the consolidation pass can run on them). Mark each row `in_progress` before its first dispatch and `completed` after the per-file loop terminates (regardless of `per_file_status` outcome — `converged` / `partial` / `unresolved` / `error` / `skipped-below-threshold` all flip the row to `completed`; the outcome is carried in the per-file record, not the TodoWrite status). Per-iter progress within a file is tracked inline within this Step (no per-iter TodoWrite row) because the iter count is bounded at `max_iterations = 2`.

For each file in the target set, run the per-file iteration loop. `max_iterations = 2` by default (compaction is judgment-heavy; two passes give the subagent a chance to refine its first attempt before declaring `partial`). Under-threshold files terminate at iter 1's (d) convergence check (chars_after ≤ compaction_threshold is already true), so their loop effectively runs once for consolidation detection only.

**(a) Read & dispatch (per-iter)**: On iter 1, reuse the cached content from Step CP1 step 3 — `chars_before` is that cache entry's char count (avoids re-reading the same file). On iter `i ≥ 2`, re-`Read` the target file so the subagent operates on the post-prior-iter content. Spawn an `Agent` (`subagent_type: general-purpose`) with the dispatch prompt assembled from these `--- LABEL ---` sections (same fence convention as `verify-diff` Step 3 dispatch):

- `--- TARGET FILE ---`: absolute path + full current content
- `--- COMPACTION HEURISTICS ---`: the four heuristics enumerated in `references/compaction-mode.md` § Heuristics (class-level extension merge / similar-entry merge / example reference extraction / one-shot incident dropout) — emit into `mechanical_edits` / `structural_notes`
- `--- CONSOLIDATION HEURISTICS ---`: the four heuristics enumerated in `references/compaction-mode.md` § Consolidation heuristics — emit into `consolidation_proposals` only, gated by the resolved `min_cluster_size`
- `--- TARGET CHARS ---`: the resolved `compaction_threshold`
- `--- MIN CLUSTER SIZE ---`: the resolved `min_cluster_size` integer
- `--- ITER INFO ---`: current iter number (1 or 2), `max_iter` (2). On iter 2, also include a one-line summary of what iter 1 applied (the count of `mechanical_edits` landed and the iter-1 `chars_after` figure) so the subagent can plan an additional pass. Note: `consolidation_proposals` are collected from iter 1 only and the subagent should not re-emit them on iter 2
- `--- COMPACTOR PROMPT ---`: the subagent instructions, including the `mechanical_edits` `old_string` uniqueness convention (1–3 lines of surrounding context, per the `verify-diff` convention) and the two-heuristic-set / distinct-output-array routing (see `references/compaction-mode.md` § Contract). Include the body verbatim from `references/compaction-mode.md`
- `--- RESPONSE FORMAT ---`: the fenced JSON schema the subagent must emit (per-iter response, not the top-level skill return shape)

**(b) Parse**: parse the subagent's fenced JSON response. Evaluate in this order, **first match wins** (same evaluate-in-order discipline as `verify-diff` § (b) Parse & apply):

1. **Verdict missing or malformed** — no fenced JSON block found, or JSON parse fails → terminate this file's loop with per-file `status: "error"`, `reason: "verdict parse failure"`
2. **Schema violation** — required keys (`mechanical_edits`, `structural_notes`, `consolidation_proposals`) are missing, values are not arrays, or any entry fails its expected shape: each `mechanical_edits` entry needs non-empty string `file`, `old_string`, `new_string`; each `structural_notes` entry needs non-empty string `file`, `description`, `rationale`; each `consolidation_proposals` entry needs non-empty string `file`, non-empty `cluster_bullets` array (each item with non-empty string `line_range` and `snippet`), `merged_principle` object with non-empty string `name` and `text`, and non-empty `replacements` array (each item with non-empty string `line_range`, `strategy ∈ {"delete", "cross_ref"}`, and — when `strategy: "cross_ref"` — non-empty string `cross_ref_text`) → terminate with per-file `status: "error"`, `reason: "verdict schema violation"`. Validating entry shape here prevents a malformed entry from crashing downstream consumers (`Edit` calls for `mechanical_edits`, caller-side rendering for `consolidation_proposals`). For forward-compat with older subagent prompts that do not emit `consolidation_proposals`, the main thread treats a **missing** `consolidation_proposals` key (not present in the JSON) as an empty array; only an explicitly non-array value triggers the schema-violation path
3. **Divergence (iter `i ≥ 2`)** — the `(remaining_edits_count, structural_notes_count)` multiset matches iter `i − 1`'s same multiset (the subagent is not making forward progress) → terminate with per-file `status: "unresolved"`, `reason: "no progress between iters"`
4. **Otherwise** — proceed to apply

**(c) Apply (per-iter)**: this phase has two sub-phases — (c1) `mechanical_edits` apply (compaction heuristics 1–4), followed by (c2) `consolidation_proposals` main-thread synthesis (iter 1 only; consolidation heuristics 1–4). Both sub-phases share the iter-level `applied_edits_count` counter.

**(c1) `mechanical_edits` apply**: for each entry in `mechanical_edits`, re-`Read` the target file (so `old_string` matches the current contents after any earlier edit in this iter), then call `Edit`. **Scope rail**: before each `Edit`, verify the entry's `file` equals the target file's path; if not, skip that entry (no working-tree write) and record the rejected path. This mirrors `verify-diff` Auto-derive A2 (c) Scope rail. If `old_string` is not found, skip that entry — this is the expected no-op fallback for overlapping edits emitted from the same iter-1 snapshot. Increment the iter-level `applied_edits_count` only for entries whose `Edit` call succeeded.

**(c2) `consolidation_proposals` main-thread synthesis (iter 1 only)**: for each cluster in `consolidation_proposals` (process clusters sequentially — cluster A complete before cluster B begins, so cluster B's bullet extraction reads the post-cluster-A working-tree state). Per § `consolidation_proposals` schema in `references/compaction-mode.md`, the subagent does **not** emit `mechanical_edits` for these proposals — main thread synthesizes the `Edit` calls from the proposal's `cluster_bullets` + `merged_principle` + `replacements` fields. Per-cluster procedure:

1. **Re-Read target file** to capture the current content (cluster B reads post-cluster-A state).
2. **Verbatim bullet extraction**: for each `cluster_bullets[i]`, use `snippet` (≤120 chars prefix, canonical `tail-truncate / no ellipsis / leading bullet prefix preserved` form per schema) as a **byte-level prefix-match seed** against current file lines. Extract the full bullet body **excluding the trailing newline** — the surrounding `\n` is preserved on disk by `Edit`'s in-place replacement semantics for steps 4 (insertion) and 5 (`cross_ref`), and the trailing `\n` is appended explicitly to `old_string` by step 5's `delete` strategy. **Tie-breaker (best-effort)**: if multiple lines prefix-match, use `cluster_bullets[i].line_range` as the authoritative selector. Note that (c1)'s `mechanical_edits` apply earlier in the same iter may have shifted line numbers since the subagent's iter-1 snapshot — `line_range` is best-effort against the post-(c1) file; if the snippet collides with multiple lines AND `line_range` no longer resolves to a prefix-matching line, treat the bullet as unresolvable and let the resulting `Edit` no-op-skip via the standard verbatim-not-found fallback (no wrong-line edit lands). Comparison is byte-level — do not interpret backticks or regex metacharacters. **Multi-line bullet**: if `line_range.M > L`, extract lines L through M inclusive as the full bullet body (multi-line `old_string` — same trailing-newline-excluded convention; the final line's `\n` is omitted).
3. **Ambiguous-emit picker**: per `references/compaction-mode.md` § `consolidation_proposals` schema's `replacements` paragraph, the subagent may emit **both** a `{strategy: "delete"}` and a `{strategy: "cross_ref"}` entry for the same `line_range` when the choice is ambiguous. Main thread **prefers `cross_ref` over `delete`** to preserve incident pointers per § Preservation rules (iii)–(iv); ignore the `delete` entry when both are present.
4. **Insertion edit** (1 per cluster): `Edit` with `old_string` = `cluster_bullets[0]` full bullet, `new_string` = `- ` + `merged_principle.text` + `\n` + the original bullet body. This inserts the merged principle immediately above the first cluster bullet.
5. **Per-replacement edits**: iterate over the picker-selected `replacements[j]` entries from step 3 (a single chosen strategy per `line_range` after the cross_ref-over-delete preference is applied; `cluster_bullets[i]` without a matching `replacements[]` entry — e.g., `cluster_bullets[0]` when the subagent only emitted replacement strategies for `i ≥ 1` — is left in place as the anchor for step 4's insertion and is not edited here). For each selected `replacements[j]`, join back to the corresponding `cluster_bullets[i]` via `line_range` to obtain the full bullet body, then:
   - `strategy: "cross_ref"`: `Edit` with `old_string` = full bullet, `new_string` = `- ` + `cross_ref_text`
   - `strategy: "delete"`: `Edit` with `old_string` = full bullet + trailing `\n`, `new_string` = `""`

The same scope rail and no-op-fallback semantics from (c1) apply: any entry whose `file` does not match the dispatched target path is skipped (recorded as rejected); any `old_string` not found in the current content is skipped (treated as overlapping-edit no-op fallback). Increment `applied_edits_count` for each successful `Edit` — the counter is **shared** between (c1) and (c2), so a post-(c) `applied_edits_count > 0` means at least one compaction edit **or** consolidation edit landed.

**(d) Per-iter convergence check**: re-`Read` the target file to measure `chars_after_iter_i`. If `chars_after_iter_i ≤ compaction_threshold`, the file's compaction work is **complete**; terminate the loop. The per-file status is then **`skipped-below-threshold`** when the cumulative `applied_edits_count` across iters is `0` (no compaction-or-consolidation edits ever landed — this can only happen when the file was already at-or-below threshold on entry, since otherwise (d)'s convergence check would have been false and the loop would have continued to iter 2 or terminated via (e) as `partial`), or **`converged`** when the cumulative `applied_edits_count > 0` (one or more edits — compaction-mechanical or consolidation-synthesized — landed and the file is now at-or-below threshold). Per (c1) + (c2), `applied_edits_count` aggregates both edit classes, so the convergence check is uniform across compaction-only / consolidation-only / mixed runs

**(e) Continue or terminate**: if `i < max_iterations` and not converged, proceed to iter `i + 1` (back to (a)). If `i == max_iterations` and not converged, terminate the loop with per-file `status: "partial"` (the file was reduced but did not reach the threshold)

**(f) Per-file record**: at file completion, aggregate:

- `path`, `chars_before`, `chars_after` (the latest measured), `iterations_used`
- `applied_edits_count` (sum across iters)
- `structural_notes` — captured from iter 1 only (treat iter 1 as the source of truth; iter 2 re-runs the heuristics on already-modified content and may return drifted notes — same `inferred_intent persistence` discipline as `verify-diff`). If iter 1 produced no parseable verdict (terminated via the (b) error paths), `structural_notes` is `[]`
- `consolidation_proposals` — same iter-1-only discipline as `structural_notes` above. Iter 2's `consolidation_proposals_count` is ignored (the subagent should not re-emit them, and the main thread does not consume them if returned). If iter 1 produced no parseable verdict, `consolidation_proposals` is `[]`
- `per_file_status` ∈ {`converged`, `partial`, `unresolved`, `error`, `skipped-below-threshold`}. Set by (d) (`converged` or `skipped-below-threshold` per the threshold-vs-applied-edits discrimination), (e) (`partial`), or (b) (`error` / `unresolved`). The `skipped-below-threshold` value's semantic is **widened**: it now means "compaction skipped because the file was already at-or-below threshold (no compaction-or-consolidation edits landed — cumulative `applied_edits_count == 0`), but Step CP2 still ran the per-file dispatch and any `consolidation_proposals` / `structural_notes` may be present"
- `below_threshold` = `chars_after ≤ compaction_threshold`
- `reason` (set only when `per_file_status ∈ {error, unresolved}`; omitted otherwise — including for `converged` / `partial` / `skipped-below-threshold`)

**Important**: `consolidation_proposals` are **auto-applied by the main thread synthesis sub-phase (c2)** — the subagent still emits them as detection-only output (the subagent does **not** call `Edit` itself, per the analysis-only / file-write contract in `references/compaction-mode.md` § Forbidden tool calls and § `consolidation_proposals` schema's Materialization disposition), and the main thread synthesizes the corresponding `Edit` calls from the cluster description. The `consolidation_proposals` array in the per-file record is therefore now the **applied-cluster trace** (surfaced alongside the resulting file-content change), not a caller-judgment note. `structural_notes` remain **not applied** by this mode — they are surfaced as caller-judgment notes (the caller, e.g. `dev-workflow` Step 11 user-gate, decides whether to act). This matches the `skill-review` semantic for structural notes.

## Step CP3: Security Self-Check

Run Security Self-Check (same as Step 6.5 in Full Extraction Mode) on all modified files. If any sensitive content is detected, revert the file via `Bash(git checkout HEAD -- <path>)` and record the file in `files_processed` with the following fixed shape (overrides the per-file record produced by Step CP2 (f)):

- `path`: the reverted file's path
- `per_file_status: "error"`
- `reason: "security check failed"`
- `applied_edits_count: 0` (the revert wiped this file's landed edits — they no longer exist on disk)
- `iterations_used`: the count of iters whose subagent dispatch returned a verdict before the revert (carry over from Step CP2 (f))
- `structural_notes`: carry over from Step CP2 (f) (iter-1 captured notes survive the revert because they are caller-judgment notes about the file's prose, not edits that were wiped)
- `consolidation_proposals`: carry over from Step CP2 (f) (same reasoning as `structural_notes` — cluster proposals are not file edits)
- `chars_before`: the pre-Step-CP2 measurement (carry over from Step CP2 (f))
- `chars_after`: the post-revert measurement, which equals `chars_before` since the revert restored the file to its pre-edit state
- `below_threshold`: recomputed against the post-revert `chars_after` (so this matches whatever the file's threshold relation was before Step CP2 ran)

## Step CP4: Emit Structured Summary

Emit a single fenced JSON block at the end of the response, matching the schema:

```json
{
  "status": "compacted" | "no-actionable" | "error",
  "compaction_threshold": <int>,
  "min_cluster_size": <int>,
  "files_processed": [
    {
      "path": "<abs-path>",
      "chars_before": <int>,
      "chars_after": <int>,
      "iterations_used": <int>,
      "applied_edits_count": <int>,
      "structural_notes": [
        {"description": "<str>", "rationale": "<str>"}
      ],
      "consolidation_proposals": [
        {
          "cluster_bullets": [{"line_range": "<L:M>", "snippet": "<str>"}],
          "merged_principle": {"name": "<str>", "text": "<str>"},
          "replacements": [
            {"line_range": "<L:M>", "strategy": "delete"},
            {"line_range": "<L:M>", "strategy": "cross_ref", "cross_ref_text": "<str>"}
          ]
        }
      ],
      "per_file_status": "converged" | "partial" | "unresolved" | "error" | "skipped-below-threshold",
      "below_threshold": <bool>,
      "reason": "<optional, required when per_file_status=error or unresolved>"
    }
  ],
  "reason": "<optional, required when top-level status=error>"
}
```

Top-level `status` mapping (3-way OR — fires when any of `mechanical_edits` / `consolidation_proposals` / `structural_notes` is non-empty on any file):

- `compacted`: at least one file in `files_processed` has `applied_edits_count > 0` **OR** non-empty `consolidation_proposals[]` **OR** non-empty `structural_notes[]`
- `no-actionable`: the target set was empty, **or** every file satisfies all three of (`applied_edits_count == 0`, empty `consolidation_proposals[]`, empty `structural_notes[]`) — including all-error cases where iter-1 verdicts failed before notes / proposals could be collected
- `error`: top-level dispatch error (e.g. settings load failure, output directory missing). Per-file dispatch errors do not propagate to the top — they appear inside `files_processed` with `per_file_status: "error"` under top-level `status: "compacted"` (when at least one other file applied edits or produced notes / proposals) or `status: "no-actionable"` (when no file produced any actionable output)

`reason` enum (closed list — callers may switch on these values deterministically):

- Per-file `reason` (set when `per_file_status ∈ {error, unresolved}`):
  - `"verdict parse failure"` — subagent response had no fenced JSON block or failed to parse (Step CP2 (b) #1)
  - `"verdict schema violation"` — required keys missing, values not arrays, or entry shape failed (Step CP2 (b) #2)
  - `"no progress between iters"` — divergence check on iter `i ≥ 2` matched the prior iter's multiset (Step CP2 (b) #3)
  - `"security check failed"` — Step CP3 detected sensitive content and reverted the file
- Top-level `reason` (set when `status == "error"`):
  - `"output directory not found"` — Step CP1 step 2 directory check failed
  - `"no targets resolved"` — used with `status: "no-actionable"` from Step CP1 step 4 (top-level `reason` is optional in `no-actionable`; this token is its canonical value)

Partial results: when top-level `status: "compacted"`, individual files in `files_processed` may carry `per_file_status` of `error` / `unresolved` / `partial` / `skipped-below-threshold` mixed with `converged`. Callers should branch on `per_file_status` per file rather than assume uniform success. (`skipped-below-threshold` appears in explicit-paths mode for files whose char count was already at-or-below `compaction_threshold` — Step CP2 still ran on them for the consolidation pass, so they may carry `consolidation_proposals` / `structural_notes` even though `applied_edits_count == 0`.)

## Step CP5: Sub-skill caller directive

See `## Sub-skill caller directive` in the parent `rules-extract` SKILL.md.
