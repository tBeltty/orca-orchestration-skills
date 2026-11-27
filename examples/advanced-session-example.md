# Example: an Advanced session

Three repositories at once on one laptop with 8 GiB of RAM, set up with
`multi-level-orchestration`. Names, ids and numbers are placeholders: a Home Governor bot reached
as `bot:home`, and three fictional repositories `app-a`, `app-b` and `game-c`.

## Why this graduated

- three repositories have active workers at the same time;
- `game-c` builds a game engine, a heavy job, and `app-b` runs a container stack for its full
  suite; together they push the laptop into swap;
- the owner wants one list of decisions, not three chats asking questions.

## Level 1 opens a coordinator chat per repository

The Governor writes one charter per repository and starts a chat for each:

```bash
orca orchestration send --to bot:home --type handoff --chat new --subject "app-a" --body-file charter-app-a.md
orca orchestration send --to bot:home --type handoff --chat new --subject "app-b" --body-file charter-app-b.md
orca orchestration send --to bot:home --type handoff --chat new --subject "game-c" --body-file charter-game-c.md
```

`charter-game-c.md`:

```
Repository: game-c (private). Goal: item 44, the save-system rewrite.
You are the Project Coordinator for game-c. Report only to the Home Chat
(orca orchestration send --to bot:home ...). Never write to the owner.
Heavy jobs here: engine builds and the full test suite. Ask the Home Chat for the
heavy slot before each one and send a status message when it ends.
Report your context use in every status message. Rotate when the Home Chat asks.
Skills to install from their source: worker-brief-builder, delivery-review,
worker-ops-hygiene, real-environment-proof. The orchestrator agent runs sandboxed,
so copy the skill folders instead of symlinking them; record the source commit.
```

## Level 2 starts each repository's orchestrator

From the `game-c` chat:

```bash
orca orchestration worker-start --environment local --item 44 \
  --worktree path:<game-c main checkout> --agent <agent> --model <high-reasoning-model-id> --effort high \
  --task-title "Orchestrator | game-c" --spec-file orchestrator-brief.md
```

The orchestrator brief says: single writer on `main`, child worktrees for parallel work, lean
models for mechanical tasks, the full gate once before each push, every child worktree and worker
cleaned up before `worker_done`.

## Level 3 fans out

The `game-c` orchestrator splits the rewrite into three tasks with disjoint files and starts them
in child worktrees, two of them on a lean model:

```bash
orca orchestration worker-start --environment local --worktree new-child \
  --name eva-t1 --display-name "Eva | T1" --task-title "Eva | T1" \
  --agent <agent> --model <lean-model-id> --effort medium --spec-file brief-t1.md
```

Workers leave their changes in their child worktrees. The orchestrator reviews each with
`delivery-review` and commits the result to `main` itself.

## The heavy-task mutex in action

The `game-c` orchestrator needs an engine build. It asks its coordinator
(`orca orchestration ask --question "Heavy slot for an engine build, about 12 minutes?"`), and the
coordinator asks the Governor:

```bash
orca orchestration send --to bot:home --type question \
  --subject "game-c: heavy slot for an engine build (~12 min)" --body-file slot-request.md
```

The Governor measures before answering:

```
$ sysctl vm.swapusage
vm.swapusage: total = 3072.00M  used = 2410.25M  free = 661.75M  (encrypted)
```

Swap is over the 2.0 GiB ceiling and `app-b` holds the slot for its container suite. The Governor
answers "queued behind app-b" and grants the slot when `app-b` sends its release:

```bash
orca orchestration send --to bot:home --type status \
  --subject "app-b: heavy slot released" --body-file release.md
```

## One decision reaches the owner

The `app-a` coordinator needs a decision on a breaking API change. It sends a question to the Home
Chat. The Governor holds it until the `game-c` coordinator's question arrives too, then raises one
item with both decisions:

```bash
orca bot item set 40 --status needs-you --comment-file decisions.md \
  --ask "Ship app-a's v2 API with a breaking change to /users?" \
  --option "Ship with a 30-day deprecation header" --option "Hold for a v3 branch" --recommended 1 \
  --ask "Let game-c drop support for save files older than 1.2?" \
  --option "Drop them" --option "Keep a converter" --recommended 2
```

## A rotation before saturation

The `app-b` coordinator reports 68 percent context use, over the 65 percent threshold. The
Governor asks it to write its continuity file, starts a fresh chat with that file as the charter,
and closes the old chat once the new coordinator confirms it sees the running orchestrator with
`orca orchestration worker-show --dispatch <id>`.

`app-b` is a public repository, so the continuity file lives in the bot's folder and never in the
repository. In the private `game-c` repository the same file could live in `docs/CONTINUITY.md`.

## Waiting on CI without polling

When `app-a`'s pull request is open, its coordinator saves a wait instead of checking CI:

```bash
orca automations watch-pr acme/app-a#61 --bot home --for 1h \
  --prompt "If CI failed, send the failing checks to the app-a orchestrator; otherwise report ready to merge"
```

## Back to Basic

When `app-b` and `game-c` finish, only `app-a` remains. The Governor closes the other two chats,
and `app-a` continues as a Basic setup: one coordinator, its workers, one item.
