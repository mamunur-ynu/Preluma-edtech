# Autopilot Task Queue

Pick the first unblocked P0 item. A task is complete only after its implementation, focused tests, and checkpoint evidence exist. Preserve this file as the durable queue across sessions.

| ID | Priority | State | Task | Acceptance evidence |
|---|---|---|---|---|
| SEC-01 | P0 | DONE | Fail closed on unlabeled RAG chunks; require authorized document owner and prevent cross-owner digest reuse. | 27 focused tests and 116 full tests passed; Ruff, compile, Bandit, pip-audit passed. |
| SEC-02 | P0 | IN PROGRESS | Audit service identity boundaries and active-account checks on AI/course write operations. | Unauthorized and deactivated-account tests; no workflow regression. |
| SEC-03 | P0 | READY | Replace single-process login/reset/AI throttles with an approved shared-store design or document a tested gateway contract. | Two-worker or gateway tests; no rate-limit bypass. |
| DATA-01 | P0 | BLOCKED: staging credentials | Rehearse PostgreSQL migration, importer, restore and RLS deny policies with synthetic staging data. | Executed commands, counts, rollback and deny-test evidence. |
| AUTH-01 | P0 | BLOCKED: gateway/staging | Verify secure HttpOnly session transport behind a supported gateway. | Browser cookie attributes, logout/revocation and role-change tests. |
| DATA-02 | P1 | READY | Audit vector index ↔ metadata consistency and recover from interrupted indexing/deletion. | Crash/restart tests and reconciliation behavior. |
| UI-01 | P1 | READY | Audit dynamic HTML escaping, keyboard navigation and contrast in student/teacher/admin views. | Targeted tests and rendered desktop/mobile evidence. |
| REL-01 | P1 | READY | Rebuild a clean ZIP from the tested PR head and verify a fresh extraction. | Checksum, integrity, tests and excluded-data scan. |

Do not infer that a blocked external task is complete from local SQLite tests. Update state, owner, evidence and next action as work progresses.
