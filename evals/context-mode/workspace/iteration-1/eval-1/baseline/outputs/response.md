I don't have a built-in "ship mode" — I don't maintain persistent modes or toggles that change my behavior across a conversation the way some tools/plugins do. Nothing in this repo's CLAUDE.md or `.claude/rules/` defines a "ship mode" either, so I don't have a documented switch to flip.

A couple of ways I could interpret the request — let me know which fits, or I'll default to the first:

1. **Communication style change**: You want me to be terser and more action-oriented from here on — less explanation, less asking, just making changes and reporting what I did (default assumption, since we're in auto mode and I should keep moving rather than stall on this).
2. **A specific repo workflow**: You want me to route through this marketplace's actual shipping path — i.e., use `git-kit`'s lifecycle skills (`starting-work` → `commit` → `create-pr` → `merge-pr` → `finishing-work`) for whatever change is next, rather than raw git commands.
3. **Something from another tool/context** (e.g. a CLI flag or IDE mode named "ship mode" elsewhere) that doesn't map to anything here.

If you tell me what you actually want shipped (a file, a fix, a PR), I'll proceed directly under interpretation #1 and use the proper git-kit skills for any git/GitHub steps along the way, per this repo's `route-through-git-kit-lifecycle-skills` rule — flagging first if a change looks like it needs plugin-rulebook or testing checks per this repo's other rules.
