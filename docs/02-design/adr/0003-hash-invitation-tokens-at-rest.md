# ADR-0003: Store only the hash of an invitation token

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SDS §4.3.3 *(deviation)*, §7.4 · SRS NFR-04 · spec UM-US-01 AC-06, AC-08, BR-07 · constitution SEC-02, SEC-03 · plan A2

## Context

`SDS.md` §4.3.3 models `invitations.token` as a plain unique string. An invitation token is a **bearer credential**: whoever holds it can claim an identity and set its password (UM-US-02). Storing it in plaintext means a database dump — a backup on a laptop, a leaked snapshot, an over-broad read grant — hands an attacker every outstanding invitation.

Password hashing is uncontroversial (SRS NFR-04 mandates bcrypt/argon2). An invitation token grants the same power as knowing the password, for 24 hours, so the same reasoning applies.

## Decision

Persist `sha256(raw_token)` hex in `invitations.token_hash` (`String(64)`, unique). The raw token exists in exactly two places: the generated response inside the request that creates it, and the email body. It is never stored, logged, or returned.

- Generation: `secrets.token_urlsafe(32)` → 256 bits, over SRS NFR-04's 128-bit floor (SEC-02).
- Lookup: hash the incoming token, then a single indexed equality query. No table scan.
- **SHA-256, not bcrypt** — the input is already 256 bits of uniform randomness, so key-stretching buys nothing against brute force and would only slow lookup. Stretching exists to compensate for low-entropy human passwords.

## Consequences

**Positive**
- A leaked database cannot be used to hijack pending invitations.
- Makes spec AC-08 ("the inviting ADMIN never learns the token") enforceable by construction rather than by remembering to omit a field.
- Token comparison stays a single indexed lookup — no performance cost.

**Negative**
- **The raw token is unrecoverable.** No "show me the link again" feature is possible; recovery is re-invitation (spec EC-02), which rotates the token anyway. Acceptable, and arguably correct.
- Deviates from the SDS ERD. Behaviour under every acceptance criterion is identical, so no AC or test changes — only the column name and type. Recorded in `docs/00-foundation/srs-sds-alignment.md`.
- Debugging an invitation means reading the email, not the database. This is the point.

## Alternatives rejected

- **Plain token as the SDS specifies** — simplest, and readable in the DB for debugging, but that readability *is* the vulnerability.
- **HMAC with a server secret** — protects against a DB leak *and* offline verification, but adds key management and rotation for no gain here: the token is already high-entropy and short-lived.
- **bcrypt the token** — resists nothing extra given 256 bits of entropy, and would force a scan-and-compare instead of an indexed lookup, since bcrypt salts every hash differently.
