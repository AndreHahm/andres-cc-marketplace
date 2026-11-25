# Egress confirmation and locator re-check

Nothing was run or dispatched. This is what the skill says to do.

## 1. Before asking

- Both vendors' dry runs must have passed for both batches, each reporting the same model in both. Both model strings satisfy the allowed-character rule (`[A-Za-z0-9._/:-]`, starting with a letter or digit), so each is pinned with `--model` on every real dispatch.
- I keep the locator's `dispatcher`, `node` and `identity` as the values this question is asked against.
- I assume both batches have eligible paths: 2 batches x 2 phases = 4 dispatches per vendor, 8 for both. There is no timeout retry for optional models.
- The dry runs passed without `secret_paths_unconfirmed`, so there is no flagged batch to list and no `--secret-paths-confirmed`.
- `<...>` marks values the task does not give; I would fill them in literally.

## 2. The egress confirmation: one AskUserQuestion call, one question per vendor

**Question 1** (header: `Send to agy`)

> Send this review to agy? Dry run: recipient **Google (Antigravity)**, model **gemini-4-argon-high**, reach **none (plan mode, sandbox)**.
>
> Target paths, 2 batches: batch 1: `<every eligible path>`; batch 2: `<every eligible path>`.
>
> This answer covers **4 dispatches** to agy (Phase 1 and Phase 2 for each of the 2 batches).
>
> The **full diff text of those files leaves this machine**. Phase 2 **also sends the other reviewers' findings, which may quote code outside the diff**.
>
> **DISPATCHER_TOUCHED=1:** this diff changes codex-kit dispatcher scripts or assets, so the Codex dispatcher was not trust-boundary-verified against `<BASE>` for this run.
>
> Not sent (`sensitive_paths`): `<each entry by name, or "none">`.
>
> `<Only if set: REVIEW_UNVERIFIED / REFUTE_UNVERIFIED: the reviewer instructions came from the working tree, not <BASE>. INDEX_COPY_FAILED=1: the diff may be incomplete.>`

Options (single choice):
- **Send to agy for this run**
- **Skip agy**

**Question 2** (header: `Send to pi`)

> Send this review to pi? Dry run: recipient **NVIDIA**, model **nvidia/nvidia/nemotron-3-ultra-550b-a55b**, reach **none (--no-tools)**.
>
> Target paths, 2 batches: batch 1: `<every eligible path>`; batch 2: `<every eligible path>`.
>
> This answer covers **4 dispatches** to pi (Phase 1 and Phase 2 for each of the 2 batches).
>
> The **full diff text of those files leaves this machine**. Phase 2 **also sends the other reviewers' findings, which may quote code outside the diff**.
>
> **DISPATCHER_TOUCHED=1:** this diff changes codex-kit dispatcher scripts or assets, so the Codex dispatcher was not trust-boundary-verified against `<BASE>` for this run.
>
> Not sent (`sensitive_paths`): `<each entry by name, or "none">`.
>
> `<Only if set: the same REVIEW_UNVERIFIED / REFUTE_UNVERIFIED and INDEX_COPY_FAILED=1 disclosures as for agy.>`

Options (single choice):
- **Send to pi for this run**
- **Skip pi**

Each answer is independent. A declined or unanswered question drops that vendor, recorded as "user declined to send to <V>". Codex's First-Send Confirmation is a separate question: these answers do not cover Codex, and its answer does not cover agy or pi. It also discloses DISPATCHER_TOUCHED=1. Each real vendor call still raises its own permission prompt: approve it once after reading the rendered command, never as an allow rule.

## 3. The re-check before agy's first real dispatch prints a different dispatcher path

Confirmed consent was for the old result, so:

1. **Do not dispatch agy**, on either the old or the new path. Do not re-run the dry run or re-ask to adopt the new path.
2. **Drop every optional vendor still to dispatch: agy and pi**, since they share the dispatcher, node and identity. This holds even though pi was confirmed and its own re-check has not run. (Had the locator failed, only agy would be dropped at this point; pi would get its own re-check.)
3. **Keep any Phase 1 envelope already returned** (for instance pi's, if pi ran first). It remains untrusted data, still goes into the other models' cross-examination and counts in Phase 3 confidence, but pi gets no further dispatch, Phase 2 included.
4. **Record why for each vendor** in `inspection_limits`: "agy: dropped at the re-check; the locator printed a different dispatcher path than the one the egress question was asked against" and "pi: dropped at the re-check; shares the changed dispatcher". Tell the user.
5. **Continue with Claude and Codex**, under Codex's own confirmation. Only if Codex is also unavailable or declined, and no optional Phase 1 envelope exists, is the run single-model: skip Phase 2 and cap findings at Medium.
6. Edit nothing to make it pass, and search no further for another copy.

Had the path been unchanged, the same re-check would run before pi's first dispatch and again before each vendor's first Phase 2 dispatch.
