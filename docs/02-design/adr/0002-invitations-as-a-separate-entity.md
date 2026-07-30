# ADR-0002: Invitations are a separate entity, not columns on `users`

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SDS §2.1, §2.4.2, §4.3.3 · spec UM-US-01 BR-03, BR-08, EC-02, EC-03 · plan A1, A3, A7

## Context

An invitation needs a token, an expiry, and a lifecycle. Two places could hold them: extra columns on the `users` row, or a table of its own. The discarded first attempt chose columns on `users` (see `docs/00-foundation/spike-notes.md`); `SDS.md` §4.3.3's ERD models `USERS ||--o{ INVITATIONS`.

The deciding question came from spec EC-02: re-inviting an address whose invitation expired. With columns on `users`, "re-invite" means overwriting the token in place — the previous attempt vanishes, and there is no way to answer "how many times was this person invited, and by whom?"

## Decision

Two tables.

```
users        id, email UK, password_hash, full_name, status, role, created_at
invitations  id, email (indexed), token_hash UK, expires_at, status,
             invited_by_id FK -> users.id, created_at
```

- Inviting writes **both** rows in **one** transaction (spec BR-08). Neither may exist without the other.
- Re-inviting marks the outstanding invitation `SUPERSEDED` and **inserts a new row** rather than mutating the old one (plan A3).
- `users.email` is unique and normalised. `invitations.email` is **not** unique — it is denormalised so the history reads without a join. Uniqueness belongs to the account, not to the attempt (plan A7).
- Invitation lifecycle is `PENDING → ACCEPTED / EXPIRED / SUPERSEDED` (SDS §2.4.2), separate from the user's `PENDING → ACTIVE → DEACTIVATED`.

## Consequences

**Positive**
- Full invitation history survives, which is what makes `invited_by_id` (spec FR-07) and the audit trail (AC-09) meaningful.
- An expired invitation leaves the user record untouched — required by SRS US-01-02, *"the account status remains PENDING"*. This is the constraint that made a separate entity necessary rather than merely tidy. See `docs/00-foundation/srs-sds-alignment.md` A2.
- A token can be invalidated without touching the account.

**Negative**
- Two inserts and one extra lookup per invitation. Irrelevant at family scale.
- "Is this address invitable?" spans two tables — mitigated by keeping the ACTIVE-account check on `users` alone (spec FR-04).
- Two `PENDING` values now exist with different meanings, one per entity. Handled by never importing both enums into the same scope unqualified.

## Alternatives rejected

- **Columns on `users`** — simpler and what the spike did, but destroys invitation history on every re-invite and contradicts the SDS ERD.
- **One invitation row, mutated on re-invite** — keeps one row per address but still loses history, and makes `SUPERSEDED` meaningless.
