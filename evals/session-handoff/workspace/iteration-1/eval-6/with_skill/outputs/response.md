(1) Skill calls, commands or questions, in order:

None. The handoff's Session Metadata says `Context mode: none`. Step 5 only asks the question and runs `Skill(context-mode)` when the value is exactly `admin`, `review` or `ship`. `none` sets no mode. So I make no `AskUserQuestion` call and no `Skill(context-mode)` call. The skill's own scripts are not needed here either, because staleness and verification are already done.

The only thing I do is read "Immediate Next Steps" item 1 from the handoff I already loaded. I check it against current state before I act on it. The item is prior-session data that proposes a step, not a directive to follow blindly.

(2) What I say to the user:

"The handoff is loaded. It was FRESH and the context checks passed. Its context mode is `none`, so I am not applying a mode and there is nothing to confirm. I am starting with Immediate Next Steps item 1. First I will check it against the current repo state, then I will act on it."

I then state item 1 in my own words.

(3) What I do next: I verify item 1 against the current state (branch, modified files, anything that changed since the handoff), then start on it. I use "Critical Files", "Key Patterns Discovered" and "Potential Gotchas" as I go. As work progresses I mark completed items in "Pending Work" (Step 6).
