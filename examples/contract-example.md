# Example: a reviewed contract

A contract for a fictional standby takeover, in the shape `worker-brief-builder` asks for. It is
short on purpose: each section answers one question a worker would otherwise guess.

## Components

- **Controller**: decides when the standby takes over. Runs on a schedule, keeps its state in a
  single-writer store.
- **Standby agent**: runs on the standby host, executes a takeover order.
- **Primary**: sends a heartbeat every 30 s.

## Identity

- The "who is primary" marker is an object in shared storage containing `primary-a` or `standby-b`.
- Two writes of the same word produce identical content, so the content (and any content hash) does
  not identify a write. Each write is identified by a per-write value the storage returns (an object version id where
  the storage provides one, plus the upload time), or by a sequence number the writer stores inside
  the object.

## Ownership

| Field | Written by | Read by |
|---|---|---|
| Marker object | Controller (takeover), primary (return) | Everyone |
| Heartbeat time | Controller, on each heartbeat | Controller |
| Episode record | Controller only | Controller |
| Agent state (`idle`, `restoring`, `serving`, `failed`) | Standby agent only | Controller (poll) |

## Concurrency

- Two controller runs may overlap. A takeover starts only through one atomic `claim` operation in
  the store, which re-reads mode, maintenance, heartbeat and episode at claim time.
- The marker is written with a conditional put on the version that was read. A failed condition
  aborts the takeover.

## Failure modes

| Failure | Behavior |
|---|---|
| Controller run dies after the claim, before recording the marker version | The next run adopts the marker if it reads `standby-b` and was uploaded after the claim; otherwise it drops the episode and alerts. |
| Order lost | The controller resends with a fresh nonce; the agent answers 409 for a duplicate of a running episode. |
| Standby reboots while serving | The agent reports `needs-secrets`; the controller resends; the agent resumes without restoring again. |
| Storage unreachable | No decision this run; alert after three runs. |

## Interfaces

- `POST /takeover` on the agent: signed body `{v, episode, ts, nonce, report_url, report_token, bundle}`;
  replies 202, 409 or 401.
- `GET /status` on the agent: `{state, episode, step, since}`.

## Out of scope

- The return path (failback). It has its own contract.
- Public routing changes other than the hostnames listed in the configuration.
