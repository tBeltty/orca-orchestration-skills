---
name: real-environment-proof
description: Use when a change touches shell scripts, containers, host configuration or any external binary, and before pushing anything a CI runner will test. Makes tests run where CI runs them, exercises real binaries with dummy data, and checks the installed layout, so platform and layout defects fail locally before the pipeline runs.
---

# Real-environment proof

A test suite that passes on a laptop shows only that the code works on that laptop. When the code
runs on another operating system, inside a container, or through a tool the test replaces with a fake, the local result says
little about production. This skill closes that gap with three checks.

## 1. Run the suite where CI runs it

Developer machines and CI runners differ in ways that break shell code:

- BSD and GNU tools take different flags (`stat -f` is a file-system query on GNU and a format
  flag on BSD; `sed -i` needs an argument on BSD).
- Tools present on one side may be missing on the other (`lockf`, `flock`, `sqlite3`, `timeout`).
- CI often runs as root, which changes permission checks.

Run the suite inside the real runner image before every push that touches scripts:

```bash
# Example: run a repository's shell harness inside a CI container, from a clean archive.
git archive HEAD | ssh ci-host 'docker exec -i ci-runner sh -c "
  rm -rf /tmp/check && mkdir -p /tmp/check && tar -x -C /tmp/check &&
  cd /tmp/check && bash tests/run-tests.sh; rc=\$?; rm -rf /tmp/check; exit \$rc"'
```

Check that no CI job is running in that container first. When a case is truly specific to one
platform, skip it with an explicit "skip (platform only)" line and count it, so the skip is
visible.

## 2. Exercise real binaries with dummy data

When a change generates input for an external program (a config file, a command line, a mount
list), feed that input to the real program before any rehearsal:

- Parse the generated config with the real binary in a throwaway container
  (`docker run --rm --network none ...`), with dummy credentials. A network error is acceptable;
  a parse error is a defect.
- Reproduce a mount layout with the real container runtime: a bind target under a read-only parent,
  a missing bind source, a file mounted where a directory exists.
- Check flags against the real binary's help output (`<tool> <subcommand> --help`). Flags move
  between subcommands across versions.

Never mount real secrets into these checks.

## 3. Check the installed layout

Write down, for every host the change installs on:

| Item | Example question |
|---|---|
| Path | Where does each script and each helper land? Does the code look for a helper next to itself, or in a fixed directory? |
| User | Which uid runs each process or container? Can that uid read every file it needs? |
| Mode | Which files must stay owner-only? Which must be readable by a container user? |
| PATH | Does a scheduler (launchd, cron, systemd) start the job with a minimal PATH that lacks the tools it calls? |
| Architecture | Does a rebuilt image match the architecture of the image it replaces? |

Add at least one test that copies the scripts into their installed layout (no repository-relative
fallbacks) and runs them from there.

## Shims and fakes

A fake may stand in for a network, a cloud API or a slow service. It must not decide the behavior
the test asserts. Signs of a fake that hides a defect:

- the fake accepts any argument list;
- the fake returns success for a file it never checks exists;
- the fake gives distinct identifiers to objects the real service treats as identical
  (for example, content-addressed ETags).

When a real run fails where the suite passed, first ask which fake allowed it, and make that fake
strict.

## Checklist

- [ ] The suite passed inside the CI runner image, from a clean archive of the commit.
- [ ] Each generated config or command line was fed to the real binary.
- [ ] The installed layout has a test that runs without repository fallbacks.
- [ ] Every fake involved in the change rejects what the real component rejects.
