"""Budget Management endpoints (SDS §5.5.1 BM-US-01)."""

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.budget import BudgetCreate, BudgetListRead, BudgetRead
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post(
    "",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a budget",
    description=(
        "Creates a new budget scoped to one of the authenticated caller's own "
        "wallets and one of their own categories, with a positive monthly "
        "amount limit. The period is always the first day of the current "
        "calendar month, computed by the system."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        404: {"description": "BUDGET_WALLET_NOT_FOUND / BUDGET_CATEGORY_NOT_FOUND"},
        409: {"description": "BUDGET_ALREADY_EXISTS"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def create_budget(
    payload: BudgetCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> BudgetRead:
    result = budget_service.create_budget(
        db,
        owner=current_user,
        wallet_id=payload.wallet_id,
        category_id=payload.category_id,
        amount_limit=payload.amount_limit,
    )
    db.commit()
    return result


@router.get(
    "",
    response_model=BudgetListRead,
    status_code=status.HTTP_200_OK,
    summary="List the caller's active budgets",
    description=(
        "Returns every budget owned by the authenticated caller whose period "
        "is the current calendar month, paginated, each carrying its current "
        "amount spent and progress percentage."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def list_budgets(
    db: DbDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> BudgetListRead:
    """Pure read — no `db.commit()` (A10)."""
    return budget_service.list_budgets(db, owner=current_user, page=page, page_size=page_size)
