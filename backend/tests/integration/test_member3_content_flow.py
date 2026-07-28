from datetime import UTC, datetime
from decimal import Decimal

from sellpilot.core.security import hash_password
from sellpilot.db.models.commerce import Product, Shop
from sellpilot.db.models.user import User

TEST_PASSWORD = "CorrectHorseBattery1!"


async def _seed_content_flow(session_factory) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        user = User(
            username="member3-content-admin",
            password_hash=hash_password(TEST_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        shop = Shop(
            external_id="SHOP-CONTENT-E2E",
            name="Synthetic content evaluation shop",
            platform="shopee",
            mode="mock",
            is_active=True,
            source_type="simulated_experiment",
            is_mock_data=True,
            source_updated_at=now,
        )
        session.add_all([user, shop])
        await session.flush()
        session.add(
            Product(
                external_id="CONTENT-E2E-P1",
                shop_id=shop.id,
                source_shop_external_id=shop.external_id,
                title="Compact USB-C Hub",
                category_external_id="CAT-CONTENT",
                category_name="Consumer Electronics",
                description="A six-port USB-C hub for laptop and tablet workflows.",
                platform="shopee",
                site="Singapore",
                currency="SGD",
                price=Decimal("49.90"),
                cost=Decimal("20.00"),
                shipping_cost=Decimal("4.00"),
                sales_count=20,
                rating=Decimal("4.50"),
                review_count=10,
                favorite_count=3,
                status="active",
                source_type="simulated_experiment",
                is_mock_data=True,
                source_created_at=now,
                source_updated_at=now,
                collected_at=now,
            )
        )
        await session.commit()


async def _auth(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "member3-content-admin", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def test_content_generation_confirmation_version_and_restore_flow(client_bundle) -> None:
    client, _, session_factory, _ = client_bundle
    await _seed_content_flow(session_factory)
    headers = await _auth(client)

    generated = await client.post(
        "/api/v1/content-generation/generate",
        headers=headers,
        json={
            "product_id": "CONTENT-E2E-P1",
            "site": "sg",
            "target_language": "en",
            "audience": "remote workers",
            "selling_points": ["compact design", "easy to carry"],
            "keywords": ["USB-C", "compact"],
            "max_attempts": 3,
        },
    )
    assert generated.status_code == 200
    generation = generated.json()["data"]
    assert generation["provider"] == "offline_template"
    assert generation["result"]["quality"]["passed"] is True
    assert generation["result"]["content"]["generation_mode"] == "offline_template"

    payload = {
        "idempotency_key": "content-e2e-save-001",
        "generation": generation,
    }
    requested = await client.post(
        "/api/v1/content-generation/draft-confirmations",
        headers=headers,
        json=payload,
    )
    assert requested.status_code == 200
    confirmation = requested.json()["data"]
    assert confirmation["status"] == "pending"
    assert confirmation["execution_result"] is None

    repeated = await client.post(
        "/api/v1/content-generation/draft-confirmations",
        headers=headers,
        json=payload,
    )
    assert repeated.status_code == 200
    assert repeated.json()["data"]["id"] == confirmation["id"]

    confirmed = await client.post(
        f"/api/v1/confirmations/{confirmation['id']}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200
    execution = confirmed.json()["data"]
    assert execution["status"] == "succeeded"
    content_id = execution["execution_result"]["content_id"]

    versions = await client.get(
        f"/api/v1/content-generation/contents/{content_id}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    version_data = versions.json()["data"]
    assert version_data["total"] == 1
    first_version = version_data["items"][0]
    assert first_version["fact_check_result"]["passed"] is True
    assert first_version["compliance_result"]["passed"] is True

    restore = await client.post(
        f"/api/v1/content-generation/contents/{content_id}/restore-confirmations",
        headers=headers,
        json={
            "idempotency_key": "content-e2e-restore-001",
            "version_id": first_version["id"],
        },
    )
    assert restore.status_code == 200
    restore_confirmation = restore.json()["data"]
    assert restore_confirmation["status"] == "pending"

    restored = await client.post(
        f"/api/v1/confirmations/{restore_confirmation['id']}/confirm",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["status"] == "succeeded"
    assert restored.json()["data"]["execution_result"]["version"] == 2

    final_versions = await client.get(
        f"/api/v1/content-generation/contents/{content_id}/versions",
        headers=headers,
    )
    assert final_versions.json()["data"]["total"] == 2
