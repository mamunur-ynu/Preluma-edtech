# Autopilot Worklog

## 2026-10-13 — continuation start

- Confirmed draft PR #2 points to `feature/preluma-release-hardening` at `b13108a1c1f705ef98d64e755eddec0ca4decfc3`; both prior GitHub CI runs passed.
- Created a persistent Git checkout at `/Users/mim/Desktop/Preluma/Preluma-edtech-vNEXT-git`.
- Searched the workspace for the newly mentioned Autopilot master prompt. It was not attached or present under the searched Downloads/Preluma paths; requested it from the owner asynchronously and proceeded with the existing security assessment.
- Found a concrete RAG authorization gap: documents lacking visibility metadata default to public, and document indexing can omit the uploader ID. SEC-01 tracks the fix.

Append dated entries with commands/results and commit SHA after every completed task. Never rewrite failed checks into passes.

## 2026-10-13 — SEC-01

- Curated topic documents now carry explicit public visibility. Old curated index entries with missing visibility are reindexed on start, while unlabelled uploads fail closed.
- `index_document` now requires an active teacher/admin uploader before parsing a file. Digest reuse is scoped to the same uploader, course and visibility.
- Added negative tests for unlabelled chunks, anonymous upload and cross-owner/private duplicate bytes.
- Executed: `pytest -q tests/test_security_hardening.py tests/test_ai.py` → 27 passed; full `pytest -q` → 116 passed in 4.80 s; Ruff, compileall, Bandit and pip-audit → PASS; both image hashes unchanged.
