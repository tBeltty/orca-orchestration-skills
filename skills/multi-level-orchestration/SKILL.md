---
name: multi-level-orchestration
description: Use when one owner runs delegated work across several repositories, bots or machines in Orca at once. Sets up three levels (a Home Governor bot, one Project Coordinator chat per repository, a repo orchestrator with ephemeral workers), shares a memory-constrained host through a heavy-task mutex, keeps every level's context healthy with clean rotations and keeps continuity state out of public repositories.
---

# Multi-level orchestration

**Tier: Advanced.** Read "Stay in Basic or graduate" first; most work does not need this.

With one repository and one coordinator, the coordinator holds the whole picture. With several
repositories running at once, three things break: the owner gets questions from many chats, heavy
jobs from different projects run together and exhaust the machine, and long-running coordinators
fill their context windows and start forgetting decisions. This skill splits the work into three
levels, each with one job and one channel upward.

Flags change between Orca versions. Check each one against `orca <command> --help` or
`orca agent-context --json` on the active host before relying on it.

## Stay in Basic or graduate

Stay in Basic (one coordinator or one bot, its workers, `worker-brief-builder`,
`delivery-review`, `worker-ops-hygiene`, `bot-items`) while all of these hold:

- the work lives in one repository, or is one bounded task;
- one chat can hold the plan, the open decisions and the worker reports;
- the machine runs the workers' builds and tests without swapping;
- the owner is fine reading one chat and one item list.

Graduate to this skill when any of these becomes true:

- two or more repositories have active workers at the same time;
- several bots, or one bot with several long-lived chats, each need the owner's decisions;
- workers run on more than one machine (`--on <server>`);
- heavy jobs (engine builds, VMs, full test suites, container stacks) from different projects
  compete for one machine's memory;
- a coordinator's context fills before the work ends, so state must survive a rotation.

Graduating costs extra chats, extra messages and a running Home Governor. Go back to Basic when
only one project remains active.

## The three levels

```
Owner
  ▲  items and Needs you (only channel)
Level 1  Home Governor Bot (the bot's Home Chat)
  ▲  status / question mail                 ▼  handoff into a new chat
Level 2  Project Coordinator chat, one per repository
  ▲  worker_done / ask                      ▼  worker-start
Level 3  Repo Orchestrator (high-reasoning model)
  ▲  worker_done / ask                      ▼  worker-start --worktree new-child
         Ephemeral workers (lean models), one child worktree each
```

| Level | Owns | Never does |
|---|---|---|
| 1. Home Governor | Cross-project priorities, the owner channel, host resources, the health of every coordinator | Read or edit project code |
| 2. Project Coordinator | One repository's architecture, its skill set, its orchestrator, its context budget | Talk to the owner directly (unless the owner writes in that chat) |
| 3. Repo Orchestrator | The target branch, briefs, verification, integration, cleanup | Report to anyone but its coordinator |

### Level 1: Home Governor Bot

The Home Chat of one bot (for example a bot named `home`, reached as `bot:home`).

- **Strategy.** Keeps the list of active projects and their order of priority, and starts or
  pauses Project Coordinators.
- **Owner channel.** The only level that writes to the owner, through items (see `bot-items`).
  Coordinators send their questions here; the Governor batches them into Needs you items with
  options and a recommendation, and relays the answers.
- **Host resources.** Grants the heavy-task slot (see "Heavy-task mutex") and triages load.
- **Coordinator health.** Watches each coordinator's activity (`orca bot chats`) and context
  reports, and orders a rotation before a chat saturates.

The Governor reads mail, items, `orca worktree ps` and process listings. It does not open project
files; when it needs a fact about a project, it asks that project's coordinator.

### Level 2: Project Coordinator chats

One chat per active repository, started by the Governor with a charter file:

```bash
orca orchestration send --to bot:home --type handoff --chat new \
  --subject "<repo-name>" --body-file charter-<repo-name>.md
```

`--chat new` starts a chat on the bot titled from `--subject`; the receipt and `orca bot chats`
give its id. The charter names the repository, its goal, its gates, and the reporting rule below.

The coordinator:

1. **Equips the repository with only the skills and CLI gates it needs.** Install skills from
   their source repository (source first, never a copy of a copy) and record the source commit.
   Agents differ in how they load skills: some follow symlinks into a shared folder, others run
   sandboxed and only read real files inside their workspace. Copy the files for those agents
   instead of linking them.
2. **Launches the Repo Orchestrator** on a high-reasoning model, linked to the project's item:

```bash
orca orchestration worker-start --environment local --item <n> \
  --worktree <selector of the main checkout> --agent <agent> --model <model-id> --effort high \
  --task-title "<Name> | <repo>-orch" --spec-file orchestrator-brief.md
```

3. **Steers and audits it** with `orca orchestration send --to dispatch:<id>`,
   `orca orchestration worker-show --dispatch <id>` and `orca orchestration worker-read --dispatch <id>`,
   and reviews each delivery with `delivery-review`.
4. **Reports upward only to the Home Chat**, with `--type status` for progress the Governor needs
   and `--type question` for decisions:

```bash
orca orchestration send --to bot:home --type question --subject "<repo>: <decision>" --body-file q.md
```

Without `--chat`, mail to `bot:home` lands in the Home Chat.

### Level 3: Repo Orchestrator and ephemeral workers

- **Single writer.** Only the orchestrator commits to the target branch. Workers work in child
  worktrees and leave their changes for the orchestrator to inspect, integrate and commit.
- **Isolation.** Each parallel task gets `--worktree new-child --name <name>-<task-id>`, and each
  file has one owner across all running workers (see `worker-brief-builder`).
- **Model calibration.** The orchestrator runs on a high-reasoning model. Mechanical,
  well-specified tasks (scoped edits, renames, checks) go to lean, cheaper models with
  `--model <id> --effort <level>`; ambiguous design work stays with the orchestrator.
- **Gates.** Every integration waits for the deterministic command the brief defined as done, and
  the full gate runs once before each push (see `delivery-review`).
- **Cleanup.** Before reporting, the orchestrator releases every worker, removes every child
  worktree and branch it created and confirms `git status` is clean (see `worker-ops-hygiene`).

## Heavy-task mutex

On a machine with little memory (for example 8 GiB of RAM), two heavy jobs at once push it into
swap, and every agent on it slows down or gets killed. The Governor holds one slot per machine.

1. **Define heavy** in each charter: engine or game builds, VMs, container stacks, full test
   suites, large dependency installs.
2. **Ask before running.** A coordinator asks the Governor for the slot with
   `--type question` and waits for the answer. The orchestrator asks its coordinator the same way
   (`orca orchestration ask`).
3. **Grant on measured headroom.** The Governor grants the slot only when no other heavy job runs
   and swap is under a ceiling the owner chose (for example 2.0 GiB):

```bash
sysctl vm.swapusage          # macOS: swap used
memory_pressure | tail -1    # macOS: free memory percentage
free -m                      # Linux
orca diagnostics memory      # memory of Orca and its managed terminals
```

4. **Release explicitly.** The holder sends a status message when the heavy job ends, and the
   Governor records the release. A slot with no release after its expected duration is checked,
   never assumed free.

### Triage when the machine is overloaded

Sort every large process into one of three groups before acting:

| Group | How to tell | Action |
|---|---|---|
| Active project load | Its working directory is a worktree that `orca worktree ps` lists with a working agent | Leave it, or ask its coordinator to pause after the current step |
| Hung or orphaned | Its worktree has no live worker in `orca orchestration worker-list`, or it outlived its task | Ask the owning coordinator to stop it through `worker-stop`; report what was stopped |
| The owner's applications | Not under any worktree or agent | Never touch. If it is the cause, tell the owner through a Needs you item |

```bash
ps -Ao pid,ppid,rss,%cpu,etime,command | sort -k3 -nr | head -20
lsof -a -d cwd -p <pid>      # working directory of one process
```

## Context hygiene and clean rotation

A coordinator whose context is nearly full drops early decisions and repeats settled questions.
Rotate before that happens.

- **Measure.** Each coordinator reports its context use in its status messages. The level above
  orders a rotation at a threshold the owner chose (for example 60 to 70 percent).
- **Write the state down first.** The leaving coordinator writes a continuity file: goal, decisions
  with dates, open items, running workers with their dispatch ids, what it does not know.
- **Hand over.** The level above starts a fresh chat (`--chat new`) or worker and sends it the file
  with `--body-file`. The new coordinator confirms it can see each running worker
  (`worker-show`) before the old one stops.
- **Close the old chat** once the new one has confirmed.

Continuity state is internal operations. In a **private** repository it can live in a file such as
`docs/CONTINUITY.md`. In a **public** repository it never enters the tree or the history: keep it
in the bot's folder or a private notes repository.

## Several machines

- `orca host list` names the machines this Orca can target; `orca project setups --environment <id>`
  shows where each project is set up.
- Start work on a paired server with `worker-start --on <server> --worktree new-child --repo id:<repoId>`.
  The Run and your mail stay on your own Orca.
- Count the heavy-task slot per machine. Moving a heavy job to a machine with headroom beats
  waiting for the local slot.

## Checklist

- [ ] The graduation criteria hold; otherwise stay in Basic.
- [ ] Only the Home Governor writes to the owner, through items.
- [ ] One Project Coordinator chat per active repository, each with a charter.
- [ ] Each orchestrator is the single writer on its branch; workers use child worktrees with
      one owner per file.
- [ ] Heavy jobs run only with the slot, after a measured swap check, and release it explicitly.
- [ ] Every coordinator reports context use and rotates through a written continuity file.
- [ ] No continuity state, handoff file or session transcript is committed to a public repository.
