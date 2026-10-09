# Resolving a Repository Slug

`plugin-integration-intake` asks `linear-work-management` to turn an `owner/repo` slug into a Linear team, because
this skill runs the Local Override trust check that the intake gate cannot. This procedure only resolves; it
writes nothing.

1. Run the Local Override trust check first. If it fails, return a rejection.
2. Normalize the slug: lowercase it and remove one trailing `.git`. It must then match
   `^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$`.
3. Look it up as an exact key of `linear.repositories`. Two map keys that normalize to the same value are a
   configuration error and reject. An unknown slug is rejected, never guessed or defaulted.
4. The operation in use (`linear.read` or `linear.write`) must be `verified` with a non-null `verified_at`,
   otherwise reject.
5. Pick `test_team_id` when the caller asked for a test run, otherwise `production_team_id`.
6. Confirm the chosen team is in `team_ids` of the operation in use. An empty list rejects every team. A null team
   ID for the chosen environment is a rejection, never a fallback to the other environment.
7. Return the environment, the team ID and a plain statement of what was verified, or the reason for the rejection.
