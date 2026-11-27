# Example: rehearsal logs

Rehearsal output for a fictional one-off job in app-b: move accounts from a retired plan to its
replacement and email each affected account. Values are placeholders. Every step is timed and
counted, and every failure names its cause.

## A failing run that explains itself

```
rehearsal: target=scratch database restored from the latest backup, egress blocked
rehearsal timing: restore-copy     48s
rehearsal timing: select            2s  accounts=18234 eligible=1207
rehearsal timing: migrate-plans    31s  updated=1180 failed=27
migrate-plans: first failure at account 4821: invalid input value for enum plan_tier: "legacy "
migrate-plans: all 27 failures have a trailing space in plan_tier
rehearsal timing: notify            3s  recorded=1180 sent=0
REHEARSAL FAILED at migrate-plans: 27 accounts not migrated
rehearsal teardown done (scratch database dropped, 0 recorder files left)
```

What this run says without any extra investigation:

1. The selection and the update ran, and the counts show how many accounts each step touched.
2. The 27 failures share one cause: stored plan names with a trailing space. The job needs to
   normalize the value before the lookup.
3. Nothing reached a real inbox: 1,180 messages were recorded and none sent.

## A passing run

```
rehearsal: target=scratch database restored from the latest backup, egress blocked
rehearsal timing: restore-copy     47s
rehearsal timing: select            2s  accounts=18234 eligible=1207
rehearsal timing: migrate-plans    33s  updated=1207 failed=0
rehearsal timing: notify            4s  recorded=1207 sent=0
rehearsal timing: verify            1s  plan counts match the expected table
rehearsal teardown done (scratch database dropped, 0 recorder files left)
total 87s
```

## Live checks kept next to the rehearsal

| Behavior | Why the rehearsal cannot prove it | Live check |
|---|---|---|
| Email delivery | Messages are recorded and never sent | Run a first batch of 50 accounts and check delivery and bounces before the rest |
| Contention with live traffic | The copy has no users | Run outside peak hours and watch lock waits during the first batch |
| Provider rate limits | The recorder has none | Send in batches under the provider's documented limit |
