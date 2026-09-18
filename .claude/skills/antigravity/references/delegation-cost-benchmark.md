# Delegation cost benchmark: why batching is the lever

Rule 4 in the Cost discipline section ("batch, don't chatter") is the one that actually
moves the needle, and here is why, from a benchmark of this plugin
(Opus 5 conductor · Gemini 3.6 Flash High executor · agy 1.1.8 · n=3/arm, cold cache):

**Per delegation the economics are fine. Repeated ingestion is what breaks them.**
Offloading a large corpus works exactly as designed — the conductor's `cache_read` fell
**61%**, it never opened the corpus itself, and each digest came back at ~4k tokens. But
**each `agy-delegate` call is an independent session that shares no cache with the last
one**, so a conductor that delegated 7.3 times against the same corpus paid to ingest it
7.3 times. **Two-thirds of the executor's cost was re-reading material it had already
read.** Break-even on that task was ~5.7 delegations; the one trial that stayed at 5 came
in cheaper than solo Claude, the ones at 9 did not.

So when several delegations work over the same material:

- **Fold related units into ONE fully-specified delegation.** This is the only lever that
  actually removes a re-ingestion. Two questions about one corpus = one delegation asking
  for both, not two delegations.
  **Only fold units that genuinely belong together.** If combining them muddies the spec,
  don't — a vague mega-prompt returns worse work, and re-running it costs far more than
  the re-ingestion you saved. Quality of the spec beats the token arithmetic every time.
- Scope `--dir` to the smallest subtree that contains the work, and expect the executor's
  **read** cost — not its writing — to dominate.
- **Do NOT reach for `--continue` to avoid re-ingestion — measured, it makes things
  worse.** Resuming a session carries the whole prior conversation forward *and* agy
  re-reads the material anyway, so you pay both: on a repeated-corpus digest the continued
  second call cost **+82% and +277%** vs a fresh one (n=2), with `cache_read` 3–14× higher.
  `--continue` is for *resuming after a failure* (quota, timeout) — not a cost lever.

Two supporting facts, both measured: **delegation moves work rather than removing it**
(the hybrid ran ~2.8× the normalized token volume for the same result — it stays
affordable because the executor is cheaper per token, not because it does less), and
**agy's own prompt cache covers only ~2/3 of its context re-reads**, so the executor is
worse than Claude at carrying context. Both push the same way: fewer, larger delegations.

These are single-configuration measurements from 2026-07 on two task families, not
constants. Treat them as direction, and re-measure on your own workload before quoting
any figure.
