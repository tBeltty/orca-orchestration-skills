# Example: a Basic session

One bot, one repository, two workers on two different models. A fictional bot named `ops` adds
rate limiting to app-a. Names, ids and paths are placeholders. This is the Basic tier: no
hierarchy, no resource mutex, no automations.

## 1. Track the work as an item

```bash
orca bot item list --link https://github.com/acme/app-a/issues/12
orca bot item add --title "Rate limiting for app-a's public API" \
  --done-means-file done-means.md --status planned
```

`done-means.md`:

```
PR merged into main with the limiter on /api/*, 429 responses with Retry-After,
and `npm test` green in the CI image.
```

The item is number 31.

## 2. Choose a route per worker

The coordinator follows `model-routing` and reads what the host offers before naming any model:

```bash
orca account list
orca agent installed
orca orchestration worker-start --help
```

The host has a `claude` account and the `opencode` CLI. app-a's `AGENTS.md` already holds the
owner's routing table: middleware with concurrency rules goes to the high-reasoning route, and
specified configuration and documentation edits go to the fast coding route. OpenCode takes
`--model` without `--effort` and only in an existing worktree, so that worktree is created first.

The fast coding route is new on this host, so a probe worker with a one-line brief runs on it
first. Its receipt names the requested agent and model, and its `worker_done` arrives in under a
minute.

## 3. Two workers, one owner per file

Two briefs from `worker-brief-builder`, saved as files. Worker A owns the middleware, worker B owns
the configuration and documentation, so no file has two owners. Names follow `worker-ops-hygiene`.

```bash
orca orchestration worker-start --environment local --item 31 --worktree new-child \
  --name ana-t1 --display-name "Ana | T1" --task-title "Ana | T1" \
  --agent claude --model <high-reasoning-model-id> --effort high --spec-file brief-t1.md
orca worktree create --name ben-t2
orca worktree set --worktree path:<ben-t2 worktree> --display-name "Ben | T2"
orca orchestration worker-start --environment local --item 31 --worktree path:<ben-t2 worktree> \
  --task-title "Ben | T2" --agent opencode --model <fast-coding-model-id> --spec-file brief-t2.md
```

Both starts link themselves to item 31, which moves to In progress. The coordinator ends its turn.

## 4. Orca wakes the coordinator

Ben's `worker_done` arrives first. The coordinator runs `delivery-review`: commits match the
report, the tree is clean, the "done" command passes. Ana asks a question instead:

```
question (msg_8812): The contract says 100 requests per minute. Per API key or per IP?
```

The contract does not settle it and the owner has not said, so it goes to the owner.

## 5. Needs you, with options

`context.md`:

```
Ana is implementing the limiter. The contract gives 100 requests per minute but not
what is counted. Per key is fairer to shared offices; per IP also stops anonymous floods.
```

```bash
orca bot item set 31 --status needs-you --comment-file context.md \
  --ask "Count the 100 requests per minute per API key or per IP?" \
  --option "Per API key | anonymous calls get a separate, lower limit" \
  --option "Per IP" \
  --recommended 1
```

The owner taps "Per API key". The answer arrives as mail and the item returns to In progress. The
coordinator updates the contract and answers Ana:

```bash
orca orchestration reply --id msg_8812 --body-file answer.md
```

## 6. Review, integrate, close

Ana's delivery passes review. The coordinator integrates both branches one at a time, runs the
full suite after each, links the pull request and comments the result:

```bash
orca bot item link 31 pr:acme/app-a#58
orca bot item comment 31 --text-file result.md
```

After the merge:

```bash
orca worktree rm --worktree path:<ana-t1 worktree> --delete-branch
orca worktree rm --worktree path:<ben-t2 worktree> --delete-branch
orca bot item done 31 --note "PR #58 merged; CI green on the merge commit"
```

## Why this stayed Basic

One repository, one chat that held every decision, a test suite the machine runs without
swapping, and one item the owner had to read. Nothing here needed a second coordinator.
