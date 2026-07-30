# ADR-0006: Use `bcrypt` directly rather than `passlib`

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SDS §7.1.5 *(deviation)* · SRS NFR-04 · constitution SEC-01, VL-04

## Context

`SDS.md` §7.1.5 says passwords are "hashed using `passlib` with `argon2` or `bcrypt`". `passlib` 1.7.4 (2020) is the last release and is effectively unmaintained. It reads `bcrypt.__about__.__version__` to detect the backend — an attribute removed in `bcrypt` 4.1 — which emits a spurious error trace on every process start and breaks outright on some versions.

`bcrypt` 5.0.0 resolved in this project's lockfile.

## Decision

Call `bcrypt` directly, wrapped in `app/core/security.py`:

```python
def hash_password(plain: str) -> str
def verify_password(plain: str, hashed: str | None) -> bool
```

**The algorithm required by SRS NFR-04 is unchanged** — this is a library choice, not a cryptographic one. SDS §7.1.5 explicitly permits bcrypt.

Two details the wrapper must own:

1. **The 72-byte ceiling.** bcrypt silently ignores input past 72 **bytes** — not characters. A long passphrase, or ~24 emoji, would have its tail quietly discarded, so the user's real password is shorter than they believe. Rejected at the schema layer instead (constitution VL-04).
2. **Timing equalisation.** `verify_password` accepts `hashed: str | None` and, when it is `None`, still performs one bcrypt round against a throwaway hash computed at import. Without this, login against a non-existent account returns measurably faster than against a real one, leaking which addresses are registered. The dummy hash is *computed*, never hard-coded — an unparseable constant would raise, skip the round, and silently reintroduce the leak.

## Consequences

**Positive** — no unmaintained dependency, no startup warnings, one less abstraction layer. The 72-byte trap and the timing leak are handled explicitly rather than assumed away.

**Negative**
- No `passlib` algorithm-agnostic interface, so migrating to argon2 later means writing a small dispatch on the stored prefix (`$2b$` vs `$argon2`). bcrypt hashes are self-describing, so this is straightforward but not free.
- The import-time bcrypt round costs ~50–100 ms of process startup. Irrelevant for a server; noticeable if the CLI is invoked in a tight loop.

## Alternatives rejected

- **`passlib[bcrypt]` as the SDS names it** — literal compliance at the cost of a broken dependency.
- **`argon2-cffi` directly** — a stronger KDF and permitted by both documents; deferred only because `bcrypt` was already resolved and verified working. Switching later is contained to `security.py` plus a rehash-on-login path.
- **`pwdlib`** — the maintained `passlib` successor with a similar interface. A reasonable choice; rejected as an unnecessary layer over a two-function need.
