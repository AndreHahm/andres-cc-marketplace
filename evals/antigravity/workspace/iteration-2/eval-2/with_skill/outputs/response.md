I'll just make this edit directly rather than routing it through Antigravity.

Reasoning: this is a single-variable rename (`usr` → `user`) inside one function in one file. Per the `antigravity` skill's own cost-discipline guidance, delegation only pays off when the offloaded volume clearly exceeds the spec-writing + round-trip + verification overhead — "a small, self-contained, or judgement-heavy task" is explicitly called out as a case to just do directly, since delegating a tiny task is a net loss. A one-variable rename in one function is exactly that case, so I did not invoke `agy-delegate`.

Attempting the edit: I searched this repository (including the current worktree) for `src/auth.py` and could not find it — there is no file at that path anywhere in the working tree (only an unrelated third-party `requests/auth.py` inside `.venv/site-packages`, which is not part of this project's source and not what you meant).

Could you confirm the correct path to the file (or add it if it doesn't exist yet)? Once I have the right file, the change itself is trivial: locate the function using `usr`, rename the variable to `user` at its declaration and every reference within that function only, and leave the rest of the file untouched.
