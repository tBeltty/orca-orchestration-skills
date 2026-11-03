# Example: a host change plan

A plan from `host-change-runbook`, for a fictional host running app-a, app-b and a database in
containers. Placeholders throughout.

## Steps

| # | Step | Interrupts traffic | Rollback |
|---|---|---|---|
| 1 | Copy the reviewed tree to `~/stack/staging/<sha>` | No | Delete the directory |
| 2 | Tag the running database image `db-image:pre-change`; build the new one with `--platform linux/amd64` | No | Retag `pre-change` |
| 3 | Compare `postgres --version` and the backup tool version in both images | No | n/a |
| 4 | Write the new secret files into RAM (`/dev/shm/stack`, 0600, per-uid) | No | Delete them |
| 5 | Install the host scripts and load the scheduled jobs | No | Restore the copies the installer kept |
| 6 | Create every bind source the new definition needs (files, not directories) | No | Delete them |
| 7 | Open the maintenance window | No | Close it |
| 8 | Install the new container definition, keep the old one as `compose.yml.pre-change` | No | Copy it back |
| 9 | Recreate the changed services | **Yes** | Old definition plus `up -d` |
| 10 | Verify services, hostnames, database role and archiving, scheduled job logs | No | n/a |
| 11 | Close the maintenance window | No | n/a |

## Assumptions written down

- The database image must stay amd64 to match the standby, even though this host's CPU is arm64.
- The proxy has `restart: on-failure`; the data services have no restart policy and start through
  the boot gate.
- Every scheduled script sets `PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin`.
- The maintenance flag expires after 120 minutes; step 7 is re-run if step 9 starts later than
  90 minutes after it.

## The one command for the owner, if the session cannot run step 9

```bash
ssh primary-host 'cd ~/stack && docker compose --profile live up -d &&
  docker compose exec proxy nginx -t && docker compose exec proxy nginx -s reload &&
  docker compose ps --format "{{.Service}} {{.Status}}"'
```
