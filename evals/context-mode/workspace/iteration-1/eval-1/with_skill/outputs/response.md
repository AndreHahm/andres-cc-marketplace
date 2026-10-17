(1) Command line I would run:

python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" ship

The argument "ship" is exactly one of the closed set (admin, review, ship, refresh, status, off), typed by the user with no other words or characters, so it passes the validation in step 2. The session is fresh with no saved mode, so the script should not refuse the call.

(2) What I would say to the user:

"Context mode `ship` is now active for this session. It is the highest confirmation bar, meant for the step before `merge-pr` and any publish. I will follow the profile that was just printed for the rest of the session. `CLAUDE.md` and `.claude/rules/` still outrank it. If the output says the mode could not be saved (for example because no session id was available), the profile still applies now, but it will not be restored automatically after a compaction. In that case `/context-mode refresh` reprints it. To switch to a different mode later, write a handoff and start a fresh session, or run `replace <mode>` yourself."

(3) Next: follow the printed ship profile for the rest of the session. If the script exits with an error (invalid value or refusal), report that to the user and stop.
