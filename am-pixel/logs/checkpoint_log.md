# checkpoint_log.md

Append-only log of `/checkpoint` events (CHANGE-028 — implemented 2026-05-10).

Each entry is written to disk at the time of the checkpoint — not retroactively.
Used to detect mid-session drift and provide an auditable alignment record.

---

## Entry schema

```
## [ISO 8601 datetime] | /checkpoint

**Triggered by:** Kyle (manual) | CompactionEvent | SessionBoundary
**Phase:** Phase N — [name]
**Last gate completed:** [gate description + date]
**Next unchecked gate:** [gate description]
**Open blockers:** [None | description]
**Current work:** [what was in progress at checkpoint time]
**Rule governing current work:** Constitution Rule N — [name]
**Constitution confirmed:** yes/no
**Alignment status:** ALIGNED | DRIFT_DETECTED — [what drifted]
```

If `DRIFT_DETECTED`: stop current work, write a new session_log.md entry, correct the drift, then resume.

---

*Initialized 2026-05-10 — CHANGE-028.*
