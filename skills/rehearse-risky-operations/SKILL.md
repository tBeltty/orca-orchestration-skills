---
name: rehearse-risky-operations
description: Use before running an operation that is rare, hard to undo or touches shared data or other people, such as a data migration, a backfill, a bulk message, an import, a restore, an account merge or a release. Adds a rehearsal mode that runs the real code path with no side effects, makes every failure explain itself, and lists what only the real run can prove.
---

# Rehearse risky operations

Code review and unit tests find logic defects. Other defects only show when the operation runs end
to end on realistic data: a slow query, a record that breaks a parser, a missing setting, a
permission, two steps in the wrong order. An operation that runs rarely tends to fail the first
time it runs for real. A rehearsal mode lets it run often, with nothing at stake.

## Design the rehearsal mode

The rehearsal runs the same steps as the real operation, in the same order, through the same code.
It differs only in these points:

| Real operation | Rehearsal |
|---|---|
| Writes to the shared data store | Writes to a scratch copy, or to a separate schema, database or namespace |
| Sends email, messages, payments, webhooks or notifications | Records them in a local log and sends nothing |
| Takes shared locks, flags, queues or public names (DNS, cron slots) | Takes none of them |
| Users see the result | Nobody sees the result |
| Keeps its result | Tears everything down at the end, and fails if anything survives |

The rehearsal refuses to start while a real run is in progress, and a real run can stop a rehearsal
at once.

When the rehearsal needs realistic data, use an anonymized copy, or restore a backup into the
isolated environment and delete it at the end. A rehearsal never points at the shared data store.

## No side effects

- **Configuration allowlist.** The rehearsal keeps only the settings it needs to run against its
  own copy (database location, internal settings, paths). Every other key gets an inert value. A
  denylist fails in both directions: it misses outbound keys with unusual names, and it blanks
  keys the operation needs.
- **Recorders for outbound calls.** Email, SMS, push, payment and webhook clients write to a local
  log in rehearsal mode, so the rehearsal can count what it would have sent.
- **Stopped consumers.** Background jobs, queue consumers and schedulers that would pick up the
  rehearsal's writes, or take work meant for production, do not run.
- **No egress.** Run the rehearsal where it cannot reach the internet, so a target stored in the
  data (a webhook URL, an address) cannot fire either.

## Make failures explain themselves

Expect the first rehearsals to fail, and make each failure cost one round:

- capture the stderr of every command the operation runs into the run log, with a redaction filter
  for `KEY=VALUE` pairs, tokens and personal data;
- when a step fails, log the record it stopped on (its id, with personal fields redacted) and the
  last lines of any component it started;
- print counts and the time of every step (records read, records changed, messages recorded), so
  changes in speed or volume are visible;
- never discard output with `>/dev/null 2>&1 || true` in a step that can fail.

## What a rehearsal cannot prove

List the behaviors the rehearsal switches off, and plan a live check for each: a small
first batch, a canary group, a feature flag for internal users, a manual check of the first
records. Typical items:

- real delivery of messages and payments;
- contention with live traffic while the operation runs;
- third-party limits (rate limits, quotas) a sandbox does not enforce;
- the rollback path after real writes.

## Loop

1. Run the rehearsal.
2. Read the first failing step and its diagnostics.
3. Give the worker the exact error lines, counts and timings (see `worker-brief-builder`).
4. Rehearse again after each fix. Run the real operation only after a full rehearsal passes, and
   plan it with `change-plan`.

## Checklist

- [ ] The rehearsal shares the real code path and differs only in the table above.
- [ ] The configuration scrub is an allowlist, with a test for unknown keys.
- [ ] Outbound calls are recorded, consumers are stopped, and there is no egress.
- [ ] Every failing step logs its own cause; counts and timings are printed.
- [ ] Teardown fails when anything survives.
- [ ] The list of live checks exists and has an owner.
