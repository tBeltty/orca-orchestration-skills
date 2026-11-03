# Example: rehearsal logs

Rehearsal output from a fictional project, as `rehearsal-hardening` asks for it. Values are
placeholders. Every step is timed, and every failure names its cause.

## A failing run that explains itself

```
rehearsal timing: preflight    0s
rehearsal timing: decrypt      0s
rehearsal timing: links        1s
rehearsal timing: files       41s
rehearsal timing: db-restore  33s
rehearsal timing: db-up        9s
compose up: Error response from daemon: ... error mounting "/dev/shm/rehearsal/app-c/.env"
  to rootfs at "/app/.env": make mountpoint "/app/.env": read-only file system
stack diagnose: app-c: State=created, ExitCode=0
stack diagnose: proxy: State=exited, ExitCode=1
stack diagnose: proxy log: [emerg] host not found in upstream "app-c"
REHEARSAL FAILED at stack: these services are not running: app-c proxy
rehearsal teardown done (0 containers, 0 volumes, 0 secret files left)
```

What this run says without any extra investigation:

1. The restore steps completed (files, database restore, database startup, each timed).
2. One bind mount targets a path inside a read-only mount, so its mountpoint cannot be created, and
   the runtime stopped creating the remaining services.
3. The proxy failure follows from the first error and is not a second defect.

## A passing run

```
rehearsal timing: preflight    0s
rehearsal timing: decrypt      0s
rehearsal timing: links        2s
rehearsal timing: files       33s
rehearsal timing: db-restore  28s
rehearsal timing: db-up        9s
rehearsal timing: stack        7s
rehearsal timing: verify       0s
rehearsal hosts: app-a.example.com=200 app-b.example.com=200 app-c.example.com=200
rehearsal teardown done (0 containers, 0 volumes, 0 secret files left)
total 79s
```

## Live-drill list kept next to the rehearsal

| Behavior | Why the rehearsal cannot prove it | Drill |
|---|---|---|
| Log shipping while the standby is primary | Archiving is off in a rehearsal | Cut the primary's network, write a marker row on the standby, fail back, find the row |
| Public routing switch | The rehearsal touches no DNS | Same drill, watch the hostnames move |
| Recovery after a power cut | Needs the real boot path | Unplug the primary, unlock it, watch it rejoin as a replica |
