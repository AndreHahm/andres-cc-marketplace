(1) Exact command line(s): none. I would run no command.

(2) What I would say to the user:

"No context mode is set for this session, and I am not setting one. A context mode is only set when you type `/context-mode admin`, `/context-mode review` or `/context-mode ship` yourself. Wording in a normal request like "review the PR and then ship it" does not count as that command. If you want a mode, type the command at the start of the session. Review and ship are separate modes, and switching from one to the other means writing a handoff and starting a fresh session, not switching in place. Otherwise I will go ahead with the review work without a mode, and the project rules in CLAUDE.md and .claude/rules/ still apply. I will ask before anything that publishes or merges."

(3) Next: I would continue with the PR review itself (through the git-kit review skill), with no mode set, and wait for your explicit go-ahead before the ship step (merge-pr).
