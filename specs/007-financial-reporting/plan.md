# Technical Plan: Financial Reporting (FR)

> **Feature:** SRS §6 Feature-07 · SDS §5.7 (FR)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** FR-US-01 *(planned)* · FR-US-03 *(planned)*

> **Naming note carried from `spec.md`:** this epic's code (`FR`) collides in spelling with `SRS
> FR-07` (the requirement) and with this file's own local `FR-NN` numbering in `spec.md`. This
> document never uses a bare `FR-NN` — every citation below is either `SRS FR-07`, `FR-US-01`/
> `FR-US-02`, or a spelled-out reference to `spec.md`'s own `FR-01`…`FR-11`.

---

## FR-US-01: View Summary Report

### Gaps & Decisions (Resolved)

Code and architecture decisions settled during design. Spec-level findings were folded back into
`spec.md` before this step closed.

| ID | Area | Decision | Status |
|----|------|----------|--------|
| A1 | Domain / Scope | **This story implements a single-period (current calendar month) snapshot only — no historical or multi-period "trend" data, no list of periods, no date-range input anywhere in the API contract.** `spec.md`'s *Assumptions & Dependencies* reasons through this in full against `SRS FR-07`'s "net savings trends" language; the short version, restated here for its architectural consequence: `SDS §5.7.1`'s own goal sentence for *this* story names four single-period figures and no trend language, `SDS §1.5.1` marks `FR-US-01…02` together **"✔ (partial)"** against `SRS US-07-01` — a documented acknowledgement that the trend portion is deliberately left to a future, unnumbered story — and `FR-US-02` (the other SDS story sharing this requirement) is itself also single-period by its own goal text. Consequence for this design: `GET /reports/summary` (A11) takes no `date_from`/`date_to`/`month`/`year` parameter of any kind, and `SummaryReportRead` (A6) carries one `period` field, not a list of periods. Not escalated as `[NEEDS RULING]` — `SRS.md` and `SDS.md` do not disagree once `SDS §5.7.1`'s and `SDS §1.5.1`'s own texts are read together; `SDS.md` narrows `SRS FR-07`'s bundle across two stories and says so explicitly. | ✅ Resolved |
| A2 | Domain | **No caller-supplied period; the period is always the current calendar month, computed server-side as `clock.utcnow().date().replace(day=1)` — identical mechanism to `BM-US-01` A2 — extended with an explicit half-open datetime interval `[period_start, period_end)` because, unlike `Budget.period` (a bare `Date` column needing no range comparison), `Transaction.timestamp` is a full timezone-aware `datetime`, so the query needs both ends of the interval, not one equality-comparable value.** Weighed against `TM-US-02` A1/A6's own precedent of accepting a caller-supplied `date_from`/`date_to`: that story built its filter because `SDS §5.6.2`'s own goal sentence explicitly names "date range" as one of three filter dimensions for *that* story; `SDS §5.7.1`'s goal sentence for *this* story names no filter or period-selection language at all, only "monthly" as a description of the figures shown — the same absence that led `BM-US-01` A2 to reject an explicit `period` input. `SRS.md`'s own text reinforces this: `US-07-01` has no Gherkin at all (not even BM-US-01's minimal one), so there is no walkthrough anywhere showing a person choosing a month. `period_end` is computed by rolling `period_start` forward one calendar month, handling the December→January year rollover explicitly (`start_date.month == 12` → `end_date = start_date.replace(year=+1, month=1)`, else `end_date = start_date.replace(month=+1)`) rather than a day-arithmetic shortcut, so the boundary is exact regardless of which month the report runs in. Both ends are then attached to UTC via the same `datetime.combine(..., time.min, tzinfo=UTC)` construction — never `datetime.now()` (`CLAUDE.md` §4). | ✅ Resolved |
| A3 | Domain / Security | **The report aggregates across every wallet the authenticated caller owns — no `wallet_id` filter parameter exists on this endpoint at all.** Weighed against `TM-US-02` A1's own precedent of building a `wallet_id` filter: that story did so because `SDS §5.6.2`'s own goal sentence explicitly names "wallet" as one of three filter dimensions; `SDS §5.7.1`'s goal sentence names no wallet-scoping language whatsoever, and the SRS's own framing ("my savings rate") is a whole-of-self figure with no source suggesting a per-wallet report. Ownership is enforced by the identical join-based pattern `TM-US-02` A2 already established — `transactions JOIN wallets ON transactions.wallet_id = wallets.id WHERE wallets.user_id = :caller_id` — extended here from a list query to two aggregate queries (A4, A5), both carrying the identical join-plus-predicate so neither can drift from the other the same way `TM-US-02` A2/QF-10 already guard against for its own two queries. No join to `categories` is needed to *enforce* ownership (the same reasoning `TM-US-02` A2 gives: `TM-US-01` BR-01 already guarantees a transaction's category belongs to the same owner as its wallet) — the join to `categories` in A5 exists only to read `name`, not to scope ownership. | ✅ Resolved |
| A4 | Architecture | **Total income and total expenses are computed by one query — `SELECT type, SUM(amount) … GROUP BY type` — not two separate per-type `SUM` queries, and not a single-row query built from a `CASE` expression.** Three shapes were weighed. Two separate queries (`SUM(amount) WHERE type = 'INCOME'`, then again for `'EXPENSE'`) is the most literal mirror of this codebase's existing "total-plus-page" pattern (`wallet_repo.list_owned()`, `transaction_repo.list_owned()`) but costs two round trips for two numbers this story always needs together. A single `CASE`-conditional-aggregation query (`SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END)`, and similarly for expense, as two columns of one row) returns both in one round trip but is harder to read than a plain `GROUP BY`, and produces a row of `NULL`s (not a missing row) when there is no data at all, which is a *different* empty-case shape than A5's grouped query below now has to handle, adding needless inconsistency. `GROUP BY type`, chosen: one round trip, at most two rows back (`TransactionType` is a closed two-value enum — `TransactionModel`, TM-US-01 A7), and the **same** "a type with zero matching rows produces no row at all, not a null-valued row" empty-case shape that A5's `GROUP BY category_id` already has, so the service layer (A7) has exactly one coalesce-to-zero pattern to apply consistently across both queries rather than two different ones. | ✅ Resolved |
| A5 | Domain / Architecture | **Top spending categories: one query joining `transactions` → `wallets` (ownership, A3) and `transactions` → `categories` (name, A6), filtered to `type == EXPENSE` and the period, `GROUP BY categories.id, categories.name`, `ORDER BY SUM(amount) DESC, categories.id ASC`, `LIMIT 5`.** Three sub-decisions. **Scoped to `EXPENSE` only:** both `SRS.md` ("top spending categories") and `SDS §5.7.1` ("top spending categories") use "spending" specifically — an `INCOME`-typed category ranked by total is not what either source names, and FR-09's own scope framing (`SRS FR-07`: "top category spending rankings") agrees. **`GROUP BY` both `id` and `name`, not `id` alone:** PostgreSQL (the deployment target, `constitution.md` ENV-03) permits omitting functionally-dependent columns from `GROUP BY` when grouping by a primary key, but relying on that would be exactly the kind of engine-specific leniency ENV-03 forbids depending on ("nothing may depend on SQLite-only behaviour, and nothing may be *hidden* by it either") — grouping by both columns is portable and correct on both engines unconditionally. **Limit of 5, named `TOP_CATEGORIES_LIMIT`:** neither `SRS.md` nor `SDS.md` names a number (`spec.md` FR-08 records this directly). Five is chosen as a small, defensible, conventional "top N" size — enough to be useful without listing every category, and small enough that no pagination machinery (`constitution.md` API-06, which governs *list* endpoints) is warranted for what is a fixed-size ranking embedded in a single summary resource, not a standalone paginated collection. Declared as a named constant in `report_service.py`, not an inline literal (anticipates the Implementation-step review point `aif-review-checklist.md` already names for magic numbers). **Tie-break `category_id` ascending, not category name:** `category_name` was considered first, since it is the more human-meaningful secondary key for a *ranking a person reads* — but rejected because `CM-US-01` A3 (checked directly) established **no uniqueness constraint on `categories.name`, not even scoped to one User**, so two tied categories could also share a name, leaving the ordering non-deterministic again. `category_id` is the only field in this ranking guaranteed unique, and ascending is the same "otherwise arbitrary, pick one and be consistent" convention `WM-US-02` A1 and `TM-US-02` A4 each already established for their own tie-breaks. | ✅ Resolved |
| A6 | Domain / API | **Each top-category entry carries `category_name: str` alongside `category_id: str` — a single projected scalar field from `Category`, not a nested `CategoryRead` object — breaking, in this one narrow instance, from the "no embedded foreign entity data" precedent `TM-US-01` A14 and `TM-US-02` A8 each established.** Weighed explicitly rather than defaulted either way. Reasons to keep the precedent (reject the name): every prior list in this codebase (`TransactionListRead`, `WalletListRead`) reuses its item's own `Read` DTO unchanged, and `constitution.md` PF-03 says "DTO projection, never an entity graph." Reasons to depart (accept the name, decided): (1) `TM-US-01`/`TM-US-02`'s own situation is materially different — there, the *primary subject* of each list row is a **Transaction**, and `category_id` is one of seven fields the caller has plenty of other context (`amount`, `timestamp`, `note`) to identify the row by even without a name; here, the **category itself is the primary subject** of half this report — "top spending categories" names categories, not transactions, and a bare id is close to meaningless for exactly the thing the ranking exists to show. (2) Checked directly: **no `GET /categories` endpoint exists anywhere in this codebase** — `api/v1/categories.py` has only `POST`, and `category_repo.py` has no `list_owned()` at all — so unlike a transaction list (where a caller could at least imagine resolving a foreign id through some other existing endpoint), there is currently **no path through this API, at any cost, by which a caller could resolve a bare `category_id` to a display name.** (3) `TM-US-02` A8 itself left the door open for exactly this re-examination: "If a real screen later needs display names, that is a new, explicit design question for whichever story builds it — not a default this story should reach for." This is that story. `category_name` is obtained via the same join A5's query already performs to group by category — no second query, no nested object, one denormalised string field. Not a precedent for embedding entire entities elsewhere; scoped to this one field, this one reasoned exception. | ✅ Resolved |
| A7 | Domain / Data Integrity | **Empirically investigated: `func.sum()` over this codebase's `Numeric(15, 2)` columns preserves exact `Decimal` arithmetic on SQLite (this project's dev engine, `constitution.md` ENV-03) — including through a `GROUP BY` + `JOIN`, the exact shape A4/A5 use — but an aggregate over zero matching rows produces no row at all (not a null-valued row), so the service layer must explicitly default a missing key to `Decimal("0.00")`.** Two scratch scripts (not part of this deliverable) were run against this project's real `sqlalchemy==2.0.51` and an in-memory SQLite engine, using this codebase's exact column style (bare `Numeric(15, 2)`, default `asdecimal=True`, matching `wallet.py`/`transaction.py`). Findings: (1) `func.sum()` over classic float-trap values (`0.10 + 0.20`, a 15-row accumulation) returned a `Decimal` bit-for-bit equal to Python's own `Decimal` summation — no float drift, confirming `constitution.md` VL-07 holds through this codebase's first `SUM()`-style query without any extra cast or rounding step. (2) The identical exactness held for `SUM(amount) … JOIN wallets … GROUP BY category_id … ORDER BY SUM(amount) DESC` — the join-plus-aggregate shape A5 uses for ownership and grouping. (A5's query additionally joins to `categories` to select `name` alongside `id`; that join was not separately re-tested, but it adds only an unaggregated display column on an equi-join to a primary key — it cannot alter what `SUM()` computes, so the exactness result generalises to it without needing a third script.) (3) **A `GROUP BY` simply omits a group with zero matching rows** — confirmed with a category carrying zero transactions in the test period, which correctly did not appear in the result at all (this is also *why* A9/`spec.md` FR-09's "omit, don't zero-pad" behaviour needs no extra application logic for the top-categories case). (4) A flat, ungrouped `SELECT SUM(amount) WHERE …` over zero matching rows returns SQL `NULL` → Python `None`, not `Decimal("0")` — confirmed separately. Both (3) and (4) are the same underlying trap from two different query shapes, and both demand the same fix: `report_service.get_summary_report()` must default a `TransactionType` absent from A4's result dict to `Decimal("0.00")` (spec AC-06, EC-02, EC-03), never treat a missing key or a `None` as an error or leave it unhandled. **PostgreSQL (the deployment target) was not independently tested here — no Docker in this environment (`constitution.md` ENV-04)** — but is reasoned, from documented, standard behaviour rather than assumed: `NUMERIC`/`DECIMAL` is PostgreSQL's own arbitrary-precision **exact** type by definition (distinct from `float4`/`float8`), and `SUM()` over a `NUMERIC` column is specified to return `NUMERIC` — at least as exact as the SQLite result already measured. Flagged explicitly as reasoned-not-tested rather than silently assumed equal (`CLAUDE.md` §6 honesty rule). | ✅ Resolved |
| A8 | Architecture / Performance | **No new index and no new Alembic migration.** The existing composite index `ix_transactions_wallet_id_timestamp` (`TM-US-02` A5, on `(wallet_id, timestamp)`) already serves both of this story's queries' access pattern exactly: `wallet_id` is the leading column both A4 and A5 join and filter through (A3), and `timestamp` — the trailing column — is exactly what bounds every query to `[period_start, period_end)`. `transactions.category_id` (TM-US-01, plain index) is not the leading predicate of A5's query (the wallet-ownership join and period filter narrow the row set first; grouping by category happens over that already-narrowed set), so no new composite touching `category_id` is warranted by this story's own query shape. Current Alembic head is `2187429f50ce` — cited for completeness; this story adds no migration and does not move the head. | ✅ Resolved |
| A9 | Architecture | **The two new queries (A4, A5) are added to the existing `transaction_repo.py`, not a new `report_repo.py`.** This codebase's repository modules map one-to-one to a model so far (`wallet_repo.py`↔`WalletModel`, `category_repo.py`↔`CategoryModel`, `budget_repo.py`↔`BudgetModel`, `transaction_repo.py`↔`TransactionModel`) — and, confirmed directly against `SRS.md` §1.5 and `SDS.md` §2.1, **there is no `Report` model**; this story introduces no new domain entity (`spec.md` *Key Entities*). The data both new queries read is fundamentally `TransactionModel` rows, aggregated two different ways, through joins `transaction_repo.py` already knows how to build (A3, extending `TM-US-02` A2's join unchanged). `transaction_repo.py` already owns every transaction query this codebase has; a `report_repo.py` would front no model of its own and would only relocate code that already belongs where every other transaction query lives. | ✅ Resolved |
| A10 | Architecture | **`report_service.py`, `schemas/report.py`, and `api/v1/reports.py` are new modules despite no `ReportModel` existing** — precedented by this codebase's own service/schema/router modules that already name a *capability*, not a model: `auth_service.py` and `schemas/activation.py` correspond to no `AuthModel`/`ActivationModel` either, yet are named for the story area they serve. `report_service.py` follows the identical pattern for the Financial Reporting story area. | ✅ Resolved |
| A11 | API | **Endpoint invented as `GET /api/v1/reports/summary` (`FR-API-01`) — checked directly, `SDS.md` §6.3's API Index and §6.5's traceability table have no Financial Reporting row of any kind, not even a partial one.** This is one step further than `TM-US-02`'s own smaller version of this gap (which at least extended an existing `TM-API-01` row) — there is nothing to extend here at all, so the path is derived purely from `constitution.md` API-01 (versioned, lowercase, plural resource noun) and NC-03 (hyphenated nouns, no verb outside an explicit state transition — `summary` is a noun, so NC-03's verb restriction is not even implicated). Three shapes were considered. **`GET /api/v1/reports`** (bare collection noun) was rejected because every other bare plural `GET` in this codebase (`/wallets`, `/transactions`, `/users`) returns a **list**, paginated per API-06 — reusing that shape for a single computed object would be a misleading precedent-collision, not a genuine list of "report" rows. **`GET /api/v1/transactions/summary`** (nested under the entity being summarised) was rejected because the report also draws on `Wallet` and `Category`, not `Transaction` alone, and nesting under one contributing entity implies a narrower scope than the story actually has. **`GET /api/v1/reports/summary`, chosen:** `reports` is the plural resource-family noun this feature area owns (matching `SDS §5.7`'s own heading, "Financial Reporting"), and `summary` names this specific, singleton report within that family — leaving room for a sibling path (e.g. a future `FR-US-02` category-expense report) to live alongside it under the same collection without either colliding with or overloading the bare collection GET. This pattern is genuinely new to this codebase (no nested resource path exists yet — every other endpoint is a flat top-level noun), recorded here explicitly rather than silently invented. **This is a note for whoever next aligns `SDS.md`:** §6.3 and §6.5 should gain this row the same way `UM-API-04` was registered at `SDS.md` v1.2.0 — not done here, since this dispatch may not edit `SDS.md` (`CLAUDE.md` §1.1). | ✅ Resolved |
| A12 | API / Validation | **This endpoint accepts no input at all — no query parameter, no path parameter, no request body — a direct consequence of A2 (no caller-supplied period) and A3 (no wallet filter).** The error catalogue below is, as a result, the narrowest of any endpoint in this codebase so far: no `422` (nothing to validate — VL-01 has nothing to be the source of truth *for*), no `404` (nothing is referenced by id), no `409` (nothing is created or mutated), no `403` (A14: no role restriction). The only reachable error is `401`. Each absence is a consequence of a design choice already justified above (A2, A3, A14), not an oversight — recorded explicitly so a reviewer does not mistake a short error table for an incomplete one. | ✅ Resolved |
| A13 | Logging | **No new audit event.** `constitution.md` LA-04 names exactly three audited event families (invitations sent, activations completed, logins); a read-only summary view is further from any of them than the list endpoints that already declined one (`WM-US-02` A5, `TM-US-01` A13, `TM-US-02` A10) — no AC or FR in `spec.md` asks for one either. | ✅ Resolved |
| A14 | Security | **No role restriction — `CurrentUserDep`, not `AdminDep`, guards the route.** `SDS §5.7.1` tags this story "(USER)", identical to every other USER-tagged story in this codebase; any authenticated caller of either role may view their own report, scoped entirely by A3's ownership join. | ✅ Resolved |

---

### Architecture

**Package layout** (additions only — no new model, no migration; see A8, A9, A10).

```text
backend/app/
├── schemas/
│   └── report.py                     # NEW  CategorySpendingRead, SummaryReportRead
├── repositories/
│   └── transaction_repo.py           # MODIFIED  add get_summary_totals(), get_top_expense_categories()
└── services/
    └── report_service.py             # NEW  _month_bounds(), TOP_CATEGORIES_LIMIT, get_summary_report()

backend/app/api/v1/
├── reports.py                        # NEW  GET /reports/summary
└── router.py                         # MODIFIED  mount reports.router

backend/tests/
└── integration/test_fr_us_01_view_summary_report.py   # NEW  written at the Implement step from test_cases.md
```

No change to `core/deps.py` (`CurrentUserDep` reused exactly as-is, A14), no change to `core/errors.py`
(the only reachable error, `401`, already exists as `NotAuthenticatedError`, A12), no change to
`app/models/*.py` (no new domain entity, `spec.md` *Key Entities*), no new Alembic migration (A8).

**Domain objects**

| Entity | Table | Fields touched | Notes |
|--------|-------|-----------------|-------|
| `TransactionModel` | `transactions` | none (read-only) | Summed two ways (A4, A5). No new column, no new index (A8). |
| `WalletModel` | `wallets` | none (read-only, join only) | Joined for ownership only (A3) — never selected from directly, mirrors `TM-US-02` A2. |
| `CategoryModel` | `categories` | none (read-only, join only) | Joined for `id`/`name` only, in A5's query — the first place in this codebase a query joins to `categories` for anything beyond an ownership check. |
| `SummaryReportRead` (DTO) | — | `period`, `total_income`, `total_expenses`, `net_savings`, `top_categories` | New; not in `SDS.md`'s DTO registry (§6.2.1 names no Financial Reporting DTO at all) — designed from nothing but `SDS §5.7.1`'s goal sentence and constitution PF-03 (A11). |
| `CategorySpendingRead` (DTO) | — | `category_id`, `category_name`, `total_amount` | New; the embedded-name exception (A6). |

**DTOs** (`app/schemas/report.py`, new file)

```python
"""Financial Reporting DTOs (SDS §5.7.1 FR-US-01; spec FR-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection -- see plan.md A6 for CategorySpendingRead's one
deliberate, narrow exception).
"""

from decimal import Decimal
from datetime import date

from pydantic import BaseModel


class CategorySpendingRead(BaseModel):
    """One ranked entry in the top spending categories list (spec AC-10..AC-13;
    plan.md A5, A6). `category_name` is a single projected field from
    Category -- not a nested CategoryRead -- because no GET /categories
    endpoint exists anywhere in this codebase through which a caller could
    otherwise resolve a bare category_id to a display name (plan.md A6).
    """

    category_id: str
    category_name: str
    total_amount: Decimal


class SummaryReportRead(BaseModel):
    """SDS §5.7.1's four named figures, plus the period they apply to (spec
    AC-01, AC-15, FR-11). Not in SDS's DTO registry (§6.2.1) at all -- this
    story designs the response shape from nothing but the goal sentence and
    constitution PF-03 (plan.md A11). `net_savings` carries no positivity
    bound -- it may be negative (spec AC-09, BR-04).
    """

    period: date
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    top_categories: list[CategorySpendingRead]
```

**Repository additions** (`app/repositories/transaction_repo.py`)

```python
def get_summary_totals(
    db: Session, *, user_id: str, period_start: datetime, period_end: datetime
) -> dict[TransactionType, Decimal]:
    """Sum the caller's own transactions in [period_start, period_end), one
    entry per TransactionType actually present (spec AC-07, AC-08, BR-03;
    plan.md A4).

    A type with no qualifying transactions in the period produces no row at
    all -- GROUP BY omits empty groups (plan.md A7, empirically confirmed) --
    so the caller (report_service.get_summary_report) must default an absent
    key to Decimal("0.00"); a missing key is never an error.
    """
    conditions = [
        WalletModel.user_id == user_id,
        TransactionModel.timestamp >= period_start,
        TransactionModel.timestamp < period_end,
    ]
    rows = db.execute(
        select(TransactionModel.type, func.sum(TransactionModel.amount))
        .join(WalletModel, TransactionModel.wallet_id == WalletModel.id)
        .where(*conditions)
        .group_by(TransactionModel.type)
    ).all()
    return {row[0]: row[1] for row in rows}


def get_top_expense_categories(
    db: Session,
    *,
    user_id: str,
    period_start: datetime,
    period_end: datetime,
    limit: int,
) -> Sequence[tuple[str, str, Decimal]]:
    """The caller's own top `limit` expense categories in
    [period_start, period_end), highest total first, category_id ascending
    as a deterministic tie-break (spec AC-10, AC-12, BR-05; plan.md A5).

    Grouped by both categories.id and categories.name -- not id alone -- so
    this stays correct on PostgreSQL without relying on its primary-key
    functional-dependency allowance for GROUP BY (constitution ENV-03).
    """
    conditions = [
        WalletModel.user_id == user_id,
        TransactionModel.type == TransactionType.EXPENSE,
        TransactionModel.timestamp >= period_start,
        TransactionModel.timestamp < period_end,
    ]
    total = func.sum(TransactionModel.amount)
    rows = db.execute(
        select(CategoryModel.id, CategoryModel.name, total)
        .join(WalletModel, TransactionModel.wallet_id == WalletModel.id)
        .join(CategoryModel, TransactionModel.category_id == CategoryModel.id)
        .where(*conditions)
        .group_by(CategoryModel.id, CategoryModel.name)
        .order_by(total.desc(), CategoryModel.id.asc())
        .limit(limit)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows]
```

`CategoryModel` becomes a new import into `transaction_repo.py` (alongside the existing
`TransactionModel`/`WalletModel` imports) — the first time this module reads from `categories` rather
than only filtering `transaction_id`/`category_id` as opaque foreign-key strings.

**Service** (`app/services/report_service.py`, new file)

```python
"""Financial Reporting service (spec FR-US-01; plan.md A1..A14).

Constitution AR-01: the only place that decides what "the current period"
means and assembles the response -- the repository only knows how to sum and
group rows (AR-03).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.models.transaction import TransactionType
from app.models.user import UserModel
from app.repositories import transaction_repo
from app.schemas.report import CategorySpendingRead, SummaryReportRead

TOP_CATEGORIES_LIMIT = 5  # spec FR-08; plan.md A5 -- no source names a number


def _month_bounds(today: date) -> tuple[datetime, datetime]:
    """The current calendar month as a half-open UTC interval [start, end)
    (spec BR-02; plan.md A2). `today` is always clock.utcnow().date() --
    never client input; this endpoint accepts none (plan.md A12).
    """
    start_date = today.replace(day=1)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    return (
        datetime.combine(start_date, time.min, tzinfo=UTC),
        datetime.combine(end_date, time.min, tzinfo=UTC),
    )


def get_summary_report(db: Session, *, owner: UserModel) -> SummaryReportRead:
    """spec AC-01..AC-15. Period is always the current calendar month, read
    from the system clock (BR-02) -- never from the request, because this
    endpoint accepts no input at all (plan.md A12).
    """
    period_start, period_end = _month_bounds(clock.utcnow().date())

    totals = transaction_repo.get_summary_totals(
        db, user_id=owner.id, period_start=period_start, period_end=period_end
    )
    total_income = totals.get(TransactionType.INCOME, Decimal("0.00"))
    total_expenses = totals.get(TransactionType.EXPENSE, Decimal("0.00"))

    top = transaction_repo.get_top_expense_categories(
        db,
        user_id=owner.id,
        period_start=period_start,
        period_end=period_end,
        limit=TOP_CATEGORIES_LIMIT,
    )

    return SummaryReportRead(
        period=period_start.date(),
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=total_income - total_expenses,
        top_categories=[
            CategorySpendingRead(category_id=cid, category_name=name, total_amount=amount)
            for cid, name, amount in top
        ],
    )
```

**Router** (`app/api/v1/reports.py`, new file)

```python
"""Financial Reporting endpoints (SDS §5.7.1 FR-US-01)."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.report import SummaryReportRead
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/summary",
    response_model=SummaryReportRead,
    status_code=status.HTTP_200_OK,
    summary="View the caller's summary report",
    description=(
        "Returns the authenticated caller's total income, total expenses, net "
        "savings, and top spending categories for the current calendar month, "
        "aggregated across every wallet the caller owns."
    ),
    responses={401: {"description": "NOT_AUTHENTICATED"}},
)
def get_summary_report(db: DbDep, current_user: CurrentUserDep) -> SummaryReportRead:
    """Pure read -- no db.commit() (plan.md A13, mirrors WM-US-02 A4 / TM-US-02 A9)."""
    return report_service.get_summary_report(db, owner=current_user)
```

`api/v1/router.py` gains `reports` in its import line and one
`api_router.include_router(reports.router)` call, alongside the existing seven.

**Business rules enforced in service layer**

| Rule | Source | Enforcement |
|------|--------|--------------|
| Any authenticated User of any role may view their own summary report | AC-01, FR-01, A14 | `GET /api/v1/reports/summary` guarded by `CurrentUserDep` — not `AdminDep` |
| Unauthenticated caller denied, nothing computed | AC-02, FR-02 | `CurrentUserDep` resolves before the service runs — identical ordering to every other protected route |
| Period is always the current calendar month, server-computed | AC-05, FR-03, A2 | `report_service._month_bounds(clock.utcnow().date())`; no query parameter exists to override it (A12) |
| Aggregated across every wallet the caller owns | AC-03, FR-04, A3 | `transaction_repo`'s two new queries both `JOIN wallets` and filter `wallets.user_id = :owner_id` |
| Another User's data never included | AC-04, FR-04, A3, constitution SEC-08 | Same ownership join; no cross-user row can satisfy either query's `WHERE` |
| Total income / total expenses, zero if none | AC-06, AC-07, AC-08, EC-02, EC-03, FR-05, FR-06, BR-03, A4, A7 | `get_summary_totals()` + `.get(type, Decimal("0.00"))` in the service |
| Net savings = income − expenses, may be negative | AC-09, EC-10, EC-11, EC-12, FR-07, BR-04 | Plain `Decimal` subtraction in `get_summary_report()`; `SummaryReportRead.net_savings` carries no positivity bound |
| Top categories: EXPENSE only, ranked descending, capped at 5, deterministic tie-break | AC-10, AC-12, EC-04, EC-05, EC-06, FR-08, BR-05, A5 | `get_top_expense_categories()`: `type == EXPENSE`, `GROUP BY`, `ORDER BY total DESC, id ASC`, `LIMIT TOP_CATEGORIES_LIMIT` |
| Zero-total category omitted, never zero-padded | AC-11, FR-09, A5, A7 | `GROUP BY` naturally excludes a category with no matching rows — no filter-out step needed |
| Each ranked category carries a name | AC-13, FR-10, A6 | `CategorySpendingRead.category_name`, joined from `categories.name` in the same query |
| Transaction outside the period never counted | AC-14, A2 | `timestamp >= period_start AND timestamp < period_end` in both queries |
| Response exposes exactly the documented fields | AC-15, FR-11, constitution PF-03 | `SummaryReportRead` / `CategorySpendingRead` — no ORM graph, no extra field |
| Pure read, no commit | A13 | Router issues no `db.commit()` |
| No audit event | A13 | `report_service.get_summary_report()` calls no `audit.record()` |

**Sequence diagram — View Summary Report**

Drawn to `constitution.md` DG-01…DG-07: four lanes only, no SQL, no parameter lists, every request
into `API` answered back to `UI` with a status code, one workflow. The simplest diagram in this
codebase so far — this endpoint takes no input, so there is no business-state branching at all, only
the one always-checked-first auth failure every protected route shares.

```mermaid
sequenceDiagram
    autonumber
    actor UI as Authenticated User (mobile app)
    participant API as API
    participant Svc as ReportService
    participant Store as Store

    UI->>API: GET /reports/summary
    API->>Svc: get_summary_report(input)
    Note over Svc: The period is always the current calendar month, read from the system clock — never from the request, which carries no period of its own (BR-02)
    Svc->>Store: sum the caller's own income and expense transactions in the period, across every wallet the caller owns
    Store-->>Svc: total income, total expenses — each zero if none
    Svc->>Store: find the caller's top five expense categories in the period, across every wallet the caller owns
    Store-->>Svc: up to five categories, each with its name and total expense amount, highest first
    Svc-->>API: summary report
    API-->>UI: 200 summary report

    Note over UI,Store: Checked before the flow above
    opt Unauthenticated or expired credentials (AC-02)
        API-->>UI: 401 NOT_AUTHENTICATED
    end
```

Only one workflow is drawn (DG-07): the single `opt` is the one flow's own pre-check, not a second
flow, mirroring how `BM-US-01`/`TM-US-02` each folded their own auth check into one diagram.

**Error flows**

| Scenario | HTTP | Error Code |
|----------|------|------------|
| No or invalid bearer credentials (AC-02) | 401 | `NOT_AUTHENTICATED` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

All in the flat envelope `{"error_code", "message", "details"}` (SDS §6.6, constitution API-02) —
reused unchanged from `main.py`; no new error class (A12). No `422` (no input to validate), no `404`
(nothing referenced by id), no `409` (nothing mutated), no `403` (A14: no role restriction) — see A12
for why this catalogue is deliberately this short, not incomplete.

**Constitution notes**

| Rule | Status | Note |
|------|--------|------|
| AR-01 Service owns business rules | Required | `report_service.get_summary_report()` is the only place that decides what "the period" means and assembles the response |
| AR-02 Thin router | Required | Router resolves `CurrentUserDep`, calls the service, formats the response — no branching on business state |
| AR-03 Repository isolation | Required | `transaction_repo`'s two new functions are queries only — grouping and summing, no decision-making (A9) |
| AR-04 DTO ↔ model mapping outside routers/repos | Required | `report_service.get_summary_report()` maps repository tuples/dicts into `SummaryReportRead`/`CategorySpendingRead` |
| AR-05 No framework objects in services | Required | `get_summary_report(db, *, owner: UserModel)` takes plain values; no `Request`/`Response` |
| AR-06 One transaction per request | N/A | Pure read — no write, no commit at all (A13) |
| AR-07 Router → service → repository | Required | The router never calls `transaction_repo` directly |
| AR-08 Module layout | Required | `backend/app/{schemas,repositories,services,api}` — no new top-level package (A9, A10) |
| API-01 Versioned plural path | Required | `GET /api/v1/reports/summary` (A11) |
| API-02 Flat error envelope | Required | Reused from `main.py`, unchanged |
| API-03 Status codes | Required | `200` read · `401` (A12) |
| API-04 Prefixed error codes | N/A | No new error code — `NOT_AUTHENTICATED` is reused unchanged |
| API-05 No generic status endpoint | N/A | This is a plain resource read, not a state transition |
| API-06 Pagination | N/A | Not a list endpoint — a single, fixed-size (≤5) ranking embedded in one summary resource (A5) |
| API-07 Explicit response_model | Required | `response_model=SummaryReportRead`, `status_code=200` |
| API-08 Public endpoint list | Required | This route is **protected** — not added to the public list |
| NC-01 Module naming | Required | `report_service.py`, singular, matching `wallet_service.py`/`budget_service.py` (A10) |
| NC-02 Naming | Required | `SummaryReportRead`, `CategorySpendingRead` — no `ReportModel` exists to name (A9) |
| NC-03 API paths | Required | `reports/summary` — lowercase, no verb (A11) |
| NC-05 Enum serialisation | N/A | This story's response introduces no enum column of its own — `TransactionType` stays internal to the repository query (A4) |
| NC-06 Concise service methods | Required (as-implemented) | `report_service.get_summary_report`, matching this codebase's real (entity-suffixed) convention — `create_wallet`, `create_budget`, `list_transactions` — not the class-dotted `Service.method` shorthand constitution NC-06's own text illustrates |
| NC-07 Plural collection parameters | N/A | No collection-valued parameter in this story's functions |
| VL-01 Pydantic is the source of truth | N/A | No request payload exists for Pydantic to validate (A12) |
| VL-07 Decimal money | Required | `Decimal` throughout — DTO fields, repository return types, service arithmetic; investigated and confirmed exact through `SUM()`/`GROUP BY` (A7) |
| SEC-07 Authz proven by test | Required (partial) | `401` gets a dedicated test; there is no `403` case to test (A14) |
| SEC-08 Ownership filter | Required | Both new repository queries filter `wallets.user_id = :owner_id` (A3) |
| SEC-10 No enumeration | N/A | No reference id is ever submitted by the caller for this endpoint to confirm or deny the existence of (A12) |
| LA-02 / LA-04 Audit | N/A (by decision) | A summary view is not one of LA-04's three named audited events, and no AC/FR asks for a fourth (A13) |
| PF-01 300 ms p95 | Required | Two indexed aggregate queries (A8), no I/O off the request path |
| PF-02 Indexed queries | Required | Both queries' join-plus-range filter is served by the existing `ix_transactions_wallet_id_timestamp` composite — no new index needed (A8) |
| PF-03 DTO projection | Required (one scoped exception) | `SummaryReportRead`/`CategorySpendingRead` — five and three fields respectively; `category_name` is the one deliberate, reasoned departure from "no foreign entity data," recorded and justified in full at A6 |
| PF-04 Bounded lists | Required | `top_categories` is hard-capped at `TOP_CATEGORIES_LIMIT` (5) — never unbounded (A5) |
| TST-01/02 AC→TC coverage | Required | Every AC and EC mapped in `test_cases.md` before any test code |
| DOD-02 Migration | N/A | No model change, no migration (A8) |
| DOD-03 Coverage > 80% | Required | Measured at the Implement step |

**Element IDs**

| Element | ID | Status | File |
|---------|----|--------|------|
| — | — | **N/A (mobile deferred)** | No summary-report screen exists this round. `mobile/`'s fixture-driven prototype covers only UM-US-01's invite screen (`CLAUDE.md` §5); a report screen is not part of Round 1's mobile scope and no SRS UXR names one. |

**Open tasks**

| ID | Task | File | Status |
|----|------|------|--------|
| T-01 | `SummaryReportRead`, `CategorySpendingRead` | `backend/app/schemas/report.py` | Open |
| T-02 | `transaction_repo.get_summary_totals(...)`, `transaction_repo.get_top_expense_categories(...)` — import `CategoryModel` | `backend/app/repositories/transaction_repo.py` | Open |
| T-03 | `report_service._month_bounds(...)`, `TOP_CATEGORIES_LIMIT`, `report_service.get_summary_report(db, *, owner)` | `backend/app/services/report_service.py` | Open |
| T-04 | `GET /api/v1/reports/summary` router; mount `reports.router` in `api/v1/router.py` | `backend/app/api/v1/reports.py`, `backend/app/api/v1/router.py` | Open |
| T-05 | Integration tests written from `test_cases.md` | `backend/tests/integration/test_fr_us_01_view_summary_report.py` | Open |

---

## FR-US-03: Summary Report per Currency

> **IDs in this section are local to FR-US-03** — `A1`, `T-01` etc. restart here, as every
> multi-story `plan.md` in `specs/` does (`TM-US-02 A1`, `BM-US-02 T-01`). A bare `AC-NN`/`FR-NN`
> below means FR-US-03's own in `spec.md`; FR-US-01's are always written `FR-US-01 AC-NN`.

### Gaps & Decisions (Resolved)

Code and architecture decisions settled during design. Spec-level findings were folded back into
`spec.md` before this step closed.

| ID | Area | Decision | Status |
|----|------|----------|--------|
| A1 | Scope / Naming | **Story code `FR-US-03`, not `FR-US-02`.** `SDS §5.7.2` assigns `FR-US-02` to *View Category Expense Report*; FR-US-01's spec (naming note, *Out of scope*) and FR-US-01 A11 above both reserve it. This story has no SDS §5 entry and cites `SRS US-07-01` + `SDS §5.7.1` as its sources. Renaming later is mechanical — the code appears only in this epic's three files. | ✅ Resolved |
| A2 | API contract | **`FR-API-01` (`GET /api/v1/reports/summary`) changes shape in place: the four flat figures and `top_categories` move into a `currencies` list, one entry per currency; `period` stays at the top level.** Four alternatives were weighed. **(b) Keep the flat fields alongside the new list** — rejected: the flat fields can only be filled by adding amounts across currencies, which the ruling forbids outright; filling them only when the caller holds a single currency (null otherwise) makes the shape depend on the data, and leaves a field that is right by coincidence. **(c) A new endpoint (e.g. `/reports/summary-by-currency`), old one deprecated** — rejected: it keeps a route alive whose only possible output is the meaningless mixed total, and it doubles the surface for one report. **(d) A `currency` query parameter, one call per currency** — rejected: the client would first have to discover the currencies (from `GET /wallets`, which hides archived wallets whose transactions still count, A5), it costs N requests for one screen, and it reintroduces caller input this endpoint has deliberately never accepted (FR-US-01 A12). **A `/api/v2` version bump** — rejected: the only client is this repo's own `mobile/` app, changed in the same delivery (T-08), and `FR-API-01` was never registered in `SDS.md` §6 (FR-US-01 A11), so no published contract outside this repo exists to protect. **(a) Replace, chosen:** it is the only shape in which every number has a currency, it keeps one request per screen, and the breaking change is contained to one repo and one delivery. The product owner authorized the per-currency behaviour itself (2026-10-19); this row records how the contract carries it. Not escalated as `[NEEDS RULING]`: every rejected option either violates the ruling or adds surface the ruling does not ask for. | ✅ Resolved |
| A3 | Domain | **A currency appears iff the caller owns an active wallet in it, or a transaction of the caller's in the period belongs to a wallet in it (spec FR-05).** Weighed in full in `spec.md` *Assumptions*. Consequence for design: the currency set is the union of two sources — active-wallet currencies (a new `wallet_repo` read, A7) and currencies present in the per-currency totals (A5). Every currency with a ranked category also has an expense total, so the ranking query never introduces a currency the totals query lacks. | ✅ Resolved |
| A4 | Domain / API | **Currencies ordered by code ascending, sorted in the service.** Alternatives: by activity (largest expenses first) — rejected, a block would jump position as amounts change, and AC-04 promises repeatability; default currency (VND) first — rejected, the server has no notion of a default currency (`DEFAULT_CURRENCY` is a client constant in `mobile/src/utils/money.ts`; a server-side default is `DC-US-01`, out of scope). Codes are unique per entry, so code order is total and needs no tie-break. Sorted in `report_service` (AR-01), since it merges two sources (A3). | ✅ Resolved |
| A5 | Architecture | **Totals: `get_summary_totals()` is replaced by `get_summary_totals_by_currency()`, grouping by `(wallets.currency, transactions.type)`.** Same join, same ownership predicate, same half-open period as FR-US-01 A3/A4 — only one more grouping column, selected from the `wallets` row the query already joins for ownership. Returns `dict[tuple[str, TransactionType], Decimal]`; a missing `(currency, type)` key still means zero (FR-US-01 A7's trap, now per currency, so the service defaults per key). No `archived_at` predicate, exactly as FR-US-01 has none (verified in `transaction_repo.py`): an archived wallet's transactions in the period still count (spec AC-08). The old function is removed, not kept beside the new one — `report_service` is its only caller (checked with grep). | ✅ Resolved |
| A6 | Architecture / Performance | **Top categories per currency: one query, `ROW_NUMBER()` window partitioned by currency, replacing `get_top_expense_categories()` with `get_top_expense_categories_by_currency()`.** An inner query groups the caller's period EXPENSE transactions by `(wallets.currency, categories.id, categories.name)` and sums `amount`; an outer query numbers rows `OVER (PARTITION BY currency ORDER BY total DESC, category_id ASC)` and keeps `rank <= limit`, ordered by currency then rank. Three shapes weighed: **one query per currency** — rejected, an N+1 pattern (PF-02); **one grouped query with no limit, cut to five per currency in the service** — simpler SQL, but sends every (currency, category) pair the caller ever spent against this month up from the database for the service to discard most of them, and moves FR-US-01's bounded `LIMIT` out of the query; **window function, chosen** — one round trip, result bounded at five rows per currency, and the tie-break is FR-US-01 A5's `category_id ASC` unchanged. **Empirically checked** (scratch probe outside the repo, this project's `sqlalchemy 2.0.51`, SQLite `3.53.1`): the window query returned top five per currency with ties broken by id, the same category ranked separately in two currencies, another user's rows excluded, and every total a `Decimal` with exact sums (`0.10 + 0.20 = 0.30`, `19.99 + 0.01 = 20.00`). Window functions exist in SQLite since 3.25 and in every supported PostgreSQL, so nothing here leans on SQLite-only behaviour (ENV-03); PostgreSQL itself was not run (ENV-04), reasoned the same way FR-US-01 A7 reasoned. `CategoryModel.archived_at` is not filtered, as in FR-US-01 (spec EC-04). | ✅ Resolved |
| A7 | Architecture | **New `wallet_repo.list_active_currencies(db, *, user_id) -> list[str]`: the distinct currencies of the caller's wallets with `archived_at IS NULL`.** The same active-wallet predicate `wallet_repo.list_owned()` already applies (WM-US-05 A3). Lives in `wallet_repo`, not `transaction_repo`, because it reads wallets only (FR-US-01 A9's one-repo-per-model convention). | ✅ Resolved |
| A8 | Performance | **No new index, no migration.** `wallets.currency` appears in the new queries only as a selected, grouped and partitioned column, after the rows have been narrowed by `wallets.user_id` (indexed, WM-US-01) and `ix_transactions_wallet_id_timestamp` (TM-US-02 A5) — it is never a `WHERE` predicate or a join key, so PF-02 does not call for an index on it. The partition runs over one caller's own (currency, category) groups — tens of rows. Alembic head unchanged. | ✅ Resolved |
| A9 | API / DTO | **`SummaryReportRead` keeps its name and becomes `{period, currencies}`; new `CurrencySummaryRead` = `{currency, total_income, total_expenses, net_savings, top_categories}`; `CategorySpendingRead` unchanged.** Keeping the name avoids churn in the router and the mobile type for what is the same resource. `CurrencySummaryRead` carries exactly the four figures FR-US-01 put at the top level, so FR-US-01's per-figure rules move into it unchanged (spec FR-03, FR-04). `currencies` is always present, `[]` when empty — never `null` and never omitted (spec AC-09, AC-12). `currency` is serialised as stored: WM-US-01 FR-05 guarantees three uppercase letters, so no normalisation step exists. | ✅ Resolved |
| A10 | API | **Error catalogue, auth, audit and commit behaviour unchanged from FR-US-01 (A12, A13, A14).** Still no input of any kind, so still only `401`; still `CurrentUserDep`; still no audit event; still a pure read with no `db.commit()`. | ✅ Resolved |
| A11 | Testing | **FR-US-01's test cases are not rewritten; their test functions are re-pointed.** All 28 FR-US-01 tests build USD wallets only (`_make_wallet(..., currency="USD")` in `test_fr_us_01_view_summary_report.py`), so each assertion on a flat field translates mechanically to the single `currencies[0]` entry with `currency == "USD"`. Two outcomes change and are superseded by this story's TCs, recorded in `test_cases.md` (FR-US-03, *FR-US-01 test cases affected*): FR-US-01 TC-17 (exact top-level fields → TC-40) and TC-18 (no wallets → TC-37). FR-US-01's TC text and Test Implementation Map rows stay as written (`CLAUDE.md` §1.1 rule 4); the re-pointing is task T-06, and its rerun is recorded against FR-US-01's map at the Implement step. | ✅ Resolved |
| A12 | UI (fast-track) | **Home's *Analysis* section renders one block per `currencies` entry, in response order.** Each block: a heading with the currency code, *Income vs. expenses* bars scaled to that block's own larger figure, net savings with the savings rate, and *Where the money went* (`ExpenseDonut`) fed with that block's `top_categories`, `total_expenses` and `currency`. Every `formatMoney` call takes the block's own `currency`. The `reportCurrency` fallback in `Dashboard.tsx` — today labelling a mixed total with `DEFAULT_CURRENCY` when the wallets disagree — is deleted, since every figure now has a currency. Empty `currencies` → one panel reading "No income or expenses recorded in <Month>." in place of the blocks. The month label stays in the section header, read from the top-level `period`. Presentation only: the client computes no figure the API does not return, beyond the per-block bar widths and savings rate it already derives today. | ✅ Resolved |
| A13 | Docs alignment | **Nothing is aligned in `SRS.md` or `SDS.md` by this story.** `SDS.md` §6.3/§6.5 still lack an `FR-API-01` row (FR-US-01 A11's open note); this dispatch may edit only this epic's three files. Whether `SRS FR-07` should state "per currency" is a product-owner extension, not an alignment (`spec.md` *Assumptions*). | ✅ Resolved |

---

### Architecture

**Package layout** (changes only — no new model, no migration; A8)

```text
backend/app/
├── schemas/report.py                 # MODIFIED  SummaryReportRead → {period, currencies}; NEW CurrencySummaryRead
├── repositories/
│   ├── transaction_repo.py           # MODIFIED  get_summary_totals → get_summary_totals_by_currency,
│   │                                 #           get_top_expense_categories → get_top_expense_categories_by_currency
│   └── wallet_repo.py                # MODIFIED  add list_active_currencies()
├── services/report_service.py        # MODIFIED  get_summary_report() assembles one CurrencySummaryRead per currency
└── api/v1/reports.py                 # MODIFIED  description text only — same path, same response_model name

backend/tests/integration/
├── test_fr_us_01_view_summary_report.py      # MODIFIED  assertions re-pointed to currencies[0] (A11)
└── test_fr_us_03_summary_per_currency.py     # NEW       written at the Implement step from test_cases.md

mobile/src/                                     # UI fast-track (A12)
├── api/types.ts                      # MODIFIED  SummaryReportRead, new CurrencySummary
└── components/wallet/Dashboard.tsx   # MODIFIED  one analysis block per currency, empty state
mobile/e2e/home.spec.ts               # NEW       [UI] TCs of this story
```

**Domain objects**

| Entity | Table | Fields touched | Notes |
|--------|-------|-----------------|-------|
| `WalletModel` | `wallets` | none (read) | `currency` becomes the grouping key (A5, A6); `archived_at` read only by `list_active_currencies()` (A7) |
| `TransactionModel` | `transactions` | none (read) | Summed per `(currency, type)` and per `(currency, category)` |
| `CategoryModel` | `categories` | none (read) | Joined for `id`/`name`, as FR-US-01 A5/A6 |
| `SummaryReportRead` (DTO) | — | `period`, `currencies` | Reshaped (A2, A9) |
| `CurrencySummaryRead` (DTO) | — | `currency`, `total_income`, `total_expenses`, `net_savings`, `top_categories` | New (A9) |
| `CategorySpendingRead` (DTO) | — | `category_id`, `category_name`, `total_amount` | Unchanged |

**Response shape** (`200`, `FR-API-01`)

```json
{
  "period": "2026-10-01",
  "currencies": [
    {
      "currency": "USD",
      "total_income": "0.00",
      "total_expenses": "20.00",
      "net_savings": "-20.00",
      "top_categories": [
        {"category_id": "6f1c…", "category_name": "Travel", "total_amount": "20.00"}
      ]
    },
    {
      "currency": "VND",
      "total_income": "15000000.00",
      "total_expenses": "100000.00",
      "net_savings": "14900000.00",
      "top_categories": [
        {"category_id": "a2d4…", "category_name": "Food", "total_amount": "100000.00"}
      ]
    }
  ]
}
```

Empty case: `{"period": "2026-10-01", "currencies": []}`.

**DTOs** (`app/schemas/report.py`)

```python
class CategorySpendingRead(BaseModel):          # unchanged (FR-US-01 A6)
    category_id: str
    category_name: str
    total_amount: Decimal


class CurrencySummaryRead(BaseModel):
    """One currency's figures (spec FR-US-03 AC-01, FR-03, FR-04; plan A9).
    Never mixed with another currency's amounts (BR-02)."""

    currency: str
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    top_categories: list[CategorySpendingRead]


class SummaryReportRead(BaseModel):
    """FR-API-01 response (FR-US-03 A2). `currencies` ordered by code (A4),
    always present, [] when nothing qualifies (AC-09)."""

    period: date
    currencies: list[CurrencySummaryRead]
```

**Repository changes**

```python
# transaction_repo.py — replaces get_summary_totals()
def get_summary_totals_by_currency(
    db: Session, *, user_id: str, period_start: datetime, period_end: datetime
) -> dict[tuple[str, TransactionType], Decimal]:
    """FR-US-01 A4's query with WalletModel.currency added to the select and
    the GROUP BY. Same ownership join, same [start, end) bounds, no archived
    filter (A5). Absent key == zero; the service defaults it."""


# transaction_repo.py — replaces get_top_expense_categories()
def get_top_expense_categories_by_currency(
    db: Session, *, user_id: str, period_start: datetime, period_end: datetime, limit: int
) -> Sequence[tuple[str, str, str, Decimal]]:
    """(currency, category_id, category_name, total), at most `limit` rows per
    currency, ordered by currency then rank. Inner: group EXPENSE rows by
    (currency, category id, category name). Outer: row_number() over
    (partition by currency order by total desc, category id asc) <= limit (A6)."""


# wallet_repo.py — new
def list_active_currencies(db: Session, *, user_id: str) -> list[str]:
    """Distinct currencies of the caller's wallets with archived_at IS NULL (A7)."""
```

**Service** (`app/services/report_service.py`, `get_summary_report` body)

```python
period_start, period_end = _month_bounds(clock.utcnow().date())   # unchanged

totals = transaction_repo.get_summary_totals_by_currency(db, user_id=owner.id, ...)
ranked = transaction_repo.get_top_expense_categories_by_currency(
    db, user_id=owner.id, ..., limit=TOP_CATEGORIES_LIMIT
)
held = wallet_repo.list_active_currencies(db, user_id=owner.id)

currencies = sorted(set(held) | {cur for cur, _type in totals})        # A3, A4
by_currency: dict[str, list[CategorySpendingRead]] = defaultdict(list)
for cur, cid, name, amount in ranked:                                   # already in rank order
    by_currency[cur].append(CategorySpendingRead(category_id=cid, category_name=name, total_amount=amount))

zero = Decimal("0.00")
entries = []
for cur in currencies:
    income = totals.get((cur, TransactionType.INCOME), zero)
    expenses = totals.get((cur, TransactionType.EXPENSE), zero)
    entries.append(CurrencySummaryRead(
        currency=cur, total_income=income, total_expenses=expenses,
        net_savings=income - expenses, top_categories=by_currency[cur],
    ))
return SummaryReportRead(period=period_start.date(), currencies=entries)
```

`_month_bounds()` and `TOP_CATEGORIES_LIMIT` are reused unchanged.

**Router** (`app/api/v1/reports.py`) — path, method, `response_model=SummaryReportRead`, status and
`401` response unchanged; the `description` becomes "…for the current calendar month, reported
separately for each currency the caller holds or used — amounts in different currencies are never
added together."

**Business rules enforced in service layer**

| Rule | Source | Enforcement |
|------|--------|--------------|
| Every figure computed per currency, from the wallet's currency | AC-01, AC-03, FR-01, BR-01 | Both transaction queries group by `wallets.currency` (A5, A6) |
| No cross-currency arithmetic, no conversion | AC-02, AC-06, EC-03, EC-07, FR-02, BR-02 | The service only ever combines values sharing a `(currency, …)` key; no conversion code exists |
| Held-or-used presence rule | AC-07, AC-08, EC-06, FR-05, BR-03 | `set(list_active_currencies()) ∪ currencies in totals` (A3, A7) |
| Currency order by code | AC-04, FR-06, BR-04 | `sorted(...)` in `get_summary_report()` (A4) |
| Per-currency top five, ties by id, no padding | AC-05, AC-06, FR-04 | Window query, `rank <= TOP_CATEGORIES_LIMIT` (A6) |
| Zero figures for an unused held currency | AC-07, EC-01, EC-02 | `.get((cur, type), Decimal("0.00"))` (A5) |
| Archived wallet's period transactions counted; archived-only unused currency absent | AC-08 | No `archived_at` filter in A5/A6; `archived_at IS NULL` in A7 only |
| Archived category still ranked | EC-04 | No `archived_at` filter on `categories` (A6) |
| Empty report is `200` with `currencies: []` | AC-09, FR-07 | Empty `currencies` list (A9) |
| Unauthenticated denied | AC-10 | `CurrentUserDep`, unchanged (A10) |
| Caller's own data only | AC-11, FR-08 | `wallets.user_id = owner` in all three queries |
| Exact fields | AC-12, FR-09 | `SummaryReportRead` / `CurrencySummaryRead` / `CategorySpendingRead` (A9) |
| One period, current month, for all entries | AC-13, FR-08 | `_month_bounds()` once per request, applied to both transaction queries |

**Sequence diagram — View Summary Report per Currency**

Drawn to `constitution.md` DG-01…DG-07: four lanes, no SQL, no parameter lists, the one request
answered with a status in every branch, one workflow.

```mermaid
sequenceDiagram
    autonumber
    actor UI as Authenticated User (mobile app)
    participant API as API
    participant Svc as ReportService
    participant Store as Store

    UI->>API: GET /reports/summary
    API->>Svc: summarise(input)
    Note over Svc: The period is the current calendar month, from the system clock — never from the request
    Svc->>Store: find the currencies of the caller's active wallets
    Store-->>Svc: currency codes, possibly none
    Svc->>Store: sum the caller's income and expenses in the period, per wallet currency
    Store-->>Svc: one total per currency and type that has transactions
    Svc->>Store: find the caller's top five expense categories in the period, within each wallet currency
    Store-->>Svc: up to five categories per currency, highest first
    Note over Svc: Merge held and used currencies, sort by code, fill missing totals with zero — no amount ever crosses a currency
    Svc-->>API: summary report, one entry per currency
    API-->>UI: 200 summary report — period and currency entries, possibly none

    Note over UI,Store: Checked before the flow above
    opt Unauthenticated or expired credentials (AC-10)
        API-->>UI: 401 NOT_AUTHENTICATED
    end
```

**Error flows**

| Scenario | HTTP | Error Code |
|----------|------|------------|
| No or invalid bearer credentials (AC-10) | 401 | `NOT_AUTHENTICATED` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

Unchanged from FR-US-01 — flat envelope (API-02), no new error code (A10).

**Constitution notes**

| Rule | Status | Note |
|------|--------|------|
| AR-01 Service owns business rules | Required | Presence rule, ordering, zero-defaulting and assembly all in `report_service.get_summary_report()` (A3, A4) |
| AR-02 Thin router | Required | Router unchanged apart from description text |
| AR-03 Repository isolation | Required | Three queries, no decisions; the ranking limit is passed in by the service (A6) |
| AR-04 DTO mapping outside routers/repos | Required | Tuples/dicts mapped to DTOs in the service |
| AR-05 No framework objects in services | Required | Signature unchanged: `(db, *, owner)` |
| AR-06 One transaction per request | N/A | Pure read, no commit (A10) |
| AR-07 Router → service → repository | Required | Router never calls a repository |
| AR-08 Module layout | Required | No new module in `app/`; one new test module |
| DG-01…DG-07 Diagram shape | Required | Four lanes, intent-only store arrows, `200`/`401` back to `UI` in every branch, one workflow; parsed with the `CLAUDE.md` §3 harness |
| API-01 Versioned plural path | Required | Path unchanged; no `/v2` (A2) |
| API-02 Flat error envelope | Required | Unchanged |
| API-03 Status codes | Required | `200`, `401` |
| API-04 Prefixed error codes | N/A | No new code (A10) |
| API-05 No generic status endpoint | N/A | Read only |
| API-06 Pagination | N/A | Not a list endpoint; `currencies` is bounded by the caller's own currencies and each ranking by five (PF-04) |
| API-07 Explicit response_model | Required | `response_model=SummaryReportRead`, `status_code=200` |
| API-08 Public endpoint list | Required | Still protected |
| NC-01 Module naming | Required | No new `app/` module |
| NC-02 DTO naming | Required | `CurrencySummaryRead` follows the `…Read` convention |
| NC-03 API paths | Required | Unchanged |
| NC-05 Enum serialisation | N/A | `currency` is a plain code string, not an enum (WM-US-01 A2); `TransactionType` stays internal |
| NC-06 Concise service methods | Required (as-implemented) | `get_summary_report` kept, as FR-US-01 recorded |
| NC-07 Plural collection parameters | N/A | No collection-valued parameter |
| VL-01 Pydantic is the source of truth | N/A | No request payload |
| VL-07 Decimal money | Required | `Decimal` end to end; exactness through the window query checked (A6) |
| SEC-07 Authz proven by test | Required (partial) | `401` test (TC-38); no `403` case exists |
| SEC-08 Ownership filter | Required | `wallets.user_id` predicate in all three queries |
| SEC-10 No enumeration | N/A | Caller submits no reference |
| LA-02 / LA-04 Audit | N/A (by decision) | No audit event (A10) |
| PF-01 300 ms p95 | Required | Three indexed reads, one round trip each |
| PF-02 Indexed queries, no N+1 | Required | Window query instead of a query per currency (A6); no new index needed (A8) |
| PF-03 DTO projection | Required | Three narrow DTOs |
| PF-04 Bounded lists | Required | ≤5 categories per currency; currencies bounded by the caller's own wallets |
| ENV-03 No SQLite-only behaviour | Required | Window functions are standard and supported by both engines (A6) |
| TST-01/02 AC→TC before code | Required | `test_cases.md` FR-US-03 |
| DOD-02 Migration | N/A | No model change (A8) |
| DOD-03 Coverage > 80% | Required | Measured at the Implement step |

**Element IDs** (`mobile/src/components/wallet/Dashboard.tsx`, UI fast-track — A12)

| Element | ID | Status | File |
|---------|----|--------|------|
| One currency's analysis block | `report-{CUR}` (e.g. `report-VND`) | Missing | `mobile/src/components/wallet/Dashboard.tsx` |
| Block heading (currency code) | `report-{CUR}-currency` | Missing | same |
| Income row | `report-{CUR}-flow-Income` | Missing (today `flow-Income`, one per screen) | same |
| Expenses row | `report-{CUR}-flow-Expenses` | Missing (today `flow-Expenses`) | same |
| Net savings | `report-{CUR}-net-savings` | Missing (today `net-savings`) | same |
| Spending breakdown | `report-{CUR}-donut` | Missing | same, wrapping `ExpenseDonut` |
| Breakdown row | `category-{name}`, scoped inside `report-{CUR}-donut` | Present | `mobile/src/components/wallet/ExpenseDonut.tsx` |
| Empty-analysis message | `report-empty` | Missing | `mobile/src/components/wallet/Dashboard.tsx` |

**Open tasks**

| ID | Task | File | Status |
|----|------|------|--------|
| T-01 | `CurrencySummaryRead`; reshape `SummaryReportRead` to `{period, currencies}` (A9) | `backend/app/schemas/report.py` | Open |
| T-02 | Replace `get_summary_totals()` with `get_summary_totals_by_currency()` (A5) and `get_top_expense_categories()` with `get_top_expense_categories_by_currency()` (A6) | `backend/app/repositories/transaction_repo.py` | Open |
| T-03 | `wallet_repo.list_active_currencies(db, *, user_id)` (A7) | `backend/app/repositories/wallet_repo.py` | Open |
| T-04 | `report_service.get_summary_report()` assembles per-currency entries: merge, sort, zero-default, group ranking (A3, A4) | `backend/app/services/report_service.py` | Open |
| T-05 | Router `description`/docstring text (A2) | `backend/app/api/v1/reports.py` | Open |
| T-06 | Re-point FR-US-01 tests to `currencies[0]`; TC-17/TC-18 tests rewritten to their superseding outcome and cite TC-40/TC-37 (A11) | `backend/tests/integration/test_fr_us_01_view_summary_report.py` | Open |
| T-07 | Integration tests TC-29…TC-49 from `test_cases.md` | `backend/tests/integration/test_fr_us_03_summary_per_currency.py` | Open |
| T-08 | **UI fast-track:** `SummaryReportRead`/`CurrencySummary` types; `Dashboard.tsx` one block per currency with the Element IDs above, empty state, `reportCurrency` removed (A12) | `mobile/src/api/types.ts`, `mobile/src/components/wallet/Dashboard.tsx` | Open |
| T-09 | **UI fast-track:** e2e tests TC-50…TC-54 against the real backend | `mobile/e2e/home.spec.ts` | Open |
