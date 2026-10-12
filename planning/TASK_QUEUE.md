# Actionable task queue

Statuses are `TODO`, `IN_PROGRESS`, `BLOCKED` or `DONE`. Select the highest-priority unblocked task by risk and user impact, then effort. Update the evidence and commit reference when closing a task.

| ID | Risk / impact | Status | Dependency | Exact scope and acceptance | Evidence / commit |
|---|---|---|---|---|---|
| SEC-01 | Critical / document privacy | DONE | None | Unlabelled RAG chunks denied; curated topics explicitly public; uploader required; duplicate scope includes owner/visibility. Negative tests and full gates. | 27 focused, 116 full tests, Ruff/Bandit/audit; `1554f3d` |
| SEC-02 | Critical / live account access | DONE | None | Revalidate a server session on every Streamlit rerun; deactivation, password reset and role change immediately affect open tabs. Enforce active-account and enrollment checks in affected services. Negative and AppTests pass. | 123 full tests, 10 AppTests, Ruff/Bandit/audit; current PR commit |
| SEC-04 | Critical / cross-user analytics | IN_PROGRESS | SEC-02 | Require an authenticated actor and course ownership for teacher analytics and student drill-down; deny student/other-teacher access. Preserve teacher dashboard behavior. | Pending |
| SEC-03 | High / abuse and cost | TODO | Design decision | Define and test shared multi-worker login/reset/AI rate limits and provider budget behavior; keep local fallback. | Pending |
| DATA-01 | Critical / migration integrity | BLOCKED | Approved isolated PostgreSQL staging | Test Alembic upgrade/downgrade, backup/restore, importer reconciliation and RLS deny policies on synthetic data. | Owner must provide isolated staging access/quota. |
| AUTH-01 | Critical / browser token privacy | BLOCKED | Approved secure gateway/staging | Demonstrate HttpOnly, Secure, SameSite cookies, CSRF handling, rotation and revocation in a rendered browser. | Owner must provide or approve isolated gateway/staging. |
| DATA-02 | High / index integrity | TODO | SEC-01 | Reconcile vector index and document metadata after interrupted indexing/deletion; test restart/recovery. | Pending |
| UI-01 | Medium / usability | TODO | SEC-02 | Audit dynamic HTML, keyboard focus and contrast across role views; verify rendered responsive pages. | Pending |
| REL-01 | Medium / reproducibility | TODO | Next milestone | Build a clean ZIP from tested PR head, extract and rerun gates; publish checksum and milestone report. | Pending |

External blockers do not stop independent local work. Do not mark a task `DONE` from a plan or an inherited report alone.
