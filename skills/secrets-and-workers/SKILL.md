---
name: secrets-and-workers
description: Use whenever delegated work touches credentials, for example configuring a service, testing an integration, debugging an authentication failure or publishing a repository. Keeps secret values out of briefs, worker sessions, logs, commits and build artifacts, and gets secrets from the owner without the value passing through chat.
---

# Secrets and workers

Briefs, worker transcripts, logs and reports are text that other tools store, index and display. A
secret value that enters any of them counts as exposed. This skill keeps values out of all of them
while the work still gets done.

## Names and locations only

- A brief names a secret by its key and where it lives (`PAYMENTS_API_KEY in the deployment's
  secret store`).
- Workers do not need production secrets. Tests use dummy values or the provider's test-mode
  credentials, defined in the test setup.
- Reports and messages say whether a secret is present and valid (its length, a successful test
  call) and leave the value out.
- Filter any debug step that would print a value (`env`, a configuration dump, verbose HTTP logs)
  before it runs.

## Getting a secret from the owner

Never ask the owner to paste a secret into a chat or a brief. Give them a small script that reads
it with silent input and writes it where it belongs:

```bash
#!/usr/bin/env bash
# usage: save-secret.sh <file> <KEY>
set -euo pipefail
target="${1:?file}"; key="${2:?KEY}"
[[ $key =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "invalid key name" >&2; exit 1; }
umask 077
printf '%s > ' "$key"; IFS= read -r -s value; echo
[ -n "$value" ] || { echo "empty, nothing written" >&2; exit 1; }
tmp="$(mktemp "${target}.XXXXXX")"
grep -v "^${key}=" "$target" 2>/dev/null > "$tmp" || true
esc=${value//"'"/"'\\''"}                 # single-quote the value for sh
printf "%s='%s'\n" "$key" "$esc" >> "$tmp"
mv "$tmp" "$target"; chmod 600 "$target"
echo "saved $key to $target"
```

Around that script:

- the file is shell syntax, sourced by the process that uses it, so the script single-quotes each
  value; a value with spaces, `$`, quotes or `$(...)` stays a literal string;
- the value never appears on a command line, where shell history stores it and the process list
  shows it;
- the file lives outside the repository, or `git check-ignore <file>` confirms it is ignored;
- the file is mode 0600 and owned by the user whose process reads it;
- the script replaces the file, which gives it a new inode. A container that mounts this single
  file keeps the old content until it restarts.

## Least privilege

- One credential per purpose, with the smallest scope the provider allows: read-only where reading
  is enough, one bucket, one zone, one project.
- Document what each credential can do and where it lives, without its value.
- Create short-lived tokens for one-off setup steps, and delete them when the setup is done.

## Keep values out of artifacts

- **Commits.** Read the staged contents before each commit (`git diff --cached`), and run a secret
  scanner in a pre-commit hook and in CI. A secret found in history counts as exposed even after a
  later commit removes it.
- **Logs and error reports.** Redact known key patterns before logs leave the process, and
  configure error-tracking tools to scrub headers and request bodies.
- **Builds.** Browser bundles, mobile apps and published packages are public. Only values meant to
  be public go into them.
- **Containers.** Values passed as container environment are stored in the container's
  configuration on disk and shown by `inspect`. Mount a secret file read-only and load it inside
  the process:

```yaml
services:
  app-a:
    volumes:
      - type: bind
        source: /run/app-a/app.env      # mode 0600, owned by the container's user
        target: /run/secrets/app.env
        read_only: true
    command: ["/bin/sh", "-c", "set -a; . /run/secrets/app.env; set +a; exec ./start.sh"]
```

## Before a repository becomes public

Before the first push to a public repository, and before each later one:

- read every tracked file, and scan every commit in the history with a secret scanner;
- look for more than keys: internal hostnames, IP addresses, local paths, personal email
  addresses, customer names;
- check that `.gitignore` covers environment files, local configuration and scratch output.

## Checklist

- [ ] Briefs, reports and logs carry key names and locations only.
- [ ] Tests use dummy or test-mode credentials.
- [ ] Secrets from the owner arrive through silent input into an ignored, 0600 file.
- [ ] Each credential has the smallest scope and is documented without its value.
- [ ] Staged contents and history are scanned; builds and container metadata carry no secret.
