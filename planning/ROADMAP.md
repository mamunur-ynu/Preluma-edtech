# Prioritized roadmap

This follows the owner's complete Autopilot master prompt. `TASK_QUEUE.md` contains the executable slices; `RELEASE_GATES.md` defines evidence needed to advance release state.

1. **Security and data isolation first:** retain completed RAG/session/teacher-scope fixes. Finish SEC-03 shared quota and spend operations, DATA-04 index coordination and SEC-05 key recovery; test cross-user/course denial. Gateway/IP and real-worker claims remain blocked without isolated staging.
2. **PostgreSQL migration and resilience gate:** with owner-approved isolated synthetic staging, validate Alembic upgrade/downgrade, RLS, backup/restore, importer reconciliation, concurrent writers and outage behavior. Never run against real student or production data.
3. **Core journeys:** preserve and exercise the five mission stages, courses, homework, projects, analytics and admin tools with role-based tests.
4. **Measured learning quality:** explainable recommendations, transparent quiz evidence, cold-start behavior and teacher review. Avoid unsupported efficacy claims.
5. **Tutor quality:** authorized retrieval, citation integrity, prompt-injection tests, deterministic offline evaluation and opt-in live-provider evaluation under an approved budget.
6. **UI and accessibility:** preserve both images and identity; improve keyboard, contrast, loading and responsive behavior with actual rendered evidence.
7. **Reliability and release:** privacy-conscious logs, backups, latency/cost benchmarks, CI, reproducible ZIP and pilot runbooks.
8. **Typed service boundary (local slices done):** retain FastAPI read-only catalog/user and enrolled-course shadow recommendation contracts, plus the narrow private auth exception. Test authorization and OpenAPI contracts before each new endpoint; defer learning mutations until secure gateway evidence.
9. **Learning Event Engine and mastery (local slice in progress):** retain transactional, privacy-minimized quiz evidence and course-scoped topic/concept projections. Add corrections, lifecycle and evaluated rules before activating the explainable planner; never infer ambiguous history.
10. **Transactional outbox (opt-in local replay done):** verify atomic acknowledgement/replay and failures locally; then, only after PostgreSQL staging approval, test multi-worker locking, poison-event policy, retry/outage, telemetry and latency before enabling any background scheduler or Redis.
11. **Secure Next.js migration (read-only slice in progress):** extend typed BFF and authenticated views after contract/CSRF tests. Prove HTTPS cookies and gateway behavior on staging; preserve every Streamlit journey until parity and rollback evidence.
12. **Measured retrieval:** consider pgvector only if retrieval evaluations outperform the existing shared relational index. Do not introduce distributed infrastructure preemptively.
13. **Pilot:** owner-approved staging and pilot gates, measured feedback, backups, rollback and explicit release authorization.

ADR-011 and ADR-013 fix the long-term architecture as an AI-native modular monolith with event-driven background processing and learning intelligence. Dependencies matter: a real-student pilot cannot precede secure session transport, data isolation, migration rehearsal and owner approval. Independent local security, API and test tasks continue while external gates are blocked.
