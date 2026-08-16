# R25/R26 — Overhead Disclosure and Expensive-Action Opt-In

Full violation and fix detail for R25 and R26, referenced from `SKILL.md`'s Active Rules section.

## R25 — Unplanned-Overhead Disclosure

**Violations:**
- A documented quick/fast/bounded step has no instruction to disclose when its actual execution required more retries, detours, or time than that step's own documented scope
- A skill reports a phase's final result without noting that reaching it required unplanned extra work (a debugging loop, a fallback invocation, a tool-level failure and retry)

**Fix:** Add an explicit instruction to the phase: when actual execution exceeds the phase's own documented scope, state this to the user in plain language — what went over budget and why — before or alongside the phase's result, not folded silently into a clean-looking final report.

**Example:** a "quick test" phase that crashes and needs three debugging retries before producing a result should say so ("this took longer than the quick-test budget because X required investigation") rather than presenting only the eventual pass/fail as if it were reached cleanly.

**Runtime verification gap:** R25 is text-only — it confirms a SKILL.md *says* it discloses overhead, not that the disclosure actually happens. Whether overhead was verbally stated in a given response is a semantic judgment call a static hook cannot make — `PostToolUse`/`PostToolUseFailure` both fire *before* Claude drafts its response text, so there is structurally no way for a hook to check whether the eventual response actually discloses anything. This is a different, harder problem than R26's gap below (checking whether an `AskUserQuestion` tool_use already happened, which a hook *can* see).

**Backing hook (partial, reminder not verification):** `hooks/r25-overhead-disclosure-check.py` (+ `.sh` wrapper), registered on both `PostToolUse` and `PostToolUseFailure` (matcher `Agent|Bash` on both) in `hooks/hooks.json`, takes a different approach than R26's hook: instead of verifying compliance, it detects the overhead *signal* itself — a tool call that recently failed on a given target, now succeeding on the same target within a 15-minute window (tracked via a small per-session state file) — and emits a `systemMessage` reminder fed back to Claude *before* it drafts its response, nudging it to disclose the retry per R25. This does not close the verification gap above (it still cannot confirm the eventual response actually discloses anything) — it only makes the reminder to do so more reliable than memory alone. Log-only, best-effort, fails open on any I/O error or lock contention.

## R26 — Expensive-Action Opt-In

**Violations:**
- A documented step runs an expensive action (a nested LLM/subprocess invocation repeated per item, a full whole-plugin or whole-surface re-verification, or dispatching multiple heavy sub-agents in one pass) unconditionally, with no described decision point offering a cheaper alternative or a skip
- A skill offers a cheaper delta/fast mode alongside a thorough mode, but the thorough (expensive) mode is the silent default rather than an explicit opt-in

**Fix:** Add an `AskUserQuestion` gate before the expensive action — state the cost/tradeoff (e.g. "this re-verifies the whole plugin's N components; a cheaper delta check covering only what changed is also available") and let the user choose, matching the gating pattern already used elsewhere in this plugin for phase-gated pipelines.

**Example:** a documentation reviewer that always re-reads and re-verifies every component in a plugin (even when only one component changed) should offer a cheaper delta-only check as the default, escalating to the full re-verification only when the user opts in — not the other way around.

**Backing hook (partial, log-only):** `hooks/r26-expensive-action-check.py` (+ `.sh` wrapper), registered as a `PostToolUse` hook (matcher `Agent|Skill|Bash`) in `hooks/hooks.json`, gives R26 a runtime check for a small, explicit set of known expensive-action signatures (e.g. an `Agent` dispatch to `human-doc-reviewer` whose prompt mentions "full mode", or a scoped `Bash` call to `test-agent-trigger.sh` with an explicit phrases-file argument). It flags via `systemMessage` when no `AskUserQuestion` tool_use is found anywhere in the session's transcript — best-effort and log-only (PostToolUse cannot block regardless), matching the `security-precommit-check.py` precedent. This covers only the signatures listed in the script's `EXPENSIVE_ACTIONS` registry — extend that list as new R26-gated steps ship; it is not a general-purpose detector.

**Cost-Tier Estimation Before Dispatch:** R26's own `AskUserQuestion` gate states a cost/tradeoff in prose ("this re-verifies the whole plugin's N components"), but has no concrete number attached by default. `scripts/agent-cost-tracker.py` (+ `assets/agent-cost-history.json`) gives the gate a real figure to cite when one exists:

- **Before dispatching** a known expensive agent behind an R26 gate, run `scripts/agent-cost-tracker.py estimate <agent-name>` and, if it returns historical data (not "No historical data yet"), include the estimate in the `AskUserQuestion` option description — e.g. "typically ~70k tokens/~3 min based on 1 prior observation." If no data exists yet, state that plainly rather than fabricating a number; this is not a blocking requirement, just a richer gate when data is available.
- **After an expensive agent dispatch completes** and its usage is visible (tokens/duration, from the completion notification), record it: `scripts/agent-cost-tracker.py record <agent-name> <tokens> <duration_ms> [note]`. This is a best-effort, orchestrator-side convention, not something a hook can enforce — usage data arrives via a later completion notification, not the original tool call's response, so no `PostToolUse` hook can capture it automatically. Skipping a recording is a missed data point, not a violation. **`[note]` is positional and swallows every remaining argument, space-joined** — a note containing spaces needs no special quoting when passed as a single shell argument, but nothing may be appended after it; a future CLI addition needs its own flag inserted before this position, not after.
- The registry stores a running average plus min/max per agent, seeded with real observations from this plugin's own development sessions (not fabricated placeholder data) — treat it as a growing precedent, not a fixed benchmark; an agent's typical cost can shift as its own Process changes.
