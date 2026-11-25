# Response (nothing was run or dispatched)

## Case A: locator exit 3, shim `node`, user wants it anyway

I do not use it. Steps:

1. Exit 3 means no usable copy: offer no optional model (no pick question, no dry run, no egress question).
2. Say in one line: "No optional models this run: the locator refused `/home/u/.asdf/shims/node (node)`, not a native program, which looks like a version manager's shim."
3. Decline the override. A shim may pick the real program from files in the checkout (the branch under review), and that program would run the dispatcher with your vendor login and send the diff to a third party. The skill has no override and no question whose "yes" allows it. I do not search further, resolve the shim myself, substitute another node, or run the dispatcher directly.
4. I can say what would work: a real native program named `node`, in an absolute PATH entry outside the repository and its worktrees, owned by you or root along its path and not replaceable by others, ahead of the shim, in a later run where the locator exits 0. A distribution `node` linking to another name (`nodejs`, `node-22`, snap) and a resolved path with `@` or `+` are refused too.
5. Go on with Claude and Codex, with Codex's own First-Send Confirmation as usual. Record "optional models: not located" with the reason in `inspection_limits`.

No question is asked about the node.

## Case B: link resolved, locator exit 0

**`/opt/node-22.1/bin/node`** goes into the dry run, literally, not `/usr/local/bin/node` and not bare `node`.

It may differ from the PATH entry because the locator prints the path with links resolved, after checking the directories and links on the way and the program itself (owner you or root, not writable by others, sticky directories excepted; native program named `node`; not inside or reached through the repository or its worktrees). Using the resolved path runs the checked program, and the link is not followed again.

1. Check `$NODE`: absolute, outside `$REPO_ROOT`, only `[A-Za-z0-9._/-]`: passes (assuming the repository is not under `/opt/node-22.1`). Check `$RVA`: absolute, ends in `/scripts/rva-dispatch.mjs`, outside `$REPO_ROOT`, same characters: passes, on the same assumption.
   This assumes `PLANNER_TOUCHED` is not 1; otherwise no optional model is offered and the locator is not run.
2. Before Codex's First-Send Confirmation, ask with `AskUserQuestion` (`multiSelect: true`): **"Add optional reviewer models to Claude and Codex for this run? At most two."** Options `agy`, `pi`, `devin`. None means none; three: say so and ask again.
3. Per batch with an eligible path, write `rva_diff.<N>.diff`, `rva_paths.<N>.txt`, `rva_review.<N>.md` under `$RUN` with the write helper.
4. Dry-run each picked vendor on each such batch (with `PATH_FILTERED=1`, first its own statement `export PATH='<FILTERED_PATH>'`). `<...>` and `$RUN`/`$REPO_ROOT` are written out literally:

```bash
/usr/bin/env -u NODE_OPTIONS -u NODE_PATH -u NODE_COMPILE_CACHE -u NODE_EXTRA_CA_CERTS -u NODE_TLS_REJECT_UNAUTHORIZED -u NODE_V8_COVERAGE -u NODE_REDIRECT_WARNINGS -u NODE_ICU_DATA "/opt/node-22.1/bin/node" "/opt/plugins/reviewadapters-kit/1.0.0/scripts/rva-dispatch.mjs" --vendor <V> --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-<V>-<N> --instruction-file "$RUN/rva_review.<N>.md" --diff-file "$RUN/rva_diff.<N>.diff" --target-paths-file "$RUN/rva_paths.<N>.txt" --cwd "$REPO_ROOT" --dry-run
```

   Not in `allowed-tools`, so it prompts: approve each call once after reading the rendered command; never add an allow rule.
5. On `ok: true`, check `model` (character rule, same in every batch), keep `recipient`/`model`/`reach`. Then one `AskUserQuestion` call, one question per remaining vendor, for example: "Send this diff to <V> (recipient <recipient>, model <model>, reach <reach>)? Targets: <paths of every batch>; <2 x eligible batches> dispatches. The full diff text of those files leaves the machine; Phase 2 also sends the other reviewers' findings, which may quote code outside the diff. <any DISPATCHER_TOUCHED, REVIEW_UNVERIFIED/REFUTE_UNVERIFIED and INDEX_COPY_FAILED disclosures; each sensitive path by name, not sent; each flagged batch's paths with the dispatcher's count>" Options: "Send to <V> for this run" / "Skip <V>". `secret_paths_unconfirmed` gets a re-run of that batch's dry run with `--secret-paths-confirmed` before the question and the flag on dispatches only after yes, for that batch only; any other failure drops the vendor.

## Case C: re-check prints `/opt/node-22.2/bin/node`

Assuming the confirmations were for another node path, such as Case B's `/opt/node-22.1/bin/node`:

- A different `node` drops **every optional vendor still to dispatch**. None has been dispatched, so both pi and devin are dropped for the run, even though the locator succeeded and the dispatcher may be unchanged: they share the node and dispatcher.
- I do not dispatch on the old path, or adopt the new path by re-asking or repeating the dry run. The earlier confirmations do not carry over. No question is asked about it.
- `inspection_limits`, for each: "pi: dropped at the re-check, locator printed a different node (/opt/node-22.1/bin/node -> /opt/node-22.2/bin/node)", and the same for devin.
- There are no optional Phase 1 envelopes to keep (any would be kept). Continue with Claude and Codex; without a valid Codex envelope this is single-model mode, Medium cap.
- A new invocation can locate, pick, dry-run and confirm again.

If 22.2 was the path confirmed, nothing changed and dispatch proceeds.

## Case D: LDAP member of the private group

**No.** The private-group exception reads only `/etc/passwd` and `/etc/group`. A member that LDAP or SSSD adds to your private group is not seen, nor is an account there with it as primary group. So a group-writable file or directory in the kit copy or config could be accepted as private while that member can write it. This is a documented residual risk, the same as in reviewadapters-kit; whoever runs the directory service could add either.

The exception is for group write on the kit's files and directories (Linux only, no extended ACL). The text describes the `node` check as refusing directories (unless sticky) and a program writable by others, and says group-writable folders are refused.

My advice, not a skill step: removing group write (and other write) from the copy and its parents removes the reliance on that exception; or pick no optional model. No question or lookup is triggered by this; I would not query LDAP.
