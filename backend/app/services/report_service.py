"""Financial Reporting service (spec FR-US-01, FR-US-03; plan.md FR-US-01
A1..A14, FR-US-03 A1..A13).

Constitution AR-01: the only place that decides what "the current period"
means, which currencies the report carries, in what order, and assembles the
response -- the repositories only know how to sum and group rows (AR-03).
"""

from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.models.transaction import TransactionType
from app.models.user import UserModel
from app.repositories import transaction_repo, wallet_repo
from app.schemas.report import CategorySpendingRead, CurrencySummaryRead, SummaryReportRead

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
    """spec FR-US-03 AC-01..AC-13 (and FR-US-01's rules within each currency).

    Period is always the current calendar month, read from the system clock
    once and applied to every currency alike (FR-US-03 AC-13) -- never from
    the request, because this endpoint accepts no input at all (FR-US-01
    plan.md A12). Every figure is computed within one wallet currency; no
    value is ever combined across currencies and nothing is converted
    (FR-US-03 BR-02).
    """
    period_start, period_end = _month_bounds(clock.utcnow().date())

    totals = transaction_repo.get_summary_totals_by_currency(
        db, user_id=owner.id, period_start=period_start, period_end=period_end
    )
    ranked = transaction_repo.get_top_expense_categories_by_currency(
        db,
        user_id=owner.id,
        period_start=period_start,
        period_end=period_end,
        limit=TOP_CATEGORIES_LIMIT,
    )
    held = wallet_repo.list_active_currencies(db, user_id=owner.id)

    # Held in an active wallet, or used in the period (FR-US-03 FR-05, A3);
    # ordered by code (A4). Every ranked currency also has an expense total,
    # so `ranked` never introduces a currency `totals` lacks.
    currencies = sorted(set(held) | {currency for currency, _type in totals})

    by_currency: dict[str, list[CategorySpendingRead]] = defaultdict(list)
    for currency, category_id, name, amount in ranked:  # already in rank order
        by_currency[currency].append(
            CategorySpendingRead(category_id=category_id, category_name=name, total_amount=amount)
        )

    zero = Decimal("0.00")  # an absent (currency, type) key means zero (A5)
    entries = []
    for currency in currencies:
        income = totals.get((currency, TransactionType.INCOME), zero)
        expenses = totals.get((currency, TransactionType.EXPENSE), zero)
        entries.append(
            CurrencySummaryRead(
                currency=currency,
                total_income=income,
                total_expenses=expenses,
                net_savings=income - expenses,
                top_categories=by_currency[currency],
            )
        )

    return SummaryReportRead(period=period_start.date(), currencies=entries)
