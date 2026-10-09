"""CM-US-03 — View a Category.

One test per test case in specs/004-category-management/test_cases.md
(TC-64..TC-73). Names state what the test proves, not what it calls.

Categories are always seeded through the real `POST /api/v1/categories`
endpoint (CM-US-01, already implemented), never inserted directly — the
`_create_category` helper is imported from `test_cm_us_04_update_category.py`,
the same precedent `test_tm_us_03_view_transaction.py` set by importing its
own prerequisites from `test_tm_us_02_list_transactions.py`.

TC-66/TC-72 compare the full response body of an ownership-mismatch case
against a genuinely-nonexistent-id case and assert they are identical, not
merely both 404 — the QF-14 technique, directly mirroring CM-US-04
QF-09/TC-44 and WM-US-03 QF-12/TC-63/TC-69.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.user import UserModel
from tests.integration.test_cm_us_04_update_category import _create_category

CATEGORIES_URL = "/api/v1/categories"


# --- helpers ----------------------------------------------------------------


def _url(category_id: str) -> str:
    return f"{CATEGORIES_URL}/{category_id}"


# --- TC-64: the happy path, full detail ---------------------------------------


def test_an_authenticated_user_views_a_category_they_own(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-64: name "Groceries"/type "EXPENSE"/icon "shopping-cart" -> 200;
    body carries id (the category's own), user_id (the caller's own), name,
    type, icon exactly as created.

    `icon` has no field on `CategoryCreate` (CM-US-01 A6/EC-05) -- it is set
    through the real `PATCH` endpoint (CM-US-04), the only way a category of
    this story's fixture ever gets one.
    """
    category = _create_category(client, user_headers, name="Groceries", type="EXPENSE")
    patched = client.patch(
        _url(str(category["id"])), json={"icon": "shopping-cart"}, headers=user_headers
    )
    assert patched.status_code == 200

    response = client.get(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == category["id"]
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Groceries"
    assert body["type"] == "EXPENSE"
    assert body["icon"] == "shopping-cart"


# --- TC-65: no such category at all ------------------------------------------


def test_a_category_id_matching_no_category_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-65: a well-formed id matching no category -> 404 CATEGORY_NOT_FOUND."""
    response = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"


# --- TC-66: another User's category collapses to the identical outcome (QF-14)


def test_another_users_category_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """TC-66: B owns a category, A owns nothing of the kind; A requests B's
    category -> 404, and error_code/message/details are all identical to a
    genuinely nonexistent id's response (QF-14).
    """
    b_category = _create_category(client, admin_headers, name="B's Category")

    not_owned = client.get(_url(str(b_category["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert not_owned.json() == not_found.json()


# --- TC-67: authentication -----------------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    """TC-67: no Authorization header, against an existing category belonging
    to some other, real User -> 401 NOT_AUTHENTICATED.
    """
    other_category = _create_category(client, admin_headers, name="Someone Else's Category")

    response = client.get(_url(str(other_category["id"])))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-68: malformed reference gets the same outcome as unknown-but-well-formed


def test_a_malformed_category_reference_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-68: GET /categories/not-a-real-id -> 404 CATEGORY_NOT_FOUND,
    identical to a well-formed but nonexistent id's response.
    """
    malformed = client.get(_url("not-a-real-id"), headers=user_headers)
    unknown = client.get(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-69: no role elevation for ADMIN ---------------------------------------


def test_an_admin_role_caller_cannot_view_another_users_category(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
) -> None:
    """TC-69: an ADMIN caller requests a category owned by a different, real
    User -> 404 CATEGORY_NOT_FOUND — the same outcome any non-ADMIN caller
    would get; no role grants visibility through this endpoint.
    """
    others_category = _create_category(client, user_headers, name="Member's Category")

    response = client.get(_url(str(others_category["id"])), headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"


# --- TC-70: an absent icon is not an error -------------------------------------


def test_a_category_with_no_icon_ever_set_still_views_successfully(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-70: a category created with name/type only, no icon ever submitted
    -> 200; icon is null — not an empty string, not an error.
    """
    category = _create_category(client, user_headers, name="Salary", type="INCOME")

    response = client.get(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert "icon" in body
    assert body["icon"] is None


# --- TC-71: exact response shape ----------------------------------------------


def test_the_response_exposes_exactly_the_five_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-71: the response body's keys are exactly id, user_id, name, type,
    icon — no more, and no data belonging to any other User.
    """
    category = _create_category(client, user_headers)

    response = client.get(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {"id", "user_id", "name", "type", "icon"}


# --- TC-72: owning a category never grants access to someone else's ----------


def test_a_caller_who_owns_a_different_category_cannot_view_another_users_category(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """TC-72: A owns a category of their own, B owns a separate one; A
    requests B's category -> 404, identical to a genuinely nonexistent id's
    response (QF-14) — owning a category of their own gives A no access to
    B's.
    """
    _create_category(client, user_headers, name="A's Category")
    b_category = _create_category(client, admin_headers, name="B's Category")

    response = client.get(_url(str(b_category["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert response.json() == not_found.json()


# --- TC-73: credentials are checked before the lookup -------------------------


def test_credentials_are_evaluated_before_the_category_reference_is_looked_up(
    client: TestClient,
) -> None:
    """TC-73: an unauthenticated caller requests a category id that matches
    no category in the system -> 401 NOT_AUTHENTICATED, not 404.
    """
    response = client.get(_url(str(uuid4())))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
