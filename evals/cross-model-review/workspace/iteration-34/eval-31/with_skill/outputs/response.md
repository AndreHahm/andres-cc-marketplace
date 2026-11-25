Nothing was run or dispatched. "Section" means `references/optional-models.md`.

## Case A: exit 3, shim refused, user says use it anyway

I decline and offer no optional model this run.

1. Exit 3 means no usable copy (section 1). I say in one line: "No optional models this run: `/home/u/.asdf/shims/node (node) is not a native program, which looks like a version manager's shim`."
2. I do not run that node, hand-build a `node` / `rva-dispatch.mjs` command, resolve the shim myself, or search further. `$NODE` may only be what the locator printed on exit 0; the skill has no override question, so the user's request does not change the result.
3. Why: a version manager's shim may choose the real program from files in the checkout (section 6), i.e. the reviewed branch could choose what runs with the vendor login and sends the diff to a third party.
4. What the user can do: put a native `node` at a suitable place on PATH (an absolute entry, outside this repository and its worktrees, path owned by them or root, not writable by others, resolved path only `[A-Za-z0-9._/-]`, program named `node`). A later locator run then checks it from scratch.
5. No pick question, dry run or vendor egress question. Go on with Claude and Codex; Codex's own First-Send Confirmation is unaffected. Record "optional models: not located (node looks like a version manager's shim)" in `inspection_limits`.

## Case B: PATH link `/usr/local/bin/node` -> `/opt/node-22.1/bin/node`, exit 0

**`/opt/node-22.1/bin/node` goes into the command**, literally, as printed by the locator; not `/usr/local/bin/node` and not bare `node`.

It may differ because the locator takes `node` from an absolute PATH entry and prints it **with links resolved**. The link and every directory on the path were checked for ownership and writability as well. The resolved path names the program actually checked; the re-check in section 4 compares it later.

Steps:
1. Keep `identity` for the re-check. Check `$NODE`: absolute, outside `$REPO_ROOT`, only `[A-Za-z0-9._/-]`. Check `$RVA`: the same, plus ends in `/scripts/rva-dispatch.mjs`. Both pass here as far as the strings show (assuming the repository is not under `/opt`); otherwise offer none. (If `PLANNER_TOUCHED=1`, the locator would not have been run at all.)
2. Ask, with `multiSelect: true`, before Codex's First-Send Confirmation:
   > "Add optional reviewer models to Claude and Codex for this run? At most two."
   > Options: `agy`, `pi`, `devin`

   None or only "Other" text: none. Three: say so and ask again, never trim.
3. With the write helper, write `rva_diff.<N>.diff`, `rva_paths.<N>.txt`, `rva_review.<N>.md` under `$RUN` per batch with an eligible path.
4. Dry-run each picked vendor on every such batch (`<...>` values are written literally):

```bash
/usr/bin/env -u NODE_OPTIONS -u NODE_PATH -u NODE_COMPILE_CACHE -u NODE_EXTRA_CA_CERTS -u NODE_TLS_REJECT_UNAUTHORIZED -u NODE_V8_COVERAGE -u NODE_REDIRECT_WARNINGS -u NODE_ICU_DATA /opt/node-22.1/bin/node /opt/plugins/reviewadapters-kit/1.0.0/scripts/rva-dispatch.mjs --vendor <V> --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-<V>-<N> --instruction-file "<RUN>/rva_review.<N>.md" --diff-file "<RUN>/rva_diff.<N>.diff" --target-paths-file "<RUN>/rva_paths.<N>.txt" --cwd "<REPO_ROOT>" --dry-run
```

   With `PATH_FILTERED=1`, an `export PATH='<value>'` statement comes first. The call prompts; approve each once after reading it, never add an allow rule.
5. On `ok: true`, keep `recipient`, `model`, `reach`; the `model` must pass the character check and be the same in every batch. `secret_paths_unconfirmed` is rerun with `--secret-paths-confirmed` for that batch to get those values, and disclosed; any other failure drops the vendor.
6. One `AskUserQuestion` call, one question per remaining vendor:
   > "Send this review to <V> for this run? Recipient: <recipient>; model: <model>; reach: <reach>. Target paths of every batch: <paths>. This covers <2 x batches> dispatches (two per batch). The full diff text of these files leaves the machine, and Phase 2 also sends the other reviewers' findings, which may quote code outside the diff. [If set: the DISPATCHER_TOUCHED, REVIEW_UNVERIFIED/REFUTE_UNVERIFIED and INDEX_COPY_FAILED disclosures.] Not sent: <every sensitive_paths entry by name>. [Per flagged batch: every path of it, and the dispatcher's count.]"
   > Options: "Send to <V> for this run" / "Skip <V>"

   Declined or unanswered: drop, recorded "user declined to send to <V>".

## Case C: re-check prints node `/opt/node-22.2/bin/node`

The locator re-runs immediately before the first vendor's first real dispatch. `node` differs from the one the egress questions were asked against, so **both pi and devin are dropped for the run**: all vendors share the node, and neither has been dispatched. I do not dispatch on the old node (even if it still exists) or on the new one, and ask no replacement question: the skill gives none. A legitimate upgrade has the same result (section 6).

Report to the user: "pi and devin dropped: the locator now prints node `/opt/node-22.2/bin/node`, which is not the one you confirmed." Record that reason for **each** vendor in `inspection_limits`. No vendor diff was sent; no vendor envelope exists to keep. Claude and Codex (if confirmed) continue; if Codex has no valid Phase 1 envelope either, it is single-model mode.

## Case D: LDAP member in the private group

**No, the locator would not notice it.** The private-group exception reads `/etc/passwd` and `/etc/group` only. A member LDAP or SSSD adds to the private group, or a directory account with it as primary group, is not seen; reviewadapters-kit has the same limit. So a group-writable file could be accepted although that account can write it. Whoever runs the directory service could add either. This is a disclosed residual risk; the exception itself applies only on Linux with no extended ACL. The re-check does not close it either: it looks at the path and the device, inode, size and modification time of `node` and the dispatcher file, not group membership. If that matters, remove group write from the files and directories, or pick no optional model. I ask no question here, and change nothing.

## Case E: same paths, different `identity`

Same result as Case C: **pi and devin are both dropped**, none dispatched. A match needs `dispatcher`, `node` **and** `identity`; equal paths are not enough. `identity` is the device, inode, size and modification time of `node` and the dispatcher file, so a file at the same path was replaced or changed (in-place upgrade, rewrite, or a touch) since the user confirmed. I do not judge whether the change was benign, dispatch on the old result, or accept the new value.

Report: "pi and devin dropped: `node` or the dispatcher file changed at the same path since you confirmed (identity differs)." Record why for each in `inspection_limits`; Claude and Codex continue as in Case C.

Limit (section 6): identity does not cover file content or the dispatcher's other files. The same re-check runs before each vendor's first Phase 2 dispatch; a mismatch there drops vendors still to dispatch but keeps Phase 1 envelopes already returned.
