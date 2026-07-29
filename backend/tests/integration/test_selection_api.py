from decimal import Decimal
from pathlib import Path

from sellpilot.core.security import hash_password
from sellpilot.db.models.user import User
from sellpilot.services.commerce_import import CommerceImportService
from tests.conftest import TEST_PASSWORD

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"


async def seed_selection_api(session_factory) -> None:
    async with session_factory() as session:
        session.add(
            User(
                username="selection-api-admin",
                password_hash=hash_password(TEST_PASSWORD),
                role="ADMIN",
                is_active=True,
            )
        )
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()


async def auth_headers(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "selection-api-admin", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def test_selection_api_full_authenticated_flow(client_bundle) -> None:
    client, _, session_factory, _ = client_bundle
    assert (await client.get("/api/v1/selection/candidates?site=sg")).status_code == 401

    await seed_selection_api(session_factory)
    headers = await auth_headers(client)

    candidates_response = await client.get(
        "/api/v1/selection/candidates",
        params={"site": "sg", "limit": 100},
        headers=headers,
    )
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()["data"]
    assert len(candidates) > 1
    assert all(item["site"] == "sg" and item["is_mock_data"] for item in candidates)

    analysis_response = await client.post(
        "/api/v1/selection/analyses",
        headers=headers,
        json={
            "site": "sg",
            "minimum_profit": "-1000000",
            "minimum_margin": "-1",
            "platform_fee_rate": "0.08",
            "other_costs": "0",
            "risk_preference": "balanced",
            "offset": 0,
            "limit": 100,
        },
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()["data"]
    assert analysis["status"] == "SUCCEEDED"
    assert analysis["ranked_count"] == len(candidates)
    assert all(Decimal(item["data_completeness"]) == Decimal("1") for item in analysis["results"])
    assert all(
        all(metric["score"] is not None for metric in item["metrics"].values())
        for item in analysis["results"]
    )

    product_ids = [item["product_id"] for item in analysis["results"][:2]]
    compare_response = await client.get(
        f"/api/v1/selection/analyses/{analysis['task_id']}/compare",
        params=[("product_id", product_id) for product_id in product_ids],
        headers=headers,
    )
    assert compare_response.status_code == 200
    assert [item["product_id"] for item in compare_response.json()["data"]] == product_ids

    export_response = await client.get(
        f"/api/v1/selection/analyses/{analysis['task_id']}/export",
        headers=headers,
    )
    assert export_response.status_code == 200
    exported = export_response.json()["data"]
    assert exported["filename"].endswith(".json")
    assert len(exported["checksum_sha256"]) == 64
    assert len(exported["task"]["results"]) == analysis["ranked_count"]
