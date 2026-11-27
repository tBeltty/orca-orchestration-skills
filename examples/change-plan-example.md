# Example: a change plan

A plan from `change-plan`, for a fictional change in app-a: replace the `full_name` column of
`users` with `display_name`. Names and numbers are placeholders.

## Steps

| # | Step | Interrupts users or cannot be undone | Rollback |
|---|---|---|---|
| 1 | Release 1: add a nullable `display_name`; the code writes both columns and reads `full_name` | No | Redeploy the previous release; the new column is ignored |
| 2 | Backfill `display_name` from `full_name` in batches of 1,000 rows (rehearsed on a copy: 41 s for 2 million rows) | No | Set `display_name` back to `NULL` |
| 3 | Release 2: the code reads `display_name` and still writes both columns | No | Redeploy release 1 |
| 4 | Watch error tracking for a day | No | n/a |
| 5 | Release 3: the code stops writing `full_name` | No | Redeploy release 2 |
| 6 | Once no release 2 instance runs, back up the `users` table | No | n/a |
| 7 | Drop `full_name` | **Yes**: the column cannot come back without the backup | Restore the column from the step 6 backup, redeploy release 2 |

## Assumptions written down

- CI and production run the same major database version (checked with `SELECT version()` on both).
- Each backfill batch commits in under 100 ms on the copy, so a user write waits at most that long
  for a row lock.
- During each rollout the previous release runs next to the new one. The old code ignores the
  column release 1 adds, and release 2 still writes both columns, so a rollback to release 1 loses
  nothing.
- The deploy pipeline's token expires after 60 minutes, so step 7 runs as its own pipeline run.

## The one command for the owner, if the session cannot run step 7

```bash
./scripts/migrate.sh drop-column users.full_name --confirm
```
