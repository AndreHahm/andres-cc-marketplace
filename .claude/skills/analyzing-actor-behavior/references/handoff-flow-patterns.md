# Cross-Agent Handoff Flow Patterns

## Categories

- **Sequential delegation** — agent A's output becomes agent B's input, one after another. Healthy when each stage's output is actually consumed by the next; a smell when a later stage re-derives what an earlier stage already produced.
- **Parallel dispatch** — multiple agents run concurrently against independent scopes. Healthy when scopes genuinely don't overlap; a smell when two agents are given overlapping file/topic scope and produce contradictory findings that then need reconciling.
- **Nested/circular risk** — agent A's own instructions could cause it to (directly or via a shared component) invoke agent B, whose own instructions could invoke A again in the same pass. Flag any round-trip risk found, even if it didn't actually fire this session — it's a latent defect.
- **Handback without context** — an agent's result is handed back to the orchestrator, which then dispatches a new agent for follow-up work without carrying forward the first agent's findings, forcing the second agent to rediscover context the first one already had.

## What to Record

For each handoff pattern observed:
- Which agents were involved, and in what order.
- Whether the pattern was efficient (no redundant rediscovery) or lossy (context or findings dropped between stages).
- If nested/circular risk was found: whether it actually fired, or was only a latent possibility this session didn't trigger.
