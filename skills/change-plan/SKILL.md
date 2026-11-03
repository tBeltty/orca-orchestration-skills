---
name: change-plan
description: Use before a change that users notice while it happens or that is hard to undo, such as a deploy with a migration, a configuration or infrastructure switch, a data operation or a production dependency upgrade. Writes the steps down, marks the ones that interrupt users or cannot be undone, gives each a rollback and checks the assumptions that usually break such changes.
---

# Change plan

Changes to a running system break on assumptions nobody wrote down: a version that differs between
environments, a setting present on a laptop and missing where the code runs, a step that cannot be
undone, a time limit that expires halfway. This skill turns those assumptions into a written plan
before the change starts.

## Write the steps

1. **List every step and mark the ones that interrupt users or cannot be undone.** Usually few do:
   switching traffic, a destructive migration, a restart. Everything else (building, uploading,
   preparing configuration, backward-compatible migrations) happens before or after them.
2. **Write the rollback for each marked step**, and keep what it needs: the previous build or image,
   the previous configuration, a backup taken right before.
3. **Split changes so each step is safe alone.** Add before removing: a new column before the code
   that writes it, the new code before the old column is dropped, a feature flag before the
   behavior it guards.
4. **Keep each marked step one short command.** When the session running the plan lacks permission
   for it, hand that one command to the owner.
5. **Pause scheduled jobs and automatic deploys, or open a maintenance window, right before the
   first marked step**, and
   close it as soon as the change is verified.

## Check the assumptions

| Assumption | Check |
|---|---|
| Versions and platform | Compare runtime, dependency and tool versions between where you tested and where it runs. A rebuilt artifact matches the CPU architecture and OS of the one it replaces. |
| Configuration | Every setting the new version reads exists in the target environment, with the right value. New keys are listed in the plan. |
| Order | Which steps depend on others? A service that starts before its dependency is ready can stay down. Give it a retry or an explicit dependency. |
| Data | How long does each migration take on production-sized data, and does it lock a table users write to? Measure it on a copy. |
| Compatibility | Can the old and new versions run at the same time during the switch (old code with the new schema, old clients with the new API)? |
| Scheduled jobs | A scheduler (cron, launchd, systemd, a CI schedule) starts jobs with a minimal environment. Check PATH and settings inside each job. |
| Permissions | Which user runs each process, and can it read what the new version needs? |
| Time limits | Tokens, maintenance flags, locks and sessions that can expire during a long change need a refresh step. |
| Capacity | Disk, memory, quotas and rate limits during the change. Freeing space can delete tools a build needs; check before deleting. |

## Verify

After the marked steps:

- check every service runs, and read the logs of any that stopped;
- exercise the main user paths from outside, the way users reach them;
- check data health: migrations recorded, counts as expected, background jobs running;
- watch error tracking and logs for new errors in the following minutes;
- check that scheduled jobs produce their next run.

## Checklist

- [ ] Marked steps are listed, each with a rollback and the copies it needs.
- [ ] The change is split so the old and new versions can overlap.
- [ ] Versions, platform and configuration were compared between test and target.
- [ ] Migration time and locks were measured on production-sized data.
- [ ] Every time limit is refreshed before it expires.
- [ ] Verification covers services, user paths, data, errors and scheduled jobs.
