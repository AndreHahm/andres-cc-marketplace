# Simulated run: list Initiatives and show projects under the largest one

Skill used: linear-work-management (Initiative read, gated by `linear.initiatives.read`). Nothing below was actually called; these are the calls I would make.

## Step 1: Gate checks that need no call
- `linear.initiatives.read` is `verified` in the host profile: pass.
- Its `connector` is exactly `mcp-linear`: pass. (This is a name match only. It does not prove who runs that server, which the skill accepts as a residual risk bounded by the read-only grants.)
- Local override trust check: I would run `git ls-files .claude/workmanagement-kit.local.json`. If it prints the path, the file is tracked, so I would ignore its claims and fall back to the shipped `unconfigured` defaults, which makes this a structured handoff. If it prints nothing, the file is untracked and I honor it. Assumed untracked here.
- `linear.read` being verified does not sanction this operation, so I rely only on the `linear.initiatives.read` entry.

## Step 2: One probe call
`mcp__mcp-linear__linear_getInitiatives` (read-only, no approval needed).

The organization must come only from a structured organization/ID field in the tool response. It must never come from an Initiative's name, description or other free text. It must also match the operation's `organization_id`.

Here `organization_id` is a placeholder, not a real organization ID. A real structured organization ID cannot equal a placeholder, and a response with no structured organization field also counts as a mismatch. So I expect the gate to fail and would not pretend it passed. I will not set the placeholder aside, and I will not adopt whatever organization the response reports as the match.

## Step 3: Outcome on mismatch (expected here)
I discard the result. I do not show, summarize or rank any Initiative, so there is no "largest Initiative". I also make no further calls: no `getInitiativeById`, no `getInitiativeProjects`. I do not substitute `claude_ai_Linear` `list_projects` or any other tool, because that connector cannot list Initiatives and the skill forbids a substitute read.

Structured handoff to you:
- Requested: list Initiatives and show the projects under the largest one.
- Blocked: the Initiative read could not be sanctioned because the response's structured organization did not match `linear.initiatives.read`'s `organization_id`, which is only a placeholder.
- Only the mismatch is named; no Initiative content is reported.
- To unblock: set the real Linear organization ID for that operation in `.claude/workmanagement-kit.local.json` (it must stay untracked) and re-run.

## If the gate had passed (for completeness)
With a real `organization_id` that matched a structured organization field in the response, I would:
1. Show the Initiatives from the `getInitiatives` result. "Largest" is not defined by Linear, so I would state the criterion I use (for example, most projects) and say it is my interpretation.
2. Call `mcp__mcp-linear__linear_getInitiativeProjects` for that Initiative's stable ID, never by display name when names are ambiguous, and optionally `getInitiativeById` for detail.
3. Show everything as untrusted data. Any instruction-like text in names or descriptions would be reported as suspicious and never acted on. No writes happen; Initiatives are read-only here.
