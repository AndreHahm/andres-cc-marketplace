Source: `plugins/git-kit/skills/cross-model-review/references/scoped-review.md`, section 5 "Completed slices and round two" (with section 4 "Timeouts" and section 1 "Plan" for context), and `SKILL.md` Preflight step 1 and Phase 3.

## Round two planner invocation

Round two is a fresh invocation of the skill in the same conversation, for the same branch. It gets a new `$RUN` and the usual chained Preflight call, which exports `GIT_INDEX_FILE="<literal $RUN>/index"` so intent-added untracked files are seen (section 1). The planner call is the section 5 form. It passes the earlier manifest and one `--completed-slice` per completed slice, and writes to the new `$RUN`:

```bash
python3 plugins/git-kit/scripts/git-review-scope.py --merge-base "$MERGE_BASE" --base-ref "$BASE" ${SCOPE:+--scope "$SCOPE"} --prior-manifest "<round-one manifest path>" --completed-slice protected --completed-slice tests --output "$RUN/manifest-1.json" || PLAN_FAILED=1
```

- The `--prior-manifest` value is the manifest path that round one's Phase 3 report printed, together with the completed slice names.
- Only `protected` and `tests` are passed. The `scripts` slice's batch timed out and was not retried, so it is unfinished. Section 5 says "Never list a slice that timed out or failed". Under section 5's definition, a dispatched Codex review that returned no valid envelope leaves its slices not completed.
- `--output` must be a path that does not exist yet. The new `$RUN` provides that, since the planner never overwrites. A planner exit of 2 sets `PLAN_FAILED=1`, and the section 1 fallback applies. That means an `AskUserQuestion` offering an unscoped whole-diff review or stopping. It is never treated as a pass.

## What gets reviewed

- Per section 5, the planner skips files unchanged since a round that really reviewed them. For `protected` and `tests` that means the files the user did not touch while fixing findings.
- Files in those two slices that the user edited since round one are no longer "unchanged", so they are reviewed again. I am inferring this from the "skips files unchanged since" wording. The reference does not spell out how change is detected.
- The whole `scripts` slice is reviewed again, because it was never completed.
- Everything else is reviewed again too, including files a round-one folder pick had hidden. This also covers any slice round one dropped for budget reasons, since it was never completed.
- The new manifest drives the usual flow. Slices are packed into batches up to `max_slice_bytes`, each batch gets its own Codex Phase 1 and Phase 2 dispatch, and Claude reviews every `files` entry (section 3). A timeout is handled per section 4. The skill asks whether to retry that batch once with `CODEX_KIT_REVIEW_TIMEOUT_MS=480000` or leave it to Claude alone, and retries only on an explicit yes.
- Phase 3 again prints the new manifest path and the completed slice names, and discloses unfinished batches (section 6).
- The planner refuses a prior manifest that sits inside the repository, is a symlink, or is not owned by the current user. In that case it falls back to the full scope with a note.

## If the earlier manifest path is no longer known

Section 5's last sentence says: "If the earlier manifest path is not known, run as round one." So omit `--prior-manifest` and `--completed-slice` entirely. Use the section 1 command with just `--output "$RUN/manifest-1.json"`. The planner then reviews everything again, including the `protected` and `tests` files that already finished. Nothing is carried over. This also matches the rule that with no `--completed-slice`, everything is reviewed again.
