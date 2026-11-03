---
name: host-change-runbook
description: Use before installing or changing anything on a production host (scripts, container definitions, images, scheduled jobs). Separates the steps that interrupt traffic from the ones that do not, and checks the assumptions that break installs: architecture, restart policy, PATH, permissions and expiring flags.
---

# Host change runbook

Installs on a production host break on assumptions nobody wrote down: the image
architecture, a scheduler's PATH, a maintenance flag that expired, a service that does not restart
on its own. This skill turns those assumptions into a written procedure before the window opens.

## Plan the window

1. **List every step and mark the ones that interrupt traffic.** Usually only recreating the
   changed services does. Everything else (copying files, building images, writing secrets,
   loading scheduled jobs that do nothing yet) happens before or after.
2. **Write the rollback for each interrupting step** and keep the previous copies (configuration,
   container definitions, images tagged as `pre-change`).
3. **Keep the interrupting step as one short command.** If the session that runs the install
   cannot run it (a permission policy, a password prompt), hand that one command to the owner.
4. **Open the maintenance window right before the first interrupting step**, and close it as soon
   as the services are verified, so automatic healing runs again.

## Check the assumptions

| Assumption | Check |
|---|---|
| Architecture | Inspect the running image and build the replacement for the same platform (`--platform`). A default build on a different CPU produces a different architecture. |
| Versions | Compare the main binary versions inside the old and new images before the recreate. |
| Restart policy | A service that must wait for others and has no restart policy can stay down after a start-order race. Give stateless services a restart-on-failure policy, or add explicit dependencies. |
| Scheduler PATH | Jobs started by launchd, cron or systemd get a minimal PATH. Set PATH inside each script that calls a tool from a package manager or `/usr/local/bin`. |
| Bind sources | With the short `host:target` volume syntax, a missing bind source is created as a directory, and the next install cannot write a file there. The long `type: bind` syntax fails instead. Create every source before the first start. |
| Permissions | List the uid of each container and the mode each mounted file needs. |
| Expiring flags | A maintenance or pause flag with a time limit needs a refresh step in long procedures. |
| Disk | Freeing space on a build machine can remove tools the build needs (browser binaries, caches of compilers). Check before deleting. |

## Verify

After the interrupting step:

- check every service is running, and read the logs of any that exited;
- request every public hostname through the local proxy and from outside;
- check the health of data services (primary or replica role, replication or archiving working);
- check the scheduled jobs loaded and produced their first log line.

## Checklist

- [ ] Interrupting steps are marked, each with a rollback.
- [ ] Architecture and versions of rebuilt images match the running ones.
- [ ] Restart policies and dependencies cover start-order races.
- [ ] Every scheduled script sets its own PATH.
- [ ] Every bind source exists before the first start.
- [ ] The maintenance window opens right before the first interrupting step, closes after
      verification, and its flag is refreshed before it expires.
- [ ] Verification covers services, hostnames, data health and scheduled jobs.
