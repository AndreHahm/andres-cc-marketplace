This repository (`antigravity-kit`) is a local copy of the GitHub repo
`yuting0624/antigravity-for-claude-code` — a Claude Code plugin that runs
the Antigravity CLI (Gemini) as a collaborating sub-agent under a
cost-aware routing policy. It was originally MIT-licensed (© 2026 linyuting)
and is now rebranded as `antigravity-kit` under Apache 2.0 with attribution.
It is not yet a git repository locally.

Run through `./docs/WORKFLOW_MAX_improved.md` to evaluate whether this
local copy is the right foundation to adopt as my own project — taking
ownership of the plugin and hardening it for my stack — with:

1. Ownership: rebrand, relicense (with attribution), and detach from
   upstream via a fresh git history
2. Hardening: tune the cost-aware routing policy for my model stack and
   verify the delegation / review / migration surface under my environment
3. Feature surface preserved: the existing slash commands, the
   `antigravity-delegate` subagent, hooks, and scripts stay functional
   throughout

The end state: `antigravity-kit` is my own hardened fork of the plugin —
rebranded and relicensed (Apache 2.0) with attribution to `yuting0624/antigravity-for-claude-code`,
detached from upstream, with a cost-aware routing policy tuned for my stack
and the same feature surface working on a known, tested foundation.

If the codebase is suitable, establish:
- Ownership (detach from upstream, fresh git history)
- Quality baseline (scorecards, SWOT, policies)
- Target roadmap (what to build, in what order)
- Governance framework (ADRs, CI/CD, migration strategy)

So that the first line of new code is written on a known foundation with
a clear direction.

Rules:
- Follow my instructions. I am the decision-maker.
- The candidate repository is this workspace itself (`antigravity-kit`).
  There is no `.draft` folder and none should be created — the repo under
  evaluation lives at the workspace root.
- Do not delete anything without my explicit decision.
- Go through the workflow in interactive mode — let me approve each step
  before starting planned tasks.
- Ask interview questions when the workflow specifies them. Do not skip
  interviews — they are a blocking gate. Present the Step Context Preamble
  (Step N of 29, Phase M of 8) before every interview block.
- Use background subagents for large analysis tasks (SWOT, scorecards,
  architecture analysis) to keep the session moving. Use a write-capable
  subagent profile (e.g. `subagent_general`) when the subagent should write
  artifacts directly to disk; use a read-only profile only for pure research.
  Instruct subagents to write files directly and return a short summary,
  not the full content.
- Write all evaluation artifacts to `./docs/draft/antigravity-kit/`.
- Track progress with a todo list across all 8 phases (29 steps total,
  including the final retrospective).
- At each phase gate, present a summary and ask for approval before
  proceeding to the next phase.

Per-Phase Self-Review and Self-Critique (mandatory at every phase gate):
Before presenting the phase summary and requesting approval, you must run
and present a short self-review with self-critique covering:

1. **Sub-Step Detection check:** Did you produce an artifact, make claims
   about the codebase, involve evaluation/analysis, have alternatives,
   modify files, have output consumed by the next step, or process multiple
   items? For each "yes," confirm the corresponding sub-step (self-review,
   self-verify, self-critique, decision-making, validation, approval,
   iteration) was actually performed. Flag any skipped sub-steps as gaps.
2. **Self-critique:** What did you miss? Where might the analysis be biased
   or shallow? What would you do differently if you re-ran this phase?
3. **Self-review:** Re-read the artifacts you produced this phase. Are they
   internally consistent? Do cross-references resolve? Are there
   contradictions between artifacts?
4. **Interview compliance:** Did you ask every interview question the
   workflow specifies for each step in this phase? If not, list which
   questions were skipped and whether the skipped decision affected the
   outcome.

Present the self-review and self-critique as a short section immediately
before the phase summary and approval request. Keep it concise — a few
bullet points per item is sufficient. The goal is honest accountability,
not performative completeness.

Final Step — Step 29 (Session Retrospective):
After all 28 implementation steps are complete and approved, execute
Step 29 (Session Retrospective) as a mandatory final step. This step is
part of the workflow and must not be skipped. Create
`./docs/draft/antigravity-kit/retrospective.md` covering:
- What worked well (keep doing)
- What didn't work (stop or change)
- What was missing (add to workflow)
- What was redundant (remove from workflow)
- Workflow deviations and gaps observed during this session
- Recommended changes to WORKFLOW_MAX_improved.md based on this run
Mark the todo list complete only after Step 29 is done.