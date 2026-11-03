---
name: real-environment-proof
description: Use before accepting or pushing a change whose tests could pass on one machine and fail elsewhere. That covers code that runs on another OS or runtime, code that drives an external program or service, and anything that ships as a package, build, image or installed app. Makes tests run where CI runs them, against real dependencies with dummy data, and on the form that ships.
---

# Real-environment proof

A test suite that passes on a laptop shows that the code works on that laptop, with the
fakes the tests chose. The code then runs somewhere else: on a CI runner, on another
operating system, in a browser, inside a package someone installs. This skill closes that gap with
three checks.

"Real" here means the same platform and the same dependencies as the place the code runs. Every
check in this skill runs on a developer machine, a CI runner or a throwaway environment, with dummy
data and dummy credentials. None of them connects to a production system, its data or its secrets.

## 1. Run the suite where CI runs it

Common differences between a developer machine and a CI runner:

- the operating system and its tools (BSD and GNU tools take different flags; `sed -i` needs an
  argument on macOS);
- runtime and tool versions, and global tools present on one side only;
- case-sensitive file systems, line endings, time zone and locale;
- the user (CI often runs as root, which hides permission errors);
- local files that a clean checkout does not have (`.env`, caches, generated code).

Run the suite from a clean archive of the commit, inside the CI image, or on a runner with the CI's
OS when CI uses no image, before every push:

```bash
# Example: run the tests of the current commit inside the CI image.
git archive HEAD | docker run --rm -i -w /src ci-image:latest \
  sh -c 'tar -x && ./scripts/install.sh && ./scripts/test.sh'
```

When a case only applies to one platform, skip it with an explicit "skip (platform only)" line and
count it, so the skip is visible.

## 2. Use real dependencies with dummy data

A fake that behaves differently from the real dependency lets defects through. Exercise the
real thing at least once before a change is accepted:

- the database engine production uses, in a throwaway container. An in-memory engine with other
  SQL rules hides query, type and locking defects;
- a real browser for UI behavior (layout, focus, storage, service workers), at the viewport sizes
  users have;
- the real parser, compiler or command-line tool for every file or command line the code
  generates. In a sandbox a network error is acceptable; a parse error is a defect;
- the provider's sandbox or test mode for third-party APIs, with test credentials;
- the `--help` output of the installed version, for every flag the code passes. Flags move
  between subcommands across versions.

Never use real user data or real credentials in these checks.

## 3. Check the form that ships

Users run a build, a package, an image or an installed app. Check that form:

| Item | Example question |
|---|---|
| Contents | Does the artifact include every file it needs (assets, migrations, templates), and nothing private? |
| Entry point | Does it start from where users start it (the installed command, the published import path, the built page)? |
| Configuration | Which settings does it read at run time, and are they present where it runs? |
| Paths | Does the code find its files relative to where it is installed, with no fallback to the repository? |
| Permissions | Which user runs it, and can that user read and write what it needs? |
| Platform | Does a rebuilt artifact match the one it replaces (CPU architecture, OS, runtime version)? |

Add at least one test that builds the artifact, installs it in a clean place and runs it there.
For example: pack a library and install the tarball in an empty project; build a container image
and run its health check; build a web app and open the result in a browser.

## Fakes

A fake may stand in for a network, a cloud API or a slow service. It must not decide the behavior
the test asserts. Signs of a fake that hides a defect:

- the fake accepts any argument list or any query;
- the fake returns success for a file or record it never checks exists;
- the fake gives distinct identifiers to objects the real service treats as identical (for
  example, content-addressed ETags).

When a real run fails where the suite passed, first ask which fake allowed it, and make that fake
strict.

## Checklist

- [ ] The suite passed inside the CI image, from a clean archive of the commit.
- [ ] Each real dependency the change drives was exercised once with dummy data.
- [ ] The shipped artifact was built, installed in a clean place and run.
- [ ] Every fake involved in the change rejects what the real component rejects.
