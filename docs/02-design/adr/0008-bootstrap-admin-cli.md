# ADR-0008: A `create-admin` CLI to break the invite-only bootstrap cycle

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SRS §1.3 Constraints, FR-01 · spec UM-US-01 Assumptions, BR-05 · plan A10

## Context

SRS §1.3 makes open self-registration a deliberate constraint: *"Open self-registration without email verification is disabled to prevent non-existent emails in the database."* Every account therefore arrives by invitation, and SDS §5.2.1 restricts inviting to `ADMIN`.

That is circular. On an empty database there is no `ADMIN`, so nobody can authenticate to send the first invitation, so no account can ever exist. Neither document specifies how the first account appears — a genuine gap, not an oversight to be papered over.

## Decision

A local operator command, outside the HTTP surface entirely:

```bash
uv run python -m app.cli create-admin --email you@example.com --password '…'
```

- Writes one `users` row with `status=ACTIVE`, `role=ADMIN`, and a bcrypt-hashed password.
- **No HTTP route.** Running it requires shell access to the deployment, which is the intended authorisation boundary — there is no network-reachable path to privilege escalation.
- Idempotent-ish: refuses if the address is already `ACTIVE`; promotes an existing `PENDING` row rather than creating a duplicate.
- Also ships `list-users` for operator inspection without a running server.

## Consequences

**Positive**
- The bootstrap problem is solved without weakening the SRS constraint. Registration stays invitation-only for every account after the first.
- Attack surface is unchanged: no new endpoint, no self-service privilege grant.
- Makes UM-US-01 verifiable at all — its Deploy step needs a real ADMIN token.

**Negative**
- **The password is passed as a command-line argument, so it lands in shell history and is briefly visible in the process table.** Acceptable for a local operator action on a family-scale system; a prompt-based entry (`getpass`) would be strictly better and is worth doing if this ever runs on a shared host.
- Bypasses email verification for exactly one account — the intended and necessary exception.
- Anyone with shell access can mint an ADMIN. That is already true of anyone with database access, so it grants no new capability.

## Alternatives rejected

- **Seed an ADMIN in a migration** — reproducible, but embeds a credential in version control, and migrations would need a hard-coded password or an env var read at migrate time.
- **A one-time `/setup` endpoint that self-disables once a user exists** — no shell needed, but adds a network-reachable privilege-granting route whose "only when empty" guard is exactly the kind of check that breaks under a race or a restored-empty database.
- **Environment-variable auto-provisioning on startup** — convenient, but re-creates the ADMIN on every boot and leaves the credential in the process environment for the process's whole life.
- **Relaxing the ADMIN restriction so any authenticated user can invite** — would contradict SDS §5.2.1 and does not help: there is still no first user.
