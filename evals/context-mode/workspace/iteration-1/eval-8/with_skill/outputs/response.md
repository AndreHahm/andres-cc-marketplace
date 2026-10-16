(1) Command line I would run (the question is a status request, and `status` is in the allowed closed set):

python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" status

(2) What I would say to the user:

I'd report what the script prints. Given the saved state, that is: "The active context mode is `review` (the PR phase: from opening the PR through the last review round, including fixing triaged findings). I'm following the review profile for this session. CLAUDE.md and .claude/rules/ still outrank it." If the script printed something different, I would relay that instead. I would not change or reprint the profile unless you ask for `refresh`.

(3) Next: wait for your next request and keep following the review profile. I would not switch modes in place. A different mode would need a handoff and a fresh session, or an explicit `replace <mode>` typed by you.
