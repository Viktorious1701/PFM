# SRS ↔ SDS alignment record

**Date:** 2026-07-30 · **Ruling:** `SRS.md` v2.0.0 is the authoritative baseline. `SDS.md` was edited to match and bumped to **v1.1.0**. `SRS.md` was **not** modified.

This file exists because editing a user-owned document without an audit trail is not acceptable. Every drift found is listed below, whether or not it was changed.

---

## Applied to SDS.md

### A1 — User status vocabulary

| | |
| :-- | :-- |
| **SRS** | §6 US-01-01 Gherkin: *"the System creates a User record with status `PENDING`"*; US-01-03: status is `"PENDING"` or `"ACTIVE"` |
| **SDS (was)** | `PENDING_INVITATION` in §2.4.1, §5.1.1 AC-2, §6.4.1 response payload, §7.1.2 identity model |
| **Ruling** | **`PENDING`** |
| **Rationale** | The SRS Gherkin is what test cases are derived from. A test asserting `status == "PENDING"` against an API returning `PENDING_INVITATION` fails for a purely documentary reason. |
| **Fixed in** | SDS §2.4.1, §5.1.1, §6.4.1, §7.1.2 |

Note: this reverses an earlier session ruling that had chosen `PENDING_INVITATION`. The reversal follows from making the SRS authoritative.

### A2 — `EXPIRED` was modelled on the wrong entity

| | |
| :-- | :-- |
| **SRS** | §6 US-01-02, *"Reject activation when token is expired"*: **"And the account status remains `PENDING`"** |
| **SDS (was)** | §2.4.1 user state machine contained `PENDING_INVITATION → EXPIRED` and `EXPIRED → PENDING_INVITATION` |
| **Ruling** | Remove `EXPIRED` from the **user** state machine. Token expiry is a property of the **invitation**. |
| **Rationale** | Direct contradiction: the SRS requires the account to stay `PENDING` when a token expires, so the user record cannot transition to `EXPIRED`. Modelling it on the user would also make "re-invite" look like a user-state change when it is really a new invitation. |
| **Fixed in** | SDS §2.4.1 (user states reduced to `PENDING → ACTIVE → DEACTIVATED`) and a **new §2.4.2 Invitation State**: `PENDING → ACCEPTED / EXPIRED / SUPERSEDED`. Former §2.4.2 (Budget Monitoring) renumbered to §2.4.3. |

Consequence: `EXPIRED` is **derived** from `expires_at` on every read. No sweeper job exists in the MVP, so no stored value can go stale.

### A3 — NFR id collision *(most consequential)*

| | |
| :-- | :-- |
| **SRS §3** | NFR-01 Performance · NFR-02 **Availability** · NFR-03 **Scalability** · NFR-04 **Security & Token** · NFR-05 Data Integrity & Precision · NFR-06 Privacy |
| **SDS §8.1 (was)** | NFR-01 Performance · NFR-02 **Security** · NFR-03 **Reliability** · NFR-04 **Usability** |
| **Ruling** | Renumber SDS §8.1 to the SRS scheme; add the missing NFR-05/NFR-06 rows; move the "< 3 taps" row to **UXR-01** (SRS §4). |
| **Rationale** | Only NFR-01 agreed. "NFR-02" meant Security in one document and Availability in the other, so *every* citation of an NFR id was ambiguous — including in `constitution.md`, which cites them. This would have silently corrupted traceability. |
| **Fixed in** | SDS §8.1 |

### A4 — Story ID map

| | |
| :-- | :-- |
| **Drift** | SRS numbers stories by feature (`US-01-01`); SDS numbers them by functional area (`UM-US-01`). No mapping existed anywhere. |
| **Ruling** | Add the mapping to the SDS. Cite both ids in every artifact. |
| **Fixed in** | New SDS §1.5.1 |

The map also makes visible that SDS §5 specifies stories the SRS does not have — `UM-US-04`, `UM-US-05`, `DC-US-01`, `DC-US-02` — marked `SDS-only`. These are **not** in MVP scope and must not leak into a Feature-01 slice.

### A5 — SRS feature annotations on SDS §5

Each `### 5.x` heading now names the SRS feature it implements (e.g. `5.2 User Management (UM) — *SRS §6 Feature-01*`). Purely navigational.

### A6 — Backend package layout *(factual correction, not an SRS alignment)*

| | |
| :-- | :-- |
| **SDS (was)** | §4.3.2 showed a tree rooted at `src/` |
| **Actual repo** | `backend/app/` — package `app`, with `backend/migrations/` and `backend/tests/` alongside |
| **Ruling** | Correct the paths; keep the layer names normative. |
| **Rationale** | The SRS says nothing about layout, so this is not an SRS-driven change. Flagged separately so it can be reverted independently of the alignment work. |
| **Fixed in** | SDS §4.3.2 |

---

## Found and deliberately left unchanged

The SRS is silent on each of these, so there is no contradiction — the SDS is elaborating, which is its job.

| Topic | SDS | Why it stands |
| :-- | :-- | :-- |
| Separate `invitations` table | §2.1, §4.3.3 ERD | SRS v2.0.0 has no domain model section at all (v1.2.0 did; v2.0.0 dropped it). Nothing to contradict. |
| `users.role`, ADMIN-only invite/list | §2.2, §5.2 | SRS US-01-01 says *"As an Admin / Account Owner"* and US-01-03 *"As an Admin"* — the SDS gives that actor a name. Consistent. |
| `POST /api/v1/users/invite` | §6.3 | SRS correctly specifies no endpoints. |
| Flat error envelope `{error_code, message, details}` | §6.6 | SRS silent. |
| Password policy: 8+ chars, upper/digit/special | §7.1.5 | Stricter than SRS NFR-04, which only mandates strong hashing. Stricter is fine. |
| `DEACTIVATED` user status | §2.4.1, §7.1.2 | SRS never mentions it, but never forbids it. Retained; no MVP story uses it. |
| `slowapi` rate limiting, `structlog` audit | §7.3, §7.1.10 | SRS FR-08/NFR silent on mechanism. |

## Known deviations from the SDS *(implementation-side, each gets an ADR)*

Recorded here so the drift ledger is complete in one place. These deviate from the **SDS**, not the SRS.

| Deviation | SDS says | Why | ADR |
| :-- | :-- | :-- | :-- |
| Invitation token stored **hashed** (SHA-256) | §4.3.3: `token UK` stored plain | A leaked database must not permit hijacking pending invitations. Behaviour under every AC is identical. | ADR-0003 |
| **SQLite** for local dev | §4.1/§4.5: PostgreSQL | Docker daemon unreachable from this WSL2 setup. PostgreSQL remains the deployment target; one `DATABASE_URL` change. | ADR-0001 |
| **bcrypt directly**, not `passlib` | §7.1.5: "hashed using `passlib` with `argon2` or `bcrypt`" | `passlib` is unmaintained and errors against bcrypt ≥ 4.1. The algorithm required by SRS NFR-04 is unchanged. | ADR-0006 |
| Package `app/` not `src/` | §4.3.2 | Already corrected in the SDS itself (A6). | ADR-0007 |

## Re-verification

```bash
# Only the changelog row should mention the retired term
grep -n "PENDING_INVITATION" SDS.md

# NFR ids must agree across both documents
grep -nE '^\| \*\*NFR-0' SDS.md
grep -nE '^\* \*\*NFR-0' SRS.md
```
