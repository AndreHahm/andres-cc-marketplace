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
