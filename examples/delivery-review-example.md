# Example: a delivery review

A review from `delivery-review`, for the fictional CSV import in
[`contract-example.md`](contract-example.md). Names, paths and numbers are placeholders.

```
Delivery review: Worker-C, CSV import for app-a (contract: docs/contracts/csv-import.md)
Worktree wt-app-a-import, commits 5d81e02..c47a9b3

Report against the branch
- 4 commits, tree clean.
- 6 changed files in the brief's scope, plus .github/workflows/ci.yml, which raises the
  test timeout from 10 s to 60 s. Outside the scope: finding 2.
- Every contract item has a test except the 20% failure threshold: finding 3.

Proof rerun
- Test suite on macOS: 112 passed. Inside ci-image:node22: 112 passed. Matches the report.
- Real PostgreSQL container, 50,000-row file of dummy contacts: done in 38 s, 0 failed rows.
- Two runners started on the same import: processed_rows reached 100,000 for a
  50,000-row file. Finding 1.
- Upsert broken on purpose: 3 tests fail, as expected.
```

| # | Severity | Where | Scenario |
|---|---|---|---|
| 1 | Blocker | `src/jobs/import.js:88` | The retry path resets `status` to `queued` while the first runner still holds the claim, so a second runner claims the same import |
| 2 | Should-fix | `.github/workflows/ci.yml:31` | A raised timeout outside the scope hides a slow test; revert it and report which test is slow |
| 3 | Should-fix | `test/import.test.js` | No test covers the 20% failure threshold |

Decision: not merged. Round 2 carries the three findings, with the steps of the two-runner run
that reproduced finding 1.
