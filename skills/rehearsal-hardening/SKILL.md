---
name: rehearsal-hardening
description: Use when building or changing any recovery path (failover, restore, takeover, migration rollback). Adds a side-effect-free rehearsal mode that runs the real code path on the real standby, makes every failing step explain itself, and lists what only a live drill can prove.
---

# Rehearsal hardening

Audits find logic defects. Environment defects (permissions, mounts, config collisions, missing
tools) only appear when the code runs on the real host with real data. A recovery path that has
never run end to end usually fails the first time it is needed. A rehearsal mode lets it run often
without touching production.

The rehearsal runs on the standby host, never on the primary, and the primary keeps serving traffic
the whole time. It reads the production backups and writes nothing back to them.

## Design the rehearsal mode

The rehearsal runs the same steps as the real recovery, in the same order, with these differences:

| Real recovery | Rehearsal |
|---|---|
| Takes the production identity (DNS, tunnel, lock, fence) | Never touches any of them |
| Reports to the orchestrator | Never reports |
| Uses the production project and volumes | Uses a separate project name and its own volumes |
| Serves traffic | Serves nothing public; checks run locally against the local proxy |
| Keeps running | Tears everything down at the end and fails if anything survives |

The rehearsal also refuses to start while a real recovery is running, and a real recovery can
interrupt a rehearsal at once (signal the rehearsal, wait for its teardown, then proceed).

## No side effects

A rehearsal restores production data and starts production code, so it must not reach the outside
world:

- **Environment allowlist.** Keep only keys the services need to start and to read their own
  restored data: database settings, internal hosts and ports, filesystem paths, boot secrets that
  never leave the host. Every other key, known or unknown, gets an inert value. A denylist fails in
  both directions: it misses outbound keys with unusual names and it blanks keys the services need.
- **Stub background workers.** Bots, pollers and schedulers that consume external queues run as
  health-only stubs, so they cannot take messages meant for production.
- **No egress.** Put the rehearsal services on an internal network without internet access, with
  only the local proxy joined, so targets stored in the database cannot fire either.
- **Archiving off.** Replication and log shipping stay off in a rehearsal.

## Make failures explain themselves

Expect the first rehearsals to fail, and make each failure cost one round:

- capture the stderr of every orchestration command (for example `compose up`) into the run log,
  with a redaction filter for `KEY=VALUE` patterns;
- when a service is not running, log its state, exit code and the last lines of its own log;
- print the time of every step, so regressions in speed are visible;
- never discard output with `>/dev/null 2>&1 || true` in a step that can fail.

## What a rehearsal cannot prove

List the behaviors that are disabled in a rehearsal and prove them in a live drill. Typical items:

- log shipping or replication while the standby is primary;
- the switch of public routing (DNS, tunnel, load balancer);
- the return path (failback) after real writes on the standby;
- recovery after a power cut, where the primary needs a manual unlock.

## Loop

1. Run the rehearsal on the real standby.
2. Read the first failing step and its diagnostics.
3. Give the worker the exact error lines and timings (see `worker-brief-builder`).
4. Install the fix on the standby only and rehearse again. Batch the release once the rehearsal
   passes end to end.

## Checklist

- [ ] The rehearsal shares the real code path and differs only in the table above.
- [ ] The environment scrub is an allowlist with a test for unknown keys.
- [ ] Rehearsal services have no egress.
- [ ] Every failing step logs its own cause.
- [ ] Teardown fails when any container, volume or secret file survives.
- [ ] The live-drill list exists and has an owner.
