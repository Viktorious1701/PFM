"""Category Management endpoints (SDS §5.4.1 CM-US-01)."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.category import CategoryCreate, CategoryRead
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
