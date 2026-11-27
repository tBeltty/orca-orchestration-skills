---
name: worker-ops-hygiene
description: Use while coordinating coding workers in Orca. Covers starting, watching, stopping and cleaning up workers so each worker is easy to identify, the coordinator is woken by Orca instead of a polling script, every stop is confirmed, and no worktree or process outlives the task.
---

# Worker operations hygiene

**Tier: Basic.**

Orchestrating several workers at once fails in quiet ways: a worker that was stopped keeps
editing, a polling script swallows the mail the coordinator was waiting for, a worktree full of
dependencies stays on disk. This skill lists the checks that prevent each one.

Flags change between Orca versions. Check each one against `orca <command> --help` or
`orca agent-context --json` on the active host before relying on it.

## Starting a worker

- Let `worker-start` create the worker's workspace. `--worktree new-child` nests it under yours;
  `--worktree current` shares yours, which is only safe for one worker or read-only work.
- Pass the brief as a file with `--spec-file` (see "Multiline text" below).
- Add `--environment local` to starts meant for this machine, so an `ORCA_ENVIRONMENT` or pairing
  code in the shell cannot send them elsewhere. Starts on a paired server take `--on <server>`.
- Start each worker on the agent, model and effort its task needs. The choice, the discovery
  commands and the per-agent flag rules are in [`model-routing`](../model-routing/SKILL.md).
- Name every worker `<Name> | <task-id>` (for example `Ana | T3`), the same string as the
  worktree display name, the task title and the worker's terminal tab. Worktree folders and
  branches stay lower case, `<name>-<task-id>`.
- Record the dispatch id the receipt returns. Every later command addresses the worker by it.

```bash
orca orchestration worker-start --environment local --worktree new-child \
  --name ana-t3 --display-name "Ana | T3" --task-title "Ana | T3" \
  --agent <agent> --model <model-id> --effort <level> --spec-file brief.md
```

Some agents (opencode, for example) retitle their own terminal tab. When the receipt gives a
terminal handle, rename the tab right after the start:

```bash
orca terminal rename --terminal <handle from the receipt> --title "Ana | T3"
```

A follow-up sent with `orca orchestration send --to dispatch:<id>` to a finished worker becomes a
new task titled with its `--subject`, so start the subject with the same name
(`Ana | T3 fix: ...`).

Start independent workers together, up to about four at once, then end your turn.

## Watching workers

Orca wakes the coordinator when a worker sends `worker_done`, asks a question, or stops without
reporting. Between those events the coordinator ends its turn and waits.

- **Never poll.** A script that runs a plain `orca orchestration check` marks the mail as handled,
  so the coordinator never sees it and Orca has nothing to wake it with. If a script must watch
  the inbox, it uses `check --peek` (optionally `--peek --wait`) and never `--ack`.
- **Read a worker without its terminal**: `orca orchestration worker-read --dispatch <id>`. Not
  every worker has a terminal.
- **Check a worker's state**: `orca orchestration worker-show --dispatch <id>`. Its
  `observation.agentWait` names a worker parked on a prompt only a person can answer. A waiting
  worker is healthy.
- **Refuse a permission prompt** with `orca orchestration deny --dispatch <id> --prompt <approval id>
  --reason "<why>"`; the worker carries on without that action.
- **Answer a question** with `orca orchestration reply --id <message id> --body-file answer.md`.
- **List everything** with `orca orchestration worker-list --run <run id>`; follow any `next` it
  prints.

Silence, a timeout or `unverifiable` liveness proves nothing. Look at `worker-show` before acting.

## Checking a completion report

Before accepting a worker's `worker_done`, confirm its commits exist and its tree is clean
(`git log <base>..HEAD`, `git status --porcelain`). The full review of the delivery is in
`delivery-review`.

## Stopping a worker for real

| Command | What it does | What it does not prove |
|---|---|---|
| `worker-stop --dispatch <id>` | Fences the dispatch and closes its agent terminal and helpers | On `stop_unknown` (exit 1) the agent may still run |
| `worker-abandon --dispatch <id>` | Fences and settles the assignment, keeping its resources | Nothing about the process; it does no process action |
| `worker-release --dispatch <id>` | Closes the terminal of a settled worker | Only acts on settled workers and owned terminals |

After every stop:

- read the receipt. Claim the worker stopped only on a confirmed result; on `stop_unknown`, check
  `worker-show` and report the uncertainty instead of repeating the stop or starting a second
  worker;
- list the processes whose working directory is the worktree, and check they are gone;
- watch file modification times in the worktree for a minute (`find <wt> -newer <mark>`);
- check `git worktree list` and `git branch` for entries you did not create.

Never close a worker's terminal with a broad `orca terminal close`, and never kill a worker
because of a single signal. Confirm it is idle or finished first.

## Cleaning up

- Finished workers close on their own about two minutes after an accepted `worker_done`. A worker
  started in a new worktree may be kept open by default; release it with `worker-release` when no
  one will use its chat. `worker-keep-open` keeps one the owner wants to read.
- Remove a worktree as soon as its branch is integrated, after confirming it is clean:
  `orca worktree rm --worktree path:<wt> --delete-branch`. Orca keeps a branch it cannot prove
  is merged.
- Delete dependency copies with the worktree.
- Before ending a session, `orca worktree ps` and `orca orchestration worker-list` should show
  only what the owner opened.
- Stop every background job, test run and dev server the session started.

## Multiline text

Write specs, bodies and comments to a file and pass the file (`--spec-file`, `--body-file`,
`--comment-file`, or `-` for stdin). Never use heredocs (`<<EOF`) or here-strings (`<<<`) in Orca
commands: Orca's guide warns they can hang the shell when macOS pipe memory runs low. For commit
messages, use `git commit -F <file>`.

## Checklist

- [ ] Each worker has one worktree, one brief file and a recorded dispatch id.
- [ ] Each worker shows as `<Name> | <task-id>` in its worktree name, task title and terminal tab.
- [ ] No script consumes the coordinator's mail; any watcher uses `check --peek`.
- [ ] Every completion was checked against commits and a clean tree.
- [ ] Every stop was confirmed by its receipt, processes, file times, worktrees and branches.
- [ ] Integrated worktrees are removed, workers released, and every process the session started is
      stopped.
