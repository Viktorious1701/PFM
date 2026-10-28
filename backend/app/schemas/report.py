"""Financial Reporting DTOs (SDS §5.7.1 FR-US-01; spec FR-US-01, FR-US-03).

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


class CurrencySummaryRead(BaseModel):
    """One currency's figures (spec FR-US-03 AC-01, FR-03, FR-04; plan.md
    FR-US-03 A9). Every amount here is in `currency` and never mixed with
    another currency's amounts (FR-US-03 BR-02). Carries exactly the four
    figures FR-US-01 put at the top level; `net_savings` may be negative
    (FR-US-01 AC-09, BR-04). `currency` is serialised as stored -- WM-US-01
    FR-05 already guarantees three uppercase letters.
    """

    currency: str
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    top_categories: list[CategorySpendingRead]


class SummaryReportRead(BaseModel):
    """FR-API-01 response (plan.md FR-US-03 A2, A9): the period, and one entry
    per currency the caller holds or used (FR-US-03 FR-05), ordered by code
    (A4). `currencies` is always present -- `[]` when nothing qualifies
    (FR-US-03 AC-09), never null or omitted. Not in SDS's DTO registry
    (§6.2.1) -- FR-US-01 plan.md A11.
    """

    period: date
    currencies: list[CurrencySummaryRead]
