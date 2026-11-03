# Orca orchestration skills

Six skills for running delegated software work with [Orca](https://github.com/stablyai/orca): one
coordinating agent that writes briefs, several coding workers that implement them, and review
agents that audit the result before anything reaches a production host.

They come from a multi-day infrastructure build (automatic failover between two hosts, with a
standby that restores production data on demand) that took about sixty worker rounds. Many of those rounds went to worker defects that tests did not catch and to coordination problems:
an open design, two workers on one file, a fake that hid the real behavior. Each skill turns one of
those failures into a procedure and a checklist.

The skills are project-agnostic. They assume a git repository, Orca worktrees and workers, and a
CI pipeline. The host and container skills also assume a container runtime such as Docker Compose.

## The skills

| Skill | Use it when | What it enforces |
|---|---|---|
| [`worker-brief-builder`](skills/worker-brief-builder/SKILL.md) | Before dispatching any worker, and for every follow-up round | A reviewed contract (identity, ownership, concurrency, failure modes), one owner per file, real-environment proof in the brief, "done" defined as a command, batched follow-ups |
| [`real-environment-proof`](skills/real-environment-proof/SKILL.md) | A change touches scripts, containers, host config or external binaries | Tests run inside the CI runner image, generated configs fed to the real binary, an installed-layout test, fakes that reject what the real component rejects |
| [`rehearsal-hardening`](skills/rehearsal-hardening/SKILL.md) | Building or changing a recovery path | A side-effect-free rehearsal mode (allowlisted environment, stubbed workers, no egress), self-explaining failures, a list of what only a live drill proves |
| [`worker-ops-hygiene`](skills/worker-ops-hygiene/SKILL.md) | Coordinating several workers | A watchdog that filters heartbeats, completion checked against commits, stops verified by processes, file times, worktrees and branches, cleanup after integration |
| [`host-change-runbook`](skills/host-change-runbook/SKILL.md) | Installing or changing anything on a production host | Traffic-interrupting steps marked with rollbacks, image architecture, restart policy, scheduler PATH, bind sources, expiring flags |
| [`secrets-in-containers`](skills/secrets-in-containers/SKILL.md) | Moving secrets or data between hosts or into containers | Secrets in RAM and out of container metadata, owner-only files kept owner-only, links shipped as a manifest, paths resolved once |

## How they fit together

```
contract ──► worker-brief-builder ──► worker ──► review ──► real-environment-proof
                                                     │
                       rehearsal-hardening ◄─────────┘  (recovery paths)
                                │
                     host-change-runbook ──► production
     worker-ops-hygiene and secrets-in-containers apply throughout
```

## Examples

The `examples/` directory has filled-in versions for a fictional project:

- [`brief-example.md`](examples/brief-example.md): a first brief and a follow-up round.
- [`contract-example.md`](examples/contract-example.md): a reviewed contract for a standby takeover.
- [`rehearsal-log-example.md`](examples/rehearsal-log-example.md): a failing and a passing rehearsal,
  and the live-drill list.
- [`host-change-plan-example.md`](examples/host-change-plan-example.md): a production change plan
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
