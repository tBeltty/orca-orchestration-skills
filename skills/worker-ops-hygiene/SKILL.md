---
name: worker-ops-hygiene
description: Use while coordinating coding workers in Orca. Covers starting, watching, stopping and cleaning up workers so a stopped worker really stops, a watchdog never misreads a heartbeat, and no worktree or process outlives the task.
---

# Worker operations hygiene

Orchestrating several workers at once fails in quiet ways: a worker that was stopped keeps
editing, a watchdog acts on the wrong message, a worktree full of dependencies stays on disk. This
skill lists the checks that prevent each one.

## Starting a worker

- Create one worktree per task from a known commit, and record that commit in the brief.
- Copy or clone dependencies once, with copy-on-write where the file system supports it, to save
  disk and install time.
- Start the worker with a brief from `worker-brief-builder`. Record the dispatch id it returns.

```bash
# Example shape; adjust to the Orca version in use.
orca worktree create --name task-a --repo id:<repo-id> --base-branch main --setup skip
orca orchestration worker-start --run <run-id> --spec "$(cat brief.md)" \
  --task-title "Worker (task-a)" --worktree path:<worktree> --agent <agent>
```

## Watching workers

Run one background watchdog per batch of workers. It exits, and so wakes the coordinator, on any
of three events:

1. an orchestration message that is **not** a heartbeat (filter heartbeats in every format the
   orchestrator uses, with or without brackets, any case);
2. a terminal waiting on a permission prompt;
3. no file change in any watched worktree for a long window (long test runs change no files, so
   use 40 minutes or more).

When the watchdog fires, read the message it printed before acting.

## Checking a completion report

When a worker reports completion:

1. read its commits (`git log <base>..HEAD`);
2. confirm the tree is clean (`git status --porcelain`);
3. check that nothing outside its owned files changed;
4. only then stop its process.

## Stopping a worker for real

The orchestrator can mark a worker stopped while its agent session keeps running inside a shared
agent server. A stopped session can keep writing to its worktree, and to other worktrees through
absolute paths, and can create branches.

After every stop:

- list the processes whose working directory is the worktree, and check they are gone;
- watch file modification times in the worktree for a minute (`find <wt> -newer <mark>`);
- check `git worktree list` and `git branch` for entries you did not create;
- if anything still writes, stop the shared agent server (in the Orca versions observed, the orchestrator starts it
  again) and check again. Restarting it also drops the sessions of other workers, so do it between rounds when
  possible.

Never kill a worker because of a single watchdog signal. Confirm the worker is idle or finished
first.

## Cleaning up

- Remove a worktree as soon as its branch is integrated, after confirming it is clean.
- Branches may stay; worktrees and their dependency copies should not.
- Before ending a session, list worktrees and leave only those the owner opened.
- Stop every background watcher, test run and dev server the session started.

## Checklist

- [ ] Each worker has one worktree, one brief and a recorded dispatch id.
- [ ] A watchdog filters heartbeats and permission prompts and uses a long idle window.
- [ ] Every completion was checked against commits and a clean tree before the stop.
- [ ] Every stop was verified by processes, file times, worktrees and branches.
- [ ] Integrated worktrees are removed.
