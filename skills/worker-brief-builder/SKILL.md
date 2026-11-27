---
name: worker-brief-builder
description: Use before dispatching any coding worker through Orca. Builds a self-contained brief that names the files the worker owns, the reviewed contract it implements, the real-environment proof it must produce and the exact command that defines "done". Use it for every new task and every follow-up round.
---

# Worker brief builder

**Tier: Basic.**

A worker only knows what the brief tells it. Many wasted rounds in a delegated build come from
briefs that leave the design open, assign a file to two workers or accept a test whose fake decides
the result. This skill turns a task into a brief that avoids those three failures.

## Before writing the brief

1. **Freeze the design.** If the task implements an interface between components, write the
   contract first and get it reviewed (see "Contract review" below). Never dispatch against a
   design that may still change.
2. **Check file ownership.** List the files the task will change. If a running worker owns any of
   them, wait for it, or split the task so each file has one owner. Two workers editing the same
   file produce a hand merge, and hand merges can reintroduce defects that one branch had fixed.
3. **Stop and verify any previous worker on the same task.** A design change sent while the old
   worker still runs leaves two implementations writing to one tree. See `worker-ops-hygiene`.
4. **Pick the agent and model for the task.** Take the route from the project's routing table,
   or build one with [`model-routing`](../model-routing/SKILL.md). Keep design, contract and
   review work on a high-reasoning model. A brief for a fast or lean model spells out the exact
   files, commands and acceptance conditions.

## Contract review

A contract is ready for a worker when it states all of these:

| Item | Question it answers |
|---|---|
| Identity | How is each object, record or message told apart from an older one with the same content? |
| Ownership | Which component writes each field, and which only reads it? |
| Concurrency | What happens when two runs, ticks or requests overlap? What is compared and set atomically? |
| Failure modes | What does the system do after a crash mid-step, a lost message, a restart, a timeout? |
| Interfaces | Exact endpoints, payloads, file paths and exit codes on both sides. |
| Out of scope | What the worker must not touch. |

Send the contract to a reviewer (a review agent or a second worker) and fix what it finds before
any implementation brief goes out.

## Brief template

```
Worker name: <name>. <One-line goal>. Worktree: <worktree>, based on <commit>.
Read first: <the contract>, <the project rules file>, <the files to change>.
You own ONLY: <paths>. Do not edit anything else. No push, no version bump,
nothing against a production or staging environment.

Build:
1. <item, with the acceptance condition>
2. ...

Prove it on the real thing:
- <the exact command that runs the tests on the CI platform>
- <the real-dependency check for each database, browser, tool or API this change drives>
- <the shipped-form check: build or pack the artifact, install it in a clean place, run it>
A fake may replace a network or an external service. It may never model the behavior a test claims
to prove.

Done means: <command> exits 0 on <platform A> AND <platform B>, and <observable result>.
Report: the commits, the test totals on both platforms, anything in the contract you think is wrong
(report it, do not change it silently).
```

## Dispatching the brief

Save the brief to a file and pass it with `--spec-file`. Shell quoting breaks long briefs, and
heredocs (`<<EOF`) can hang the shell. Name the worker as `worker-ops-hygiene` describes, and add
`--item <n>` when a bot tracks the task as an item (see `bot-items`):

```bash
orca orchestration worker-start --environment local --worktree new-child \
  --name <name>-<task-id> --display-name "<Name> | <task-id>" --task-title "<Name> | <task-id>" \
  --agent <agent> --model <model-id> --effort <level> --spec-file brief.md [--item <n>]
```

Then end your turn. Orca wakes you when the worker reports or asks.

## Follow-up rounds

- Label each finding blocker, should-fix or nit, and send every finding of one review in a single
  round, blockers first.
- Quote the reviewer's evidence (file, line, scenario) in the brief so the worker does not
  rediscover it.
- When a real run failed, paste the exact error lines (redacted) and the step timings. If the run
  left no error output, first ask for the logging that `rehearse-risky-operations` describes.
- Send the round to the same worker with
  `orca orchestration send --to dispatch:<id> --subject "<Name> | <task-id> round 2" --body-file round2.md`.
  A finished worker gets it as a follow-up task in the same workspace.

## Checklist before dispatch

- [ ] Contract reviewed, or the task needs none.
- [ ] Every file in scope has exactly one owner.
- [ ] Previous workers on this task are stopped and verified stopped.
- [ ] The agent, model and effort follow the routing policy in `model-routing`, and the brief goes
      out as a `--spec-file`.
- [ ] The brief names the CI platform command, the real-dependency checks and the
      shipped-form check.
- [ ] "Done" is a command with an exit code, on every platform the code runs on.
- [ ] The brief forbids pushes, version bumps and changes to shared environments unless the task
      is exactly that.
