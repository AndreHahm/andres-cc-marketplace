# Verify Tool/API/Language Behavior Before Instructing

## When this applies

Writing an instruction, script, or workflow step — inside a SKILL.md/agent/command body, a hook, or a
standalone script — whose correctness depends on how a tool, API, or language actually behaves, when
that behavior isn't already independently verified against its real, current source (not memory, not
an intuitive reading of its name). Applies whether the tool is a Claude Code primitive
(`AskUserQuestion`, `Bash`), a third-party CLI (`gh`, `jq`), a language runtime's own semantics (bash
arithmetic, Python's `ast` module), or an external API (GitHub's REST/GraphQL surface).

## Rule

Before writing an instruction, script, or workflow step whose correctness depends on how a
tool/API/language actually behaves — not how it's commonly assumed to behave — check the real source:
`ToolSearch`/the tool's own schema, `gh api --help` / `gh <cmd> --help`, a live one-off call against
the real API, or the language's own parser/stdlib instead of a hand-rolled approximation. A field or
behavior named intuitively (`gh pr checks`'s workflow field, a Reactions API entry) is not evidence of
what it actually contains or does — request the real value and read it.

This includes checking a tool's *full* schema for every constrained dimension, not just the one
already known from a prior incident — a tool can have independent caps or behaviors that compound
(see `AskUserQuestion`'s per-question *and* per-call caps below: the per-call cap surfaced in a
*later* review round on the same tool whose per-question cap was already known, not from the initial
check).

## Why

**This is the single largest source of avoidable third-party review rounds found so far in this
repo** — roughly a third of all findings across the first six PRs analyzed in
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` trace to this exact shape, more than any other single
pattern named in that document. Concrete instances, each independently found by a paid review round
that a five-minute live check would have caught before the first push:

| PR | Assumed behavior | Actual behavior |
|---|---|---|
| #47 | `sort \| head -1` just stops a pipeline cleanly | Under `set -e -o pipefail`, `head`'s early exit can SIGPIPE `sort` and abort the whole script |
| #47 | Bash `$((VAR))` treats `"08"` as the decimal number 8 | Bash arithmetic reads a leading-zero numeral as **octal**, and `08`/`09` are invalid octal digits → hard error |
| #49 | `jq -e 'any(...)'` over `--paginate` output matches if *any* page matched | `jq -e`'s exit status is based only on the **last** value it emitted — an earlier page's match is silently overridden |
| #49 | A GitHub reaction on a PR can be timestamp-correlated to "the current head" | The Reactions API has **no commit-SHA field at all** — a hard API limitation, not a bug to work around |
| #51 | `gh pr checks` exposes a workflow's **file name** | It exposes the workflow's **display name** — a different string, only discoverable by requesting the real JSON field |
| #52 | A shell variable set in one `Bash` tool call is visible to a later `Bash`/`Read`/`Write` call | Claude Code's `Bash` tool has no persistent shell state across calls — each call is a fresh subprocess |
| #54 | `AskUserQuestion` only caps options-per-question | It **also** caps questions-per-call (4), independently — a second, uncovered dimension of the same tool's schema |
| #55 | Hand-rolled regex can reliably extract Python call-site arguments | Only `ast.parse()` can — arbitrary legal Python source has an unbounded adversarial tail no regex will cover |
| #142 | A branch containing a merge commit can still be rebase-and-merged via `gh pr merge --rebase` | GitHub's rebase-and-merge unconditionally rejects a branch containing an existing merge commit — confirmed via a live `"This branch can't be rebased"` GraphQL error, not a transient failure |

Every one of these was independently confirmed real and fixed — this isn't about reviewers being
noisy. Each round cost the same push→CI→review→pull-comments round-trip regardless of how small the
underlying fix was, and every one of them was checkable locally, for free, before the first push.
