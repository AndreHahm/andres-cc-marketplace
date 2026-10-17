(1) Command line

The argument is exactly `refresh`, one of the closed set of valid values, so I would run:

python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" refresh

If `CLAUDE_PLUGIN_ROOT` is empty in this session, which can happen in this repo's own sessions where skills load from the `.claude/` mirror, the variable would expand to a path that does not exist. In that case I would first confirm the mirrored file exists, then run:

python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" refresh

(2) What I would say to the user

"Refreshing the context mode. The saved mode is review, so I am reprinting its profile now. Review mode is active for the rest of this session. It covers the PR phase, including fixing triaged findings. `CLAUDE.md` and `.claude/rules/` still outrank the profile." After the script prints the profile, I would follow it and state plainly that review is the active mode. If the script instead reports that nothing is saved, for example because the session id is missing, I would say the profile was printed but not saved.

(3) Next

I would run the script, report the printed review profile, and keep following it for the rest of the session. I would not switch modes in place.
