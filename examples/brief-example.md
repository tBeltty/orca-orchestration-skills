# Example: a worker brief

A filled-in brief from `worker-brief-builder`, for a fictional project. Names, paths and commands are
placeholders.

```
Worker name: Worker-B. Add a /healthz endpoint to app-a that reports the database
connection state. Worktree: wt-app-a-health, based on 3f2c1aa.

Read first: docs/contracts/healthz.md (the reviewed contract), CONTRIBUTING.md,
services/app-a/src/server.js, services/app-a/src/db.js.

You own ONLY: services/app-a/src/routes/healthz.js, services/app-a/src/server.js,
services/app-a/test/healthz.test.js. Do not edit anything else. No push, no version
bump, nothing against a production or staging host.

Build:
1. GET /healthz answers 200 {"db":"ok"} when a `SELECT 1` succeeds within 500 ms,
   and 503 {"db":"down"} otherwise. Acceptance: both cases covered by tests.
2. The route never logs the connection string.

Prove it on the real thing:
- npm test inside the CI image: `docker run --rm -v "$PWD":/src -w /src ci-image:node22 npm test`
- One run against a real PostgreSQL container with dummy credentials, stopping the
  database mid-run: the endpoint must switch to 503 within 1 s.
A shim may replace the network. It may never decide whether the query succeeded.

Done means: `npm test` exits 0 on macOS and inside ci-image:node22, and the real-database
run shows 200 then 503.
Report: the commits, the test totals on both platforms, and anything in the contract you think is wrong.
```

## A follow-up round for the same task

```
Worker name: Worker-B. Round 2 on wt-app-a-health (HEAD 9ab01c2). The review found no
blockers, two should-fix items and one nit; close all three in this round.

1. should-fix, src/routes/healthz.js:18: the timeout timer is never cleared, so a slow
   but successful query still runs the 503 path after 500 ms. Clear it on success; add a test with a
   400 ms query.
2. should-fix, test/healthz.test.js:40: the fake pool resolves any query string, so the
   test does not prove `SELECT 1` is what runs. Make the fake reject other SQL.
3. nit: the 503 body should match the contract's casing ("down").

Done means: the same two commands as round 1 exit 0.
```
