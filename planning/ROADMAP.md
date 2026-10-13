# Prioritized roadmap

This follows the owner's complete Autopilot master prompt. `TASK_QUEUE.md` contains the executable slices; `RELEASE_GATES.md` defines evidence needed to advance release state.

1. **Security and data integrity:** deny-by-default RAG visibility, live session revalidation, active-account and ownership checks, private uploads, shared abuse controls. Local fixes proceed now; gateway/RLS evidence requires authorized staging.
2. **Staging and migration:** synthetic PostgreSQL Alembic upgrade/rollback, importer reconciliation, private object storage and RLS deny tests. No real student data or production database is in scope.
3. **Core journeys:** preserve and exercise the five mission stages, courses, homework, projects, analytics and admin tools with role-based tests.
4. **Measured learning quality:** explainable recommendations, transparent quiz evidence, cold-start behavior and teacher review. Avoid unsupported efficacy claims.
5. **Tutor quality:** authorized retrieval, citation integrity, prompt-injection tests, deterministic offline evaluation and opt-in live-provider evaluation under an approved budget.
6. **UI and accessibility:** preserve both images and identity; improve keyboard, contrast, loading and responsive behavior with actual rendered evidence.
7. **Reliability and release:** privacy-conscious logs, backups, latency/cost benchmarks, CI, reproducible ZIP and pilot runbooks.
8. **Typed service boundary:** add a minimal read-only FastAPI entry point and versioned schemas over existing service functions; prove authentication, authorization, error behavior and OpenAPI contracts without changing Streamlit routes.
9. **Learning intelligence:** define append-only learning events, attributable course/lesson evidence, course-specific mastery projections and explainable recommendation rules. Migrate with synthetic data first; never infer ambiguous historical provenance.
10. **Secure web migration:** implement a same-origin Next.js/React/TypeScript BFF with server-held credentials, HttpOnly/Secure/SameSite cookies, CSRF controls and revocation tests; add frontend slices only against verified API contracts. Keep Streamlit as a functional parallel UI until parity and rollback are demonstrated.
11. **Measured background processing and retrieval:** use Redis/workers for durable event processing when justified by measured load or latency; consider pgvector only after retrieval evaluation. Do not introduce distributed infrastructure preemptively.
12. **Pilot:** owner-approved staging and pilot gates, measured feedback, backups, rollback and explicit release authorization.

ADR-011 fixes the long-term architecture as an AI-native modular monolith with event-driven background processing and learning intelligence. Dependencies matter: a real-student pilot cannot precede secure session transport, data isolation, migration rehearsal and owner approval. Independent local security, API and test tasks continue while external gates are blocked.
