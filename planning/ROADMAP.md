# Prioritized roadmap

This follows the owner's complete Autopilot master prompt. `TASK_QUEUE.md` contains the executable slices; `RELEASE_GATES.md` defines evidence needed to advance release state.

1. **Security and data integrity:** deny-by-default RAG visibility, live session revalidation, active-account and ownership checks, private uploads, shared abuse controls. Local fixes proceed now; gateway/RLS evidence requires authorized staging.
2. **Staging and migration:** synthetic PostgreSQL Alembic upgrade/rollback, importer reconciliation, private object storage and RLS deny tests. No real student data or production database is in scope.
3. **Core journeys:** preserve and exercise the five mission stages, courses, homework, projects, analytics and admin tools with role-based tests.
4. **Measured learning quality:** explainable recommendations, transparent quiz evidence, cold-start behavior and teacher review. Avoid unsupported efficacy claims.
5. **Tutor quality:** authorized retrieval, citation integrity, prompt-injection tests, deterministic offline evaluation and opt-in live-provider evaluation under an approved budget.
6. **UI and accessibility:** preserve both images and identity; improve keyboard, contrast, loading and responsive behavior with actual rendered evidence.
7. **Reliability and release:** privacy-conscious logs, backups, latency/cost benchmarks, CI, reproducible ZIP and pilot runbooks.
8. **Pilot and future scale:** approval-gated pilot, measured feedback and a decision on FastAPI/Next.js only if product and operational evidence warrants it.

Dependencies matter: a real-student pilot cannot precede secure session transport, data isolation, migration rehearsal and owner approval. Independent local security and test tasks continue while those external gates are blocked.
