# Orca orchestration skills

Seven skills for running delegated software work with [Orca](https://github.com/stablyai/orca): one
coordinating agent that writes briefs, several coding workers that implement them, and review
agents that check each delivery before it is merged or shipped.

They came out of a project that ran for more than 48 hours straight, in which a coordinating agent
on Opus 5.5 (high effort) orchestrated coding workers on DeepSeek 4.1 (high effort).

## The skills

| Skill | Use it when | What it enforces |
|---|---|---|
| [`worker-brief-builder`](skills/worker-brief-builder/SKILL.md) | Before dispatching any worker, and for every follow-up round | A reviewed contract (identity, ownership, concurrency, failure modes), one owner per file, real-environment proof in the brief, "done" defined as a command, batched follow-ups |
| [`real-environment-proof`](skills/real-environment-proof/SKILL.md) | A change could pass on one machine and fail elsewhere | Tests run inside the CI image, real dependencies exercised with dummy data, the shipped artifact installed and run, fakes that reject what the real component rejects |
| [`delivery-review`](skills/delivery-review/SKILL.md) | A worker reports a task as done | The report checked against the commits, scope checked against the brief, the proof rerun, findings sorted by severity, branches integrated one at a time |
| [`worker-ops-hygiene`](skills/worker-ops-hygiene/SKILL.md) | Coordinating several workers | A watchdog that filters heartbeats, stops verified by processes, file times, worktrees and branches, cleanup after integration |
| [`rehearse-risky-operations`](skills/rehearse-risky-operations/SKILL.md) | Before a migration, backfill, bulk message, import, restore or release | A rehearsal mode on the real code path with no side effects, self-explaining failures, a list of what only the real run proves |
| [`change-plan`](skills/change-plan/SKILL.md) | Before a change users notice or one that is hard to undo | Marked steps with rollbacks, changes split so old and new versions overlap, written assumptions, verification |
| [`secrets-and-workers`](skills/secrets-and-workers/SKILL.md) | Delegated work touches credentials | Key names in briefs and logs, test-mode credentials, silent input for the owner's secrets, least privilege, scans before publishing |

## How they fit together

```
contract ──► worker-brief-builder ──► worker ──► delivery-review ──► merge
                                                      │
                           real-environment-proof ◄───┘  (in the brief and in the review)

risky operation ──► rehearse-risky-operations ──► change-plan ──► live system

worker-ops-hygiene and secrets-and-workers apply throughout
```

## Examples

The `examples/` directory has filled-in versions for a fictional project:

- [`brief-example.md`](examples/brief-example.md): a first brief and a follow-up round.
- [`contract-example.md`](examples/contract-example.md): a reviewed contract for a CSV import.
- [`delivery-review-example.md`](examples/delivery-review-example.md): the review of that import's
  delivery, with a blocker found by rerunning the proof.
- [`rehearsal-log-example.md`](examples/rehearsal-log-example.md): a failing and a passing
  rehearsal of a plan migration that emails users, and the list of live checks.
- [`change-plan-example.md`](examples/change-plan-example.md): a column replaced in three releases,
  with rollbacks and written assumptions.

## Installing

Each skill is a directory with a `SKILL.md` file (YAML front matter with `name` and `description`,
then the instructions). Copy or symlink the directories into the skills folder your agent reads,
for example a project's `.claude/skills/` or a shared `.agents/skills/`:

```bash
git clone https://github.com/tBeltty/orca-orchestration-skills.git
ln -s "$PWD/orca-orchestration-skills/skills/"* /path/to/project/.claude/skills/
```

Command examples that call `orca` show the shape of the CLI; check the flags against the Orca
version you run.

## Contributing

Issues and pull requests are welcome. A good addition names the failure it prevents, the check that
catches it and an example with placeholder data.

## License

MIT. See [LICENSE](LICENSE).
