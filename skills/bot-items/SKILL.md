---
name: bot-items
description: Use when an Orca bot runs delegated work for its owner. Tracks each deliverable or decision as a bot item, asks the owner through a Needs you item with quick-reply options, marks Waiting only with a named wakeup, links workers to items and closes items when their done-means is met.
---

# Bot items

**Tier: Basic.** One bot, its workers, one owner.

A bot in Orca is an agent with its own folder, chats, memory and connectors. Its owner reads its
items: a list of deliverables and decisions, each with a status. The owner checks items more
often than they read chats, so a decision that lives only in a chat message is easy to miss. This
skill keeps the owner's view current with as few interruptions as possible.

Flags change between Orca versions. Check each one against `orca <command> --help` or
`orca agent-context --json` on the active host before relying on it.

## Know the bots and their chats

| Need | Command |
|---|---|
| The bots on this computer and the address that reaches each | `orca bot list` |
| A bot's chats, with ids for `--chat` | `orca bot chats [--bot <name>] [--all]` |
| Services the bot can use, who it acts as, sign-in state | `orca bot connectors` |
| Ask the owner to connect a service | `orca bot connectors --offer <slack\|linear\|github\|google\|webhook>` |
| The bot's own MCP servers | `orca bot tools`, `orca bot tools add <url\|command> --name <name>`, `orca bot tools rm <name>`, `orca bot tools connect <name>` |
| Propose a new bot to the owner | `orca bot create --offer --name <name> --purpose "<one sentence>"` |
| Change what the bot checks on its own, and how often | `orca bot look-around set [--on\|--off] [--every every-4h\|every-2h\|twice-daily\|mornings] [--focus <text>]` |
| Remove a wrong fact from the bot's memory | `orca bot memory forget --fact "<the fact>"` |
| The workers the bot started | `orca bot work list` |
| Start the next request with a new worker, when the owner says so | `orca bot work forget` |

`bot create --offer` creates nothing until the owner accepts the card. Edit `MEMORY.md` only
through `bot memory forget`: a line removed any other way comes back when the turn ends.

## One item per deliverable or decision

```bash
orca bot item list --link <pr-url>           # check first: update an item that already covers it
orca bot item add --title "<deliverable>" --done-means-file done-means.md --status planned
```

- Write the done-means as something the owner can check: a merged pull request, a command that
  exits 0, a page that loads.
- Link work as it starts. A worker started with `--item <n>` links itself and moves the item to
  In progress:

```bash
orca orchestration worker-start --environment local --item <n> --worktree new-child \
  --name <name>-<task-id> --display-name "<Name> | <task-id>" --task-title "<Name> | <task-id>" \
  --agent <agent> --spec-file brief.md
orca bot item link <n> pr:<owner/repo#123>
```

- Put worker results on the item with `orca bot item comment <n> --text-file result.md
  [--file <path>]`. A comment there stays readable after the chat moves on.

## Needs you: one decision per question

When only the owner can decide, set the item to Needs you with the context, one question and
quick-reply options:

```bash
orca bot item set <n> --status needs-you --comment-file context.md \
  --ask "Merge without the second review?" \
  --option "Merge now | the first review found no blockers" \
  --option "Wait for the second review" \
  --recommended 2
```

- `--comment-file` holds the context: what happened, what each option costs.
- `--ask` is one line under 140 characters that ends in `?`. Repeat `--ask` for several decisions;
  each gets its own `--option` list and waits for its own answer. `--multi` allows several picks.
- `--recommended <n>` marks the option you would choose.
- A new set of questions replaces the unanswered ones. Repeat an earlier question only if it still
  matters.
- The owner's answer arrives as mail and moves the item back to In progress.

Ask only what the brief, the code and sensible defaults cannot settle. A question the bot could
answer itself costs the owner a context switch.

## Waiting: name what wakes you

Waiting is for work none of your workers is doing: CI with no worker on it, a deploy, a
teammate's review, a usage reset. It needs a note that names the wakeup:

```bash
orca bot item set <n> --status waiting --note "CI on #47; a watch-pr wait wakes me"
```

Create the wakeup before you set Waiting (`event-driven-waits` covers `watch-pr` and
`--once` waits). A Waiting item with nothing scheduled to wake it stalls without anyone noticing.

Your own workers, reviewers included, count as In progress. Waiting on the owner is Needs you.

## Closing

- `orca bot item done <n> --note "<what proves the done-means>"` once the done-means is met.
- `orca bot item cancel <n> --reason "<why it was dropped>"` for dropped work.
- Reopen your own closed item with `orca bot item set <n> --status in-progress`.

## Talking to other bots and chats

```bash
orca orchestration send --to bot:<name> --type question --subject "<topic>" --body-file q.md
orca orchestration send --to bot:<name> --type handoff --subject "<topic>" --body-file job.md
orca orchestration send --to bot:<name> --type status --subject "<topic>" --body-file note.md
orca orchestration send --to bot:<name> --item <n> --type status --subject "<topic>" --body-file note.md
```

`question` gets an answer by mail, `handoff` gives the job away, `status` informs with nothing
back. Without `--chat` the mail lands in the bot's Home Chat; `--chat <id>` picks a chat and
`--chat new` starts one titled from `--subject`. The chat you send from refuses its own mail.

## Multiline text

Write long text to a file and pass the file: `--spec-file`, `--body-file`, `--comment-file`,
`--text-file`, `--done-means-file`, `--note-file`, `--reason-file`, or `-` to read stdin. Never
use heredocs (`<<EOF`) or here-strings (`<<<`) in these commands: Orca's own guide warns they can
hang the shell when macOS pipe memory runs low.

## Checklist

- [ ] Every deliverable or decision has one item, with a done-means the owner can check.
- [ ] Workers were started with `--item <n>` or linked with `bot item link`.
- [ ] Each Needs you item has context, one question per decision, options and a recommendation.
- [ ] Each Waiting item names the wait or reminder that will wake the bot, and that wait exists.
- [ ] Results are item comments; finished items are done or canceled with a reason.
