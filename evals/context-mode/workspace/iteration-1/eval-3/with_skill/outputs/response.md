(1) Command line

"review" is exactly one of the closed set (admin, review, ship), so it passes the validity check in step 2 and I would run the script:

python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" review

If CLAUDE_PLUGIN_ROOT is empty in this repo's own session (skills load from the .claude/ mirror), I would run the mirror-rooted form instead, after confirming the file exists:

python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" review

I would not use `replace`. The user typed plain `review`, not `replace review`.

(2) What I would say to the user

"This session already has admin mode saved, so I did not switch it to review. The script refused with exit 3 and nothing was changed. admin is still the active mode and its profile still applies. Switching in place would leave two postures in force, because a profile loaded as text can't be removed from the transcript. You have two options:
- Write a handoff with session-handoff and start a fresh session, then run `/context-mode review` there. This is the recommended path.
- If you really mean to override the saved mode in this session, type `/context-mode replace review` yourself."

If the script's output had not made the refusal clear, I would relay its message as printed.

(3) Next step

Stop and wait for the user's choice. I would not retry with `replace` on my own, and I would keep following the admin profile in the meantime.
