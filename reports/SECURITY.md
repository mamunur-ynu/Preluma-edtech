# Security Assessment

Date: 2026-10-13

## Threat assumptions

Students, teachers and uploaded course documents are untrusted. Attackers may modify browser inputs, filenames, MIME claims, query parameters and API arguments. Environment/Streamlit secrets and the server process are trusted. The current plain Streamlit deployment does not provide a production-grade cookie transport or multi-worker shared rate limiter.

## Findings and disposition

| Risk | Before | Implemented evidence | Residual status |
|---|---|---|---|
| Persistent token in localStorage/query | Enabled by “keep me logged in” | Disabled by default; guarded by `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION`; checkbox disabled otherwise; server tokens remain hashed/revocable | **High production blocker** until external gateway/FastAPI secure cookie transport exists |
| Actor username spoofing in reset/admin services | Actor selected by username string | `issue_reset_code` and `set_active` require actor ID loaded from the server-owned authenticated session; negative role tests | Fixed for current UI contract; future API must resolve actor ID server-side |
| Multiple valid reset codes | Older codes stayed usable | New issuance invalidates all unused codes; one-time/expiry/throttle retained; behavioral test | Fixed |
| Weak upload validation | Extension/size checks; project limit 100 MB | Central basename/extension/size/signature checks; text NUL/encoding checks; atomic private local writes; project limit 25 MB | Malware scanning/private object storage remain staging requirements |
| Stored HTML injection | Dynamic legacy values interpolated in HTML | Escaped profile, project/file and class-dashboard values; reusable components escape by contract tests | Medium: full manual audit of every legacy presentation state remains recommended |
| Cross-course RAG leakage | Retrieval had topic filter only | Public/private/staff/course metadata and pre-return filters; teacher upload/delete ownership checks; negative leakage tests | PostgreSQL/RLS/object-store policy not live-tested |
| Prompt injection in documents | Retrieved text inserted as course material | Source blocks labelled untrusted; system instructs model to ignore commands/role/secret requests; no fabricated citations | Model behavior needs staging red-team/evaluation with live providers |
| Duplicate/stale documents | Metadata lacked digest/version | Content SHA-256, visibility/version columns and digest deduplication; deletion removes vector document | Multi-process index coordination remains unverified |
| AI abuse/cost | Timeout/output cap only | Per-user single-process sliding-window limit plus input cap and provider timeout/token limit | Shared gateway limiter/budget required for multi-worker production |
| Conversation privacy/retention | User/session scoped but no purge policy | User/session query keys, clear API, configurable 30-day purge on write, assistant content cap | Scheduled purge and policy/legal review required at scale |
| Secrets/runtime data packaging | Gitignore existed | Archive scan excludes `.env`, secrets, DB, logs, caches and personal data; dependency audit added | Historical credentials in git history must still be rotated by owner |
| Broad CI/false-green monitoring | Subset lint; keep-alive hid failures | Whole-tree lint, tests, compile, Bandit and pip-audit; keep-alive workflow removed | External monitoring not configured |

## Authorization matrix exercised

| Action | Anonymous | Student | Teacher | Admin |
|---|---:|---:|---:|---:|
| Protected Streamlit routes | deny | own routes | teacher routes | all routes |
| Create course | deny | deny | allow | allow |
| View owned-course analytics | deny | deny | owner/default course | allow |
| Index knowledge document | deny | deny | allow with course ownership | allow |
| Delete knowledge document | deny | deny | uploader only | allow |
| Read conversation | deny | own user/session | own user/session | own user/session unless audited feature added |
| Issue student reset code | deny | deny | allow | allow |
| Issue staff reset code | deny | deny | deny | allow |
| Deactivate account | deny | deny | deny | allow; self/admin targets protected |

The matrix is enforced in tests for the implemented service contracts. Legacy CSV homework/project ownership remains a cutover blocker, not a completed relational authorization claim.

## Executed security checks

- Bandit 1.9.4: PASS; no reported findings after excluding B311 only for non-security quiz/demo randomisation.
- pip-audit 2.10.1: PASS — no known vulnerabilities found for resolved `requirements.txt` and `requirements-dev.txt` environments.
- Secret-pattern scan: no real key/private-key pattern detected in source; placeholder examples only.
- Negative authorization and upload tests: included in the passing Pytest suite.
- Browser console: 0 errors during student, teacher and admin rendered checks.

## Deploy/no-deploy criteria

**Do not deploy for real students** until all of the following are verified:

1. secure browser session transport via a supported external gateway or FastAPI cookie layer;
2. PostgreSQL migration/rollback rehearsal on staging;
3. Supabase/PostgreSQL RLS and private object-storage deny tests;
4. real-data migration reconciliation with ambiguous identities resolved;
5. shared login/reset/AI rate limiting and cost caps;
6. provider prompt-injection/citation evaluation using non-production test keys/data;
7. credential rotation for anything ever published in repository history.

Local classroom/demo use with synthetic data is acceptable when the limitations are visible and the legacy persistent browser bridge stays disabled.
