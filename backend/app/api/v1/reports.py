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
