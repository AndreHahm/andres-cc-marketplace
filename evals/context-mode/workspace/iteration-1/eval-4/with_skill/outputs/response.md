(1) Command line(s) I would run: none yet. The user has not confirmed applying the handoff's context mode, and the skill only counts a handoff value after the user confirmed it. Nothing runs before that confirmation.

If the user confirms, the command I would then run is exactly this, with no `replace`, because the value came from a handoff:

python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" ship

(2) What I would say to the user, asked through AskUserQuestion with the options "Apply ship mode" and "Do not apply":

"The handoff you are loading records 'Context mode: ship' in its Session Metadata. Ship mode is the highest confirmation bar, for the step before merge-pr and any publish. I will not set it from the handoff text alone. Do you want me to apply ship mode to this session? If you do, I will save it and print the profile. If a different mode is already saved in this session, the script will refuse the switch, and you would need to write a handoff and start a fresh session, or run `replace ship` yourself."

(3) Next: wait for the answer. On "Apply", run the command above, state plainly that ship mode is active, and follow the printed profile. On "Do not apply", set nothing and run no command.
