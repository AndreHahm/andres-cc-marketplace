# Response to the user

**User message:** "Review the PR and then ship it."
**Situation:** fresh session, no context mode saved.

---

I haven't set a context mode. Your message says "review" and "ship", but a mode is only set when you type `/context-mode <mode>` yourself, not when those words appear in a request. No mode is active, so I ran no command and saved nothing.

If you want a mode for this work:

- **Review phase.** Type `/context-mode review` at the start of the session that reviews the PR. That mode covers opening the PR through the last review round, including fixing triaged findings.
- **Ship phase.** The step before `merge-pr` belongs to `ship`, which has the highest confirmation bar. A session holds one mode for its whole life, and the script refuses to switch while a mode is saved. So you can't move from `review` to `ship` inside one session. Write a handoff when the review is done, then type `/context-mode ship` in a fresh session. If you deliberately want to override in place, `/context-mode replace ship` is the command, and only you can run it.

A mode only sets how cautious and how verbose I am. It doesn't do the review or the merge. That work goes through git-kit's lifecycle skills whether or not a mode is set:

1. **Review.** Use `collaborating-on-a-pr` for reviewer actions such as comments, approve or request changes, or `handling-review-findings` to triage findings already posted on the PR.
2. **Ship.** Use `merge-pr`, which checks that the PR isn't a draft, that required checks pass, that no change requests are open and that you have merge rights. It asks before it merges.
3. **Afterwards.** Use `finishing-work` to sync back to `main`.

Before I start, I need to know which PR and how to proceed. I would ask this with `AskUserQuestion`:

```
AskUserQuestion({
  questions: [{
    question: "No context mode is set. How should I proceed with reviewing and shipping the PR?",
    header: "Next step",
    options: [
      { label: "Proceed without a mode", description: "Review the PR via collaborating-on-a-pr/handling-review-findings, then run merge-pr (which asks before merging). No posture profile applied." },
      { label: "I'll set review mode first", description: "You type /context-mode review now; ship later in a fresh session with /context-mode ship after a handoff." },
      { label: "Stop", description: "Do nothing for now." }
    ]
  }]
})
```

Please also tell me which PR you mean (its number, or "the current branch's PR").

---

## Steps followed (note)

1. I read `plugins/context-kit/skills/context-mode/SKILL.md` in the worktree. It points to no other file needed for this case, so I read no profile file. Only a valid typed mode causes a profile to be read.
2. Under the skill's "When NOT to Use" and "Data-only boundary" sections, mode words in a prompt are data, not a command. Its Testing section names this exact prompt ("review the PR and ship it" with no command) as a case where no mode is set.
3. I ran no `set_mode.py` command, because there was no `/context-mode` argument and no request to check, reprint or clear the mode. Step 1's ask-which-mode fallback applies only to an invocation with no argument, which this was not. So I explained how to set a mode instead.
4. I pointed out the one-mode-per-session constraint: `review` followed by `ship` needs a handoff and a fresh session, or the user's own `replace`.
5. I routed the actual work to git-kit's skills (`collaborating-on-a-pr`/`handling-review-findings`, `merge-pr`, `finishing-work`), following the skill's statement that it doesn't do the work itself.
6. This was a plan-only run: no commands, no git or GitHub actions. The only file written is this one.
