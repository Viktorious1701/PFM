"""Financial Reporting DTOs (SDS §5.7.1 FR-US-01; spec FR-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection -- see plan.md A6 for CategorySpendingRead's one
deliberate, narrow exception).
"""

from datetime import date
from decimal import Decimal

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
