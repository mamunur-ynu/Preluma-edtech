# Current state and exact resume point

Updated: 2026-10-13, Asia/Shanghai

- Base SHA: `b13108a1c1f705ef98d64e755eddec0ca4decfc3` (first published vNEXT review commit).
- Current branch: `feature/preluma-release-hardening`, draft PR: <https://github.com/mamunur-ynu/Preluma-edtech/pull/2>.
- Latest completed tasks: SEC-01 at `1554f3d`, SEC-02 at `577c532`, SEC-04 at `11f8dc6`, and DATA-02 at `71350e2`. SEC-03 local safeguards are at `8ccf25b`, but the distributed task is not complete. Check `git log -1` and `git status` before editing.
- Environment: macOS, Python 3.12.15 in `/private/tmp/preluma-v5-py312.iqqage`. The latest full local suite after SEC-02 was 123 passed in 5.60 s; 10 role/AppTests passed in 4.23 s; Ruff, compileall, Bandit and pip-audit passed. These checks used isolated synthetic SQLite and mocked/offline AI; they do not validate production infrastructure.
- Current issue: DATA-04 shared vector index and SEC-03 PostgreSQL/gateway/provider-spend validation. Shared atomic database counters and provider HTTP-call cap passed synthetic concurrent-worker tests; real PostgreSQL, IP quota and currency budgeting remain open.
- Next three executable tasks: shared vector-index design and synthetic multi-worker tests; provider/token-aware spend policy; UI-01 rendered accessibility review. Re-rank after each completed task and any new PR feedback.
- DATA-03: new quiz attempts store course/lesson provenance. Teacher analytics now report quiz performance only from attributed attempts in authorized courses, not global mastery. An attempt with a uniquely matching enrolled course is inferred; ambiguous attempts stay unattributed. Old records with a lesson ID can be backfilled by migration; other historical records cannot be safely guessed (DATA-05).
- DATA-02: new uploads retain authenticated encrypted extracted text in database metadata. Local restart recovery can rebuild lost/tampered chunks with the same key. SQLite demo creates a private key file; PostgreSQL uploads require `PRELUMA_DOCUMENT_KEY`. Legacy rows without ciphertext still need owner re-upload; losing the key makes encrypted sources unrecoverable. The JSON vector index itself remains process-local and contains passages; DATA-04/SEC-05 track shared storage and key operations.
- REL-01: source ZIPs and SHA-256 checksums are in `/Users/mim/Desktop/Preluma/Deliverables/`; the previous encrypted-recovery archive passed 139 extraction tests, Ruff and both image hashes. Rebuild the ZIP after this shared-limit commit, then choose the file whose short SHA matches `git rev-parse --short HEAD`.
- External blockers: no approved isolated PostgreSQL/Supabase project, secure gateway, real-data export or live paid-provider budget. DATA-01 and AUTH-01 remain BLOCKED. Safe alternative: synthetic SQLite/service tests and local gateway design only.
- Schema: Alembic head `20261013_04`; synthetic SQLite upgrade/downgrade passed locally. Real PostgreSQL migration and backup/restore NOT PERFORMED. Never apply these revisions to production without backup, isolated staging rehearsal and owner approval.
- Deployments: staging NOT PERFORMED; production NOT PERFORMED. No merge to `main`, real-data mutation or paid API calls.
- Images: campus SHA-256 `35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc`; tower SHA-256 `3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2`.

**RESUME FROM HERE:** in `/Users/mim/Desktop/Preluma/Preluma-edtech-vNEXT-git`, run `git status --short --branch`, read `AGENTS.md` and this file, finish shared-limit verification/checkpoint if uncommitted, then tackle DATA-04. Do not claim real PostgreSQL, gateway/IP or currency spend protection without staging evidence.
