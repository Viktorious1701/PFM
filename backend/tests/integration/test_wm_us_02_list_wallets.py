"""WM-US-02 — List Wallets.

One test per test case in specs/003-wallet-management/test_cases.md
(TC-23..TC-39). Names state what the test proves, not what it calls.

`_create_wallet` seeds preconditions through the real `POST /api/v1/wallets`
endpoint (WM-US-01, already implemented) rather than inserting rows directly —
every TC in this file describes wallets "created via POST /api/v1/wallets",
and going through the real endpoint also means each wallet's `id` is whatever
the server actually assigned, which TC-32/TC-38's ordering assertions depend
on (QF-06: the expected order must be computed from the ids creation calls
actually returned, not assumed).

TC-30/TC-31/TC-39 need two distinct authenticated owners; this file reuses the
`normal_user`/`admin_user` fixtures for that (nothing in WM-US-02 cares which
role each caller has except TC-39, which specifically needs one of them to be
ADMIN — constitution SEC-08, spec EC-04).

TC-32/TC-38 assert the returned order equals the created wallets' own `id`
values sorted ascending as plain strings — computed independently in the test
from the ids the creation calls actually returned — and each asserts the
creation order does not already coincidentally match that sorted order, so
neither test could pass by coincidence if the implementation actually sorted
by insertion order instead of `id` (QF-06's assertion technique).
"""

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import Settings
from app.models.user import UserModel

WALLETS_URL = "/api/v1/wallets"


# --- helpers --------------------------------------------------------------


def _create_wallet(
    client: TestClient, headers: dict[str, str], **overrides: object
) -> dict[str, object]:
    """POST a wallet through the real WM-US-01 endpoint and return its body.

    Asserts 201 itself so a seeding failure fails loudly at the seeding line,
    not as a confusing downstream assertion in the test that depends on it.
    """
    payload: dict[str, object] = {
        "name": "Main Checking",
        "type": "BANK",
        "currency": "USD",
        "initial_balance": "100.00",
    }
    payload.update(overrides)
    response = client.post(WALLETS_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


def _expired_token(user: UserModel, settings: Settings) -> str:
    return security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=-1,  # already past
        algorithm=settings.jwt_algorithm,
    )


# --- TC-23/TC-24: the happy path envelope -----------------------------------


def test_authenticated_user_lists_every_wallet_they_own_with_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-23: three wallets of different types/currencies, created via POST
    -> 200; items contains all three, each carrying id, user_id (caller's),
    name, type, currency, balance; total is 3.
    """
    _create_wallet(client, user_headers, name="Cash", type="CASH", currency="USD")
    _create_wallet(client, user_headers, name="Bank", type="BANK", currency="EUR")
    _create_wallet(client, user_headers, name="Credit", type="CREDIT", currency="GBP")

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    for item in body["items"]:
        assert item["user_id"] == normal_user.id
    assert {item["name"] for item in body["items"]} == {"Cash", "Bank", "Credit"}


def test_response_item_exposes_exactly_six_fields_wrapped_in_paginated_envelope(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-24: top-level body exposes exactly items, total, page, page_size;
    each entry in items exposes exactly id, user_id, name, type, currency,
    balance — no more, no field this story invents.
    """
    _create_wallet(client, user_headers)

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert len(body["items"]) == 1
    assert set(body["items"][0].keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "currency",
        "balance",
    }


# --- TC-25: the empty case ---------------------------------------------------


def test_user_with_no_wallets_yet_receives_empty_list_and_zero_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-25: no wallets owned -> 200, not an error; items is empty, total is
    0.
    """
    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-26/TC-27: authentication ---------------------------------------------


def test_unauthenticated_or_invalid_credential_caller_is_denied_with_401(
    client: TestClient, normal_user: UserModel, settings: Settings
) -> None:
    """TC-26: no `Authorization` header, and separately an expired token,
    both -> 401 NOT_AUTHENTICATED; no items returned either way.
    """
    no_auth = client.get(WALLETS_URL)
    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in no_auth.json()

    expired = client.get(
        WALLETS_URL,
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in expired.json()


def test_credentials_are_evaluated_before_any_query_parameter(client: TestClient) -> None:
    """TC-27: an out-of-range `page` from an unauthenticated caller still
    answers 401, not 422 — mirrors UM-US-03 TC-61's ordering.
    """
    response = client.get(WALLETS_URL, params={"page": 0})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-28/TC-29: pagination defaults and explicit values --------------------


def test_default_page_is_1_of_size_25_with_accurate_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-28: no page/page_size supplied -> page 1, page_size 25, all three
    wallets returned, total 3.
    """
    for _ in range(3):
        _create_wallet(client, user_headers)

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert len(body["items"]) == 3
    assert body["total"] == 3


def test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-29: page=2, page_size=2 over 5 wallets -> that page's two wallets
    and total=5.
    """
    for _ in range(5):
        _create_wallet(client, user_headers)

    response = client.get(WALLETS_URL, params={"page": 2, "page_size": 2}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


# --- TC-30/TC-31: ownership scoping, items and total alike (QF-05) -----------


def test_a_user_only_ever_sees_their_own_wallets_never_another_users(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
) -> None:
    """TC-30: A (two wallets) and B (three wallets) -> A's request returns
    exactly A's two wallets, none of B's three; total is 2, not 5 (assertion
    technique per QF-05).
    """
    _create_wallet(client, user_headers, name="A-1")
    _create_wallet(client, user_headers, name="A-2")
    _create_wallet(client, admin_headers, name="B-1")
    _create_wallet(client, admin_headers, name="B-2")
    _create_wallet(client, admin_headers, name="B-3")

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["user_id"] == normal_user.id
    assert {item["name"] for item in body["items"]} == {"A-1", "A-2"}


def test_reported_total_counts_only_callers_own_wallets_even_when_smaller(
    client: TestClient, user_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    """TC-31: A (no wallets) and B (four wallets) -> A's request returns
    items empty and total 0 — not 4, and not any count reflecting B's
    wallets (assertion technique per QF-05).
    """
    for i in range(4):
        _create_wallet(client, admin_headers, name=f"B-{i}")

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-32: stable order matching ids sorted ascending (QF-06) ---------------


def test_list_is_returned_in_stable_order_matching_ids_sorted_ascending(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-32: five wallets -> the returned order equals the wallets' own ids
    sorted ascending as strings, computed independently from the ids the
    creation calls actually returned — not merely "the same order both
    times" (assertion technique per QF-06). Requested twice, with nothing
    created/changed/removed in between, to also prove repeatability.
    """
    created_ids = [_create_wallet(client, user_headers, name=f"W{i}")["id"] for i in range(5)]
    expected_order = sorted(created_ids)
    assert expected_order != created_ids, (
        "fixture coincidence: creation order already matches ascending id "
        "order — this run cannot distinguish id-order from insertion-order"
    )

    first = client.get(WALLETS_URL, headers=user_headers)
    second = client.get(WALLETS_URL, headers=user_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["id"] for item in first.json()["items"]] == expected_order
    assert [item["id"] for item in second.json()["items"]] == expected_order


# --- TC-33/TC-34/TC-35: pagination boundary validation -----------------------


@pytest.mark.parametrize("bad_page", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page: object
) -> None:
    """TC-33: page in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming `page`;
    no items returned.
    """
    response = client.get(WALLETS_URL, params={"page": bad_page}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page" in _fields(body)
    assert "items" not in body


@pytest.mark.parametrize("bad_page_size", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_size_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page_size: object
) -> None:
    """TC-34: page_size in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming
    `page_size`; no items returned.
    """
    response = client.get(WALLETS_URL, params={"page_size": bad_page_size}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)
    assert "items" not in body


def test_a_page_size_above_the_maximum_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-35: page_size=101 -> 422 VALIDATION_ERROR naming `page_size`; the
    request is not silently capped at 100.
    """
    response = client.get(WALLETS_URL, params={"page_size": 101}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)


# --- TC-36/TC-37: boundary values that ARE accepted --------------------------


def test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-36: page=5, page_size=25 over 3 wallets -> 200, not 404; items
    empty, total still 3.
    """
    for _ in range(3):
        _create_wallet(client, user_headers)

    response = client.get(WALLETS_URL, params={"page": 5, "page_size": 25}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3


def test_a_page_size_of_exactly_100_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-37: page_size=100 -> 200. The cap is a ceiling, not a target: only
    101 (TC-35) is rejected.
    """
    response = client.get(WALLETS_URL, params={"page_size": 100}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


# --- TC-38: cross-page completeness, no duplicate, no gap (QF-06) -----------


def test_paging_through_every_page_returns_every_wallet_exactly_once_in_stable_order(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-38: five wallets, created in an order not already matching
    ascending id order, paged with page_size=2 across page=1,2,3 -> the
    concatenation of all pages' items contains every wallet exactly once, no
    duplicate, no gap, in the same ascending-id order TC-32 established
    (assertion technique per QF-06).
    """
    created_ids = [_create_wallet(client, user_headers, name=f"W{i}")["id"] for i in range(5)]
    expected_order = sorted(created_ids)
    assert expected_order != created_ids

    seen: list[str] = []
    for page in (1, 2, 3):
        response = client.get(
            WALLETS_URL, params={"page": page, "page_size": 2}, headers=user_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        seen.extend(item["id"] for item in body["items"])

    assert len(seen) == 5
    assert len(set(seen)) == 5
    assert seen == expected_order


# --- TC-39: ADMIN role grants no extra visibility here (QF-07) --------------


def test_admin_role_caller_who_also_owns_a_wallet_sees_only_their_own(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    admin_user: UserModel,
) -> None:
    """TC-39: an ADMIN who owns one wallet, and a second User who owns two of
    their own -> the ADMIN's request returns exactly the ADMIN's own one
    wallet, never either of the other User's; total is 1 (assertion
    technique per QF-07).
    """
    _create_wallet(client, admin_headers, name="Admin Wallet")
    _create_wallet(client, user_headers, name="Other-1")
    _create_wallet(client, user_headers, name="Other-2")

    response = client.get(WALLETS_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["user_id"] == admin_user.id
    assert body["items"][0]["name"] == "Admin Wallet"
