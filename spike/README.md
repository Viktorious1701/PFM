# spike/ — discarded first attempt

**Status: reference only. Do not edit. Do not import from here.**

This is an implementation-first attempt at Feature-01 written on 2026-07-30: about
1,750 lines across 26 modules, produced with **no** spec, design, or test-plan
artifacts, and never executed as a test suite. It was rejected for that reason —
the AIF-SDLC cycle exists precisely to prevent this.

It is kept because parts of it are informative, and because deleting evidence of a
process failure is dishonest. See `docs/00-foundation/spike-notes.md` for what it
proved and what it got wrong.

## Superseded by design decisions

Anything reused from here must be re-derived from the approved `spec.md` and
`plan.md` for its story. In particular the spike **contradicts `SDS.md`**:

| Spike did | SDS requires |
| :-- | :-- |
| invitation token columns on `users` | separate `invitations` table (§2.1, §4.3.3) |
| `PENDING` / `ACTIVE` | `PENDING_INVITATION` / `ACTIVE` / `DEACTIVATED` (§2.4.1) |
| no `role`, any caller may invite | `users.role`; invite and list are ADMIN-only (§5.2) |
| nested `{"error": {"code": …}}` | flat `{"error_code", "message", "details"}` (§6.6) |
| `POST /users/invitations` | `POST /users/invite` (§6.3) |
| activation returned the user object | `{"status": "SUCCESS", "message": …}` (§6.4.2) |
| password: min length only | 8+ chars, 1 upper, 1 digit, 1 special (§7.1.5) |
| no rate limiting, no audit logging | `slowapi` (§7.3), structured audit logs (§7.1.10) |
