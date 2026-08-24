# Pattern Mining Methodology

## Action-Token Abstraction Examples

Raw actions must be normalized into abstract tokens before mining. Examples:

```text
cat docs/constitution.md
Read(docs/constitution.md)
```
become:
```text
READ_GOVERNING_ARTIFACT(constitution)
```

```text
uv run pytest tests/unit/test_state.py
uv run pytest -q tests/unit/test_state.py
```
become:
```text
RUN_TEST(unit,state)
```

Other useful tokens: `EDIT_CODE`, `COMMAND_FAILURE`, `RETRY_COMMAND`, `ASK_USER_QUESTION(<topic>)`, `DISPATCH_AGENT(<type>)`, `READ_ARTIFACT(<kind>)`.

## Automation Candidate Criteria

A mined sequence is a strong automation candidate when it is:

- Repeated at least 3 times.
- Stable in ordering (the same steps, in the same order, each time).
- Low in decision complexity (no branching judgment call embedded in the steps).
- Not an approval, architecture, or governance decision (those should stay manual).

## Memory-Recall Detection

- Check whether the project has a memory mechanism (auto-memory, `CLAUDE.md`, a prior persisted report on the same topic) that was available but never consulted where its content was clearly relevant.
- Distinguish "not consulted because irrelevant" from "not consulted despite being relevant" — only the latter is a finding.

## Repeated-Question Detection

- Compare every `AskUserQuestion` invocation in scope; flag near-identical questions (same header, same or near-identical option set) asked more than once without new information justifying the re-ask.
- A repeated question after new information arrived (e.g. re-asking scope after the user changed their mind) is not a finding.

## Retry-Loop Detection

From the mined sequences, a retry loop is: the same failing command (or a semantically equivalent one) repeated without an intervening change to the approach. Distinguish this from a legitimate multi-step retry, where each attempt differs meaningfully from the last.

**For `DISPATCH_AGENT`/`Skill` tokens specifically, compare arguments, not just the name.** A repeated-name signal (the same skill or agent type invoked many times in one session) is not by itself evidence of a loop — a legitimate batch sweep (e.g. running the same skill once per target in a list) produces the identical shape. Before flagging a repeated `DISPATCH_AGENT(<type>)`/skill-invocation token as a retry loop, check whether each occurrence's actual arguments (target path, scope, prompt) differ — a different target argument each time is an intervening change to the approach, even though the token itself repeats. Confirmed case: an 11x `reviewing-evals` invocation in one session initially read as a possible stuck loop by call count alone, but each of the 11 calls targeted a distinct skill path — a one-target-per-call sweep, not a retry (see `.claude/output/analyzing-sessions/plugin-devkit-self-reflexion-3d-2026-08-24T11-04-12Z.md`, finding F2).
