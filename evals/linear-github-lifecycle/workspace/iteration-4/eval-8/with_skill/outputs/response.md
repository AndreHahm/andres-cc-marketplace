Next, I stop `merge-to-completion` before its procedure (no policy check, merge or Linear write) and invoke `Skill(linear-github-lifecycle)` for ENG-205.

Why: its "When NOT to Use" routes taking an accepted Issue all the way to merge to `linear-github-lifecycle`, unless that skill dispatched this one for its phase. Here the user's request loaded it directly. The skill itself never dispatches the lifecycle skill; the routing is mine as caller, so I make the switch in the session and tell the user.

`linear-github-lifecycle` then sequences the stages and may dispatch `merge-to-completion` for its phase. Merge and Linear disposition each keep their own confirmation; merging alone never closes ENG-205, even though "close it" was requested.
