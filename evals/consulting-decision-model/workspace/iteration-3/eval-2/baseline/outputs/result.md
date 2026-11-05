# Is the `users.email` to `users.contact_email` migration safe?

## The decision model was not consulted

No decision model gave an answer here, so nothing below is its verdict.

`<clone>/README.md` line 28 describes `decision-kit` as a second opinion from a pinned OpenRouter decision model. Reaching it needs the withheld skill and a network call, and this run allows neither. I did not read that plugin, did not call any other model as a stand-in, and did not inspect `<clone>/.claude/hooks/dck-session-context.sh`, which looks like part of the same plugin.

The rest of this file is my own assessment, with no independent check behind it. There is no database, schema or application code for this migration in the clone, so it rests on general database behavior, not on your system.

## My assessment: not safe as described

Don't run this as a single in-place rename against production while the application is live.

- **Main risk: an outage during the deploy.** Code and schema can't change at the same instant. Old code that still uses `email` fails as soon as the rename lands, and new code that uses `contact_email` fails if it runs before the rename. `users.email` is probably used in login, so the failure could block sign-in.
- **Rollback is harder than it looks.** The rename can be reversed, but only together with the code. If the two are out of step, the errors continue during the rollback.
- **Hidden references won't be caught by the rename.** These include raw SQL, reporting queries, ETL and change-data-capture pipelines, read replicas' consumers, stored procedures and other services that share the database. ORM-generated prepared statements and caches can also keep the old name.
- **Locking.** On PostgreSQL the rename itself is fast, but it needs an `ACCESS EXCLUSIVE` lock. If it waits behind a long-running query, it can queue all other traffic on `users` behind it, so set a `lock_timeout`.
- **"No backfill" needs a closer look.** A plain rename keeps the data, so it needs no backfill and that part is fine. But skipping a backfill also means this is the risky all-at-once path. The safer path adds a new column and does need one.

## Safer approach

Use expand and contract:

1. Add `contact_email` as a nullable column.
2. Deploy code that writes to both columns, or use a trigger.
3. Backfill existing rows in batches, then verify that the columns match.
4. Add any index or constraint the old column had. On PostgreSQL, use `CREATE INDEX CONCURRENTLY`, and recreate uniqueness this way too.
5. Switch reads to `contact_email`, and confirm nothing still reads `email`.
6. Drop `email` in a later release.

If you must have no backfill, an in-place rename is only reasonable inside a planned maintenance window with the application stopped. Schema and code should change together, and a tested rollback should be ready.

## Questions for you

I am stopping here. I would ask:

1. Do you want me to get the real decision model's answer? That needs a run with `decision-kit` available and network access, and this result doesn't replace it.
2. Which database engine and version is this?
3. Can you accept a maintenance window, or must the application stay up during the change?
4. Does anything besides this one application read `users.email`, such as other services, reports, pipelines or replicas?
