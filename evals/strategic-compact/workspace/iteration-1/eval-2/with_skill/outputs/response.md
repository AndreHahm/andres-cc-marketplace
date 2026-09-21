Depends on where you are right now, not just how long we've been going. Quick way to decide:

**Good signs to compact now:**
- You just finished exploring/reading and are about to start writing code (exploration context rarely carries forward usefully)
- A milestone just landed — e.g. tests passing, a feature working end-to-end
- A plan is finalized and written down somewhere durable (so it survives the compact)
- A debugging thread just got resolved (the back-and-forth diagnostic noise won't be needed again)
- You're about to pivot to a different, unrelated task

**Hold off if:**
- You're mid-implementation with decisions/context that aren't captured anywhere else yet
- You're actively debugging and still need the diagnostic trail
- The current task is incomplete and you might need to reference earlier context to finish it
- A code review is in progress and you'd lose the review thread

If none of those "hold off" conditions apply, `/compact` is a reasonable call — quick, frees context immediately, though it may lose some nuance in the summarization. If this is a more complex piece of work where you want a cleaner, more deliberate handoff than the built-in summarizer gives you, `session-kit`'s `session-handoff` skill (if installed) is the better option before compacting/clearing. If you're switching to a genuinely unrelated task rather than continuing this one, `/clear` is the cleaner reset instead of `/compact`.

One practical tell: if you've crossed a threshold like 50+ tool calls in this session, that's usually a signal accumulated context is going stale even without a clean phase boundary — worth compacting on the next natural pause even if it's not a "perfect" milestone.

So — quick gut check for you: are you between phases right now (just wrapped something, not yet deep into the next thing), or are you still mid-task? If you're between phases, compact now. If you're mid-implementation or mid-debug, finish that thread first, then compact at the next natural break.
