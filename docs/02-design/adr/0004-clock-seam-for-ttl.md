# ADR-0004: A single clock seam for all time reads

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SRS NFR-04 · SDS §2.4.2 · spec UM-US-01 AC-06, BR-04 · constitution TST-06 · plan A5

## Context

TTL correctness is a security requirement (SRS NFR-04: tokens "strictly expire after their configured TTL"), so it must be tested — including at the boundary, one second either side of expiry. Tests cannot wait 24 hours, so time has to be controllable.

A second, subtler problem surfaced in the spike: SQLite stores no timezone. A datetime written as timezone-aware reads back **naive**, and comparing naive to aware raises `TypeError: can't compare offset-naive and offset-aware datetimes`. That failure appears only once data round-trips through the database, so it survives unit tests and breaks at runtime.

## Decision

One module, `app/core/clock.py`, with two functions:

```python
def utcnow() -> datetime:              # timezone-aware current UTC
def ensure_aware(value: datetime)      # attach UTC if naive
```

- **Every** time read goes through `utcnow()`. `datetime.now()` and `datetime.utcnow()` are banned in application code (constitution: Time convention).
- **Every** stored datetime passes through `ensure_aware()` before it is compared or serialised.
- Tests freeze time by monkeypatching this one function.
- `EXPIRED` is therefore always **derived** — computed by comparing `expires_at` against `utcnow()` on read — never a stored flag, so no value can go stale and no sweeper job is needed (SDS §2.4.2, spec BR-04).

## Consequences

**Positive**
- Boundary tests become trivial and instant: freeze, advance 24h + 1s, assert expiry.
- No `freezegun` dependency; the seam is four lines.
- The SQLite/PostgreSQL timezone difference is neutralised in one place instead of at every comparison site.
- Deriving `EXPIRED` means the database can never disagree with the clock.

**Negative**
- Modules that do `from app.core.clock import utcnow` bind their own reference, so a test patching `clock.utcnow` alone misses them. The test fixture must patch each importing module's binding — a real sharp edge, documented in `conftest.py`.
- Requires discipline: a stray `datetime.now()` silently escapes the seam. Worth a lint rule if it ever recurs.

## Alternatives rejected

- **`freezegun`** — patches globally and works, but adds a dependency, slows the suite, and does nothing about the naive/aware round-trip problem, which was the more dangerous of the two issues.
- **Naive UTC everywhere** — sidesteps the comparison error by storing naive datetimes, but throws away timezone information that PostgreSQL would otherwise preserve, and makes correct API serialisation ambiguous.
- **Persisting an `EXPIRED` status via a scheduled job** — matches a literal reading of the SDS state diagram but introduces a background worker and a window where stored state lags reality.
