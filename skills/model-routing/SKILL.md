---
name: model-routing
description: Use when deciding which agent, model and reasoning effort each Orca worker runs on, including in a setup with a single orchestrator. Discovers the accounts, agents and model flags the host supports before any dispatch, helps the owner write a routing policy that fits their cost, latency and quality priorities, records it in the project's rules file and checks each route with one probe worker before a batch.
---

# Model routing

**Tier: Basic.**

The orchestrator does not have to run every task on its own model. `orca orchestration
worker-start` takes `--agent`, `--model` and `--effort` for each worker, so a contract review can
run on a high-reasoning model while a scoped test fix runs on a fast coding model, inside the same
run. This skill picks those three values per task from facts on the host, never from memory.

Model ids, agent ids and flag rules change between Orca releases and between hosts. Read them from
`orca agent-context --json` and `orca <command> --help` on the host that will run the workers.

## 1. Discover what the host can run

Run these before choosing anything:

```bash
orca account list
orca agent installed
orca orchestration worker-start --help
```

- `orca account list` shows the accounts configured on this host for each provider (`claude`,
  `codex`, `opencode`, `devin`, `antigravity`). `system` is the provider's own sign-in outside
  Orca. Filter one provider with `orca account list --agent <agent>`.
- `orca agent installed` lists the agent CLIs Orca can start here. Each `id` it prints is a value
  `--agent` accepts.
- `orca orchestration worker-start --help` gives the model rules for the version you run. Read its
  notes for each agent you plan to use, for example:
  - `--effort` requires `--model`, and neither combines with `--terminal`.
  - OpenCode takes `--model` without `--effort`, and only in an existing worktree with a verified
    CLI on the execution host and an available model.
  - Pi takes a `provider/id` model and maps `--effort` to its `--thinking` level.
  - Agents without model support in Orca launch with the model from their own configuration.

To change which account new launches use on this host, run
`orca account select --agent <agent> --account <id>` with an id from `orca account list`. Never
put a provider credential in a brief, a spec file or a command line.

## 2. Let the owner set the policy

Each owner weighs cost, latency and quality differently, so the routing policy is theirs. The
coordinator's job is to propose one from what it found: the accounts and agents on the host, the
tasks in the plan, and how much review each task needs.

The roles below are examples to adapt. They are not rules:

| Role | Typical tasks | Example route |
|---|---|---|
| Orchestration and review | Plans, architecture, contracts, `delivery-review` of a delivery | A high-reasoning model at `high` effort, such as a `claude` high-reasoning tier |
| Scoped implementation | Specified edits, tests, refactors, operational docs | A fast coding worker, such as `opencode` with a fast coding model, or a lighter coding model at `medium` effort |
| Visual and design work | UI mockups, layouts, image-heavy tasks | A model with strong visual or multimodal skills, at the effort the task needs |
| Small lookups | Read-only checks, one-file questions | The coordinator itself, or a lightweight fast model, without a heavy worker |

A proposal to the owner names each role, the agent and model chosen for it, the effort, the reason
(cost, speed or quality) and what happens when that route is unavailable. The owner approves or
edits it before the first batch.

## 3. Record the policy in the project's rules file

Write the approved table into the file the project's agents already read (`AGENTS.md`,
`CLAUDE.md` or the equivalent), so every coordinator session routes the same way:

```markdown
## Model routing

| Role | Agent | Model | Effort |
|---|---|---|---|
| Orchestration and review | claude | <high-reasoning-model-id> | high |
| Scoped implementation | opencode | <fast-coding-model-id> | (none) |
| Small lookups | coordinator | (its own) | (none) |

Fallback: when a route fails its probe, use the orchestration route and say so in the report.
Checked on this host with `orca account list` and `orca agent installed`.
```

Keep the ids exactly as the host reports them. Update the table when an account, agent or model
changes, and record why in the commit message.

## 4. Dispatch with the chosen route

Pass the route on every start. Name the worker as `worker-ops-hygiene` describes and build the
brief with `worker-brief-builder`. A brief for a fast or lighter model spells out the exact files,
commands and acceptance conditions.

A model that takes an effort level:

```bash
orca orchestration worker-start --environment local --worktree new-child \
  --name ana-t3 --display-name "Ana | T3" --task-title "Ana | T3" \
  --agent claude --model <model-id> --effort high --spec-file brief-t3.md
```

OpenCode with a model needs an existing worktree, so create it first and start the worker in it:

```bash
orca worktree create --name ben-t4
orca worktree set --worktree path:<ben-t4 worktree> --display-name "Ben | T4"
orca orchestration worker-start --environment local --worktree path:<ben-t4 worktree> \
  --task-title "Ben | T4" --agent opencode --model <fast-coding-model-id> --spec-file brief-t4.md
```

`--retry-of` carries `--model` and `--effort` over to the retry when neither is passed and the
retry target supports them; pass them again when the retry should use a different route.

## 5. Probe a route before a batch

A wrong model id or an account that cannot launch shows up only at start time. Before you start
several workers on a new route:

1. Start one worker on that route with a small brief that ends in `worker_done`, for example
   "Read README.md and report its first heading".
2. Read the receipt and `orca orchestration worker-show --dispatch <id>`. Continue only when the
   worker started on the requested agent and model and reported.
3. Start the batch, up to about four workers at once, then end your turn.

When the probe fails, do not guess another id. Read the error, rerun the discovery commands in
section 1, and bring the corrected route to the owner when it changes cost or quality.

## Checklist

- [ ] `orca account list`, `orca agent installed` and the `worker-start --help` notes were read on
      the host that runs the workers.
- [ ] The owner approved the routing table, and it is recorded in the project's rules file.
- [ ] Every start passes the agent, model and effort from that table, with `--effort` only where
      the agent accepts it.
- [ ] Each new route passed one probe worker before a batch.
- [ ] No credential appears in a brief, spec file, command or rules file.
