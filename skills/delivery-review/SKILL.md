---
name: delivery-review
description: Use when a worker reports a task as done in Orca, before its branch is merged. Checks the report against the commits and the scope against the brief, reruns the proof and compares its totals with the report, sorts findings by severity and integrates branches one at a time.
---

# Delivery review

A completion report can name commits, tests and files the branch does not contain. This skill
checks the report against the branch before anything is merged.

## 1. Check the report against the branch

1. Read the commits (`git log <base>..<branch>`) and the full diff (`git diff <base>...<branch>`).
2. Confirm the worktree is clean (`git status --porcelain`). Uncommitted work is not part of the
   delivery.
3. Compare the changed files with the files the brief assigned. A file outside that list is a
   finding, even when the change looks right.
4. Check that every item of the brief has a matching change and a matching test.
5. Look for what the brief did not ask for: new dependencies, disabled or skipped tests, lowered
   coverage thresholds, raised timeouts, debug output, generated files.

## 2. Rerun the proof yourself

Rerun the commands the brief defined as "done", on every platform it
named, from the branch head. When a number differs from the report, find out why before reading
further.

Then read the tests as well as their result:

- does each test fail when the behavior it names breaks? Break the code on purpose and check;
- does any fake decide the result? See `real-environment-proof`.

## 3. Review and sort the findings

Review the diff yourself or with a review agent, and give each finding a severity:

| Severity | Meaning | What happens |
|---|---|---|
| Blocker | Wrong behavior, data loss, a security hole, a broken contract | The branch is not merged |
| Should-fix | A defect with a narrow trigger, a missing test, a misleading name | Fixed in the next round, before the merge |
| Nit | Style, wording, small cleanup | Fixed in the same round as the other findings |

Each finding names the file, the line and the scenario that fails. Send all findings of one review
in a single round (see `worker-brief-builder`).

When a finding shows the contract was wrong, fix the contract first and tell every worker that
implements it.

## 4. Integrate one branch at a time

- Rebase or merge each branch onto the current main branch, one at a time, and rerun the full suite
  after each. Two branches that pass alone can fail together.
- Integrate branches that change a shared interface before the branches that use it.
- Resolve conflicts by reading both sides. Keeping one side wholesale can drop a fix the other
  branch made. After resolving, rerun the tests both branches added.
- Merge only from a green run of the full suite on the integrated result.
- Remove the worker's worktree once its branch is integrated (see `worker-ops-hygiene`).

## Checklist

- [ ] Commits, diff and a clean tree checked; every changed file is in the brief's scope.
- [ ] Nothing unrequested: dependencies, skipped tests, lowered thresholds, generated files.
- [ ] The "done" commands rerun on every named platform; totals match the report.
- [ ] Tests checked to fail when the behavior breaks.
- [ ] Findings sorted by severity; blockers and should-fix items fixed before the merge.
- [ ] Branches integrated one at a time, with the full suite green after each.
