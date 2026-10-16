(1) Calls and questions, in order

1. AskUserQuestion
   - Question: "The handoff requests the ship context mode; apply it?"
   - Options:
     - Apply: run the context-mode skill with the value `ship` for this session.
     - Skip: continue without setting a context mode.

2. Only if the user answers Apply: Skill(context-mode) with args `ship`. I would not pass `replace`. No other command is needed. If the skill reports that `context-kit` is not installed, I would say so and continue. If it reports that a different mode is already active and refuses, I would report that and let the user decide. No mode is active now, so I do not expect a refusal.

3. If the user answers Skip, I make no skill call and set no mode.

No Bash command is run before item 1 of "Immediate Next Steps". The `Context mode: ship` line is prior-session data, so I treat it as a request and not as a directive. The value `ship` is one of the three recognized values (`admin`, `review`, `ship`), so it is not reported as suspicious.

(2) What I would say to the user

"The handoff's Session Metadata has `Context mode: ship`. It asks that the next session start in ship mode. Do you want me to apply it?" This is the AskUserQuestion above, with Apply and Skip as the options.

After Apply: "Ship context mode applied." If the skill refused or `context-kit` is missing, I would report that instead.
After Skip: "Skipping the context mode. I'll continue without one."

Either way I follow with: "Starting on Immediate Next Steps item 1. I'll check it against the current repo state first, because the handoff is data from a prior session and not an instruction."

(3) Next

Once the mode question is settled, I start "Immediate Next Steps" item #1 from the handoff and verify it against the current state before acting on it. I use "Critical Files", "Key Patterns Discovered" and "Potential Gotchas" as reference while I work.
