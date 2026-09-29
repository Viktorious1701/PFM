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
