---
name: secrets-in-containers
description: Use when a change moves secrets or data between hosts or into containers (failover bundles, staged code trees, env files, backups). Keeps secrets out of on-disk container metadata, keeps owner-only files owner-only, ships links as a validated manifest and avoids check-then-use races on paths.
---

# Secrets and data in containers

Containers make it easy to leak secrets to disk and to widen permissions without noticing. This
skill covers four risks: secrets written to container metadata, owner-only files made readable,
links inside archives, and paths swapped between check and use.

## Keep secrets out of container metadata

Values passed through `env_file` or `environment` are stored in the container's on-disk
configuration (for example Docker's `config.v2.json`) for the container's whole life, where
anyone who can run `docker inspect` or read the runtime's data directory can read them.

- Put secret files in a RAM-backed directory (`/dev/shm/<app>`), mode 0700 for the directory and
  0600 for each file, owned by the uid that reads it.
- Mount the file read-only into the container and source it inside the command, so the values
  never reach the runtime's configuration:

```yaml
services:
  app-a:
    env_file: !reset []        # drop any env_file inherited from a base file
    volumes:
      - type: bind
        source: /dev/shm/app-a/app.env
        target: /run/secrets/app.env
        read_only: true
    command: ["/bin/sh", "-c", "set -a; . /run/secrets/app.env; set +a; exec node server.js"]
```

- In any file the orchestration tool interpolates, escape shell variables (`$$name`), or the tool
  substitutes an empty string at start.
- A file mounted inside a read-only parent needs an existing mountpoint. Create an empty, mode
  0600, root-owned placeholder at that path in the staged tree, never with content.

## Never widen owner-only files

- Extract archives preserving the source's modes, then strip set-id bits.
- Normalize modes only for the code and config trees that containers must read: directories 0755,
  files 0644, or 0755 when the owner had execute. A file the source kept owner-only stays
  owner-only.
- Restored data (databases, uploads, user files) keeps its restored modes, or becomes 0600 when the
  mode was lost.
- The sender refuses, or excludes and logs, any owner-only file outside the allowlisted trees. It
  catches leftovers such as old scripts with embedded credentials.

## Ship links as a manifest

- Archives never carry symlinks or hardlinks; the receiver refuses link, device and fifo members.
- Release links (for example `<app>/current -> releases/<id>`) travel as a manifest of
  `name -> relative target`. The receiver recreates each link after checking the target is relative,
  has no `..`, and stays inside its own app directory.

## Resolve a path once

A path checked on one side and opened later can be swapped in between (a symlink placed after the
check).

- Mount the parent directory the other side cannot rename, and pass the path relative to it.
- Open the file inside the namespace that uses it, with no-follow semantics for every component.
- Refuse paths containing characters the mount syntax treats as separators (`,`, `:`, `=`,
  newline).

## Checklist

- [ ] No secret passes through `env_file` or `environment`; every secret file lives in RAM with
      per-uid ownership.
- [ ] Shell variables in interpolated files are escaped.
- [ ] Read-only mount targets have empty placeholders.
- [ ] Owner-only files stay owner-only; only code and config trees are normalized.
- [ ] Links travel as a validated manifest.
- [ ] Every path is resolved once, inside the namespace that opens it.
