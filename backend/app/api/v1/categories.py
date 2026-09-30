"""Category Management endpoints (SDS §5.4.1 CM-US-01, §5.4.2 CM-US-02)."""

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.category import CategoryCreate, CategoryListRead, CategoryRead
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    description=(
        "Creates a new category owned by the authenticated caller, with a "
        "name and a type of exactly INCOME or EXPENSE."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def create_category(
    payload: CategoryCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> CategoryRead:
    result = category_service.create_category(
        db,
        owner=current_user,
        name=payload.name,
        category_type=payload.type,
    )
    db.commit()
    return result


@router.get(
    "",
    response_model=CategoryListRead,
    status_code=status.HTTP_200_OK,
    summary="List the caller's categories",
    description=(
        "Returns every category owned by the authenticated caller, paginated, "
        "with an accurate total scoped to that caller."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def list_categories(
    db: DbDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> CategoryListRead:
    """Pure read — no `db.commit()` (plan.md A4)."""
    return category_service.list_categories(db, owner=current_user, page=page, page_size=page_size)
