"""Category DTOs (SDS §2.1; spec CM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), PF-03 (DTO projection),
NC-05 (enum serialisation).
"""

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.category import CategoryType


class CategoryCreate(BaseModel):
    """plan.md DTO block. No `user_id` field at all (plan.md A6, spec AC-07) —
    the owner comes only from `CurrentUserDep`; an extra `user_id` (or
    `icon`) key in the submitted JSON is silently ignored by Pydantic's
    default `BaseModel` behaviour, matching every existing schema in this
    codebase.
    """

    # Trimmed and required non-empty after trimming (spec AC-03, EC-02);
    # bounded at the column width (spec AC-04; plan.md A1).
    name: str = Field(min_length=1, max_length=100)

    # Closed enum, no case-folding, no trimming (plan.md A2; spec AC-05,
    # AC-06, EC-01, EC-06) — Pydantic's own enum-membership validation
    # rejects anything that is not exactly `"INCOME"` or `"EXPENSE"`.
    type: CategoryType

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """spec AC-03, EC-02: trimmed, and a trimmed-to-empty name still
        fails — matching `WalletCreate.name`'s exact technique. Opt-in per
        field, no model-wide `str_strip_whitespace`.
        """
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Category name cannot be empty or whitespace only")
        return trimmed


class CategoryUpdate(BaseModel):
    """Request DTO for PATCH /categories/{category_id} (CM-US-04). All three
    fields are independently optional (plan.md A1) -- None means "leave this
    field unchanged," including for icon (A12): there is no way to submit a
    null that clears an existing icon, only a new non-blank string that
    replaces it. At least one field must be given a non-None value (A1) or
    the request is refused -- the first multi-field optional update contract
    in this codebase.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: CategoryType | None = None
    # Bounded at 50, not name's 100 -- an icon is a short identifier/slug,
    # not a label (plan.md A11). No format constraint beyond length and
    # non-blankness (A11).
    icon: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Only runs when a value was actually submitted -- Pydantic skips a
        field validator for a field left at its None default. Same
        trim-then-reject-blank technique as CategoryCreate.validate_name.
        """
        if v is None:
            return v
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Category name cannot be empty or whitespace only")
        return trimmed

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str | None) -> str | None:
        """Same technique as validate_name, applied to icon (plan.md A11)."""
        if v is None:
            return v
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Category icon cannot be empty or whitespace only")
        return trimmed

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "CategoryUpdate":
        """spec AC-05, FR-04 (plan.md A1) -- the one cross-field rule
        Pydantic cannot express on a single field, the same class of rule
        TM-US-02 A7 already needed for date_from/date_to ordering.
        """
        if self.name is None and self.type is None and self.icon is None:
            raise ValueError("At least one of name, type, or icon must be provided.")
        return self


class CategoryRead(BaseModel):
    """SDS §2.2 (as aligned). Now five fields (plan.md A6) -- icon added for
    the first time; None until a category has one set via CM-US-04's own
    PATCH. Reused unchanged across create, list, and update responses.
    """

    id: str
    user_id: str
    name: str
    type: CategoryType
    icon: str | None


class CategoryListRead(BaseModel):
    """New envelope (CM-US-02 plan.md A2) — mirrors `WalletListRead`
    (WM-US-02 plan.md A2) and `TransactionListRead` (TM-US-02 plan.md A8).
    `CategoryRead`'s own fields are reused unchanged as the per-item shape —
    no other entity's data folded in. Now five fields per item since CM-US-04
    extended `CategoryRead` with `icon` (plan.md A6); this envelope itself
    needed no change to carry it through.
    """

    items: list[CategoryRead]
    total: int
    page: int
    page_size: int
