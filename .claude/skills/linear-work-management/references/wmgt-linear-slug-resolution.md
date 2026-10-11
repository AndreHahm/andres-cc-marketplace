# Resolving a Repository Slug

`plugin-integration-intake` asks `linear-work-management` to turn an `owner/repo` slug into a Linear team, because
this skill runs the Local Override trust check that the intake gate cannot. This procedure only resolves; it
writes nothing.

1. Run the Local Override trust check first. If it fails, return a rejection.
2. Normalize the slug: lowercase it and remove one trailing `.git` (once, never repeatedly). It must then match
   `^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$` (at most 100 characters on each side of the `/`). A repository name that starts with a dot, such as
   `org/.github`, cannot match and so cannot be mapped.
3. Look it up as an exact key of `linear.repositories`. Two map keys that normalize to the same value are a
   configuration error and reject. An unknown slug is rejected, never guessed or defaulted.
4. The operation in use (`linear.read` or `linear.write`) must be `verified` with a non-null `verified_at`,
   otherwise reject.
5. Pick the environment. For a write delegated by `plugin-integration-intake` under a hash-bound approval (a batch
   or an update) it comes **only** from the `environment` your own `wmgt_batch_hash.py chunk` call printed (`test`
   selects `test_team_id`, `production` selects `production_team_id`), never from the caller's message, the
   original payload's `test_run` or a delegation argument. For intake's resolution request made before a
   submission file exists, use the `test_run` intake passes: the team choice is provisional and is re-derived from
   the printed `environment` at write time, but a rejection is final (return it). A query writes nothing, so its
   resolution is final. For a single-record create delegated with no file, use the `test_run` intake passes and
   name the environment and team in bold in your own per-write preview. Otherwise pick `test_team_id` when the
   caller asked for a test run, else `production_team_id`.
6. Confirm the chosen team is in `team_ids` of the operation in use. An empty list rejects every team. A null team
   ID for the chosen environment is a rejection, never a fallback to the other environment.
7. Return the environment, the team ID and a plain statement of what was verified, or the reason for the rejection.
