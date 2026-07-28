from datetime import UTC, datetime
from decimal import Decimal

from sellpilot.core.security import hash_password
from sellpilot.db.models.commerce import Product, Review, Shop
from sellpilot.db.models.user import User

TEST_PASSWORD = "CorrectHorseBattery1!"


async def seed_api_data(session_factory):
    now = datetime.now(UTC)
    async with session_factory() as session:
        user = User(
            username="review-api-admin",
            password_hash=hash_password(TEST_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        shop = Shop(
            external_id="SHOP-REV-API",
            name="Mock review API shop",
            platform="shopee",
            mode="mock",
            is_active=True,
            source_type="simulated_experiment",
            is_mock_data=True,
            source_updated_at=now,
        )
        session.add_all([user, shop])
        await session.flush()
        product = Product(
            external_id="REV-API-P1",
            shop_id=shop.id,
            source_shop_external_id=shop.external_id,
            title="Review API Product",
            category_external_id="CAT-REV",
            category_name="Review",
            description="Synthetic",
            platform="shopee",
            site="Singapore",
            currency="SGD",
            price=Decimal("50"),
            cost=Decimal("20"),
            shipping_cost=Decimal("5"),
            sales_count=10,
            rating=Decimal("2.00"),
            review_count=1,
            favorite_count=1,
            status="active",
            source_type="simulated_experiment",
            is_mock_data=True,
            source_created_at=now,
            source_updated_at=now,
            collected_at=now,
        )
        session.add(product)
        await session.flush()
        session.add(
            Review(
                external_id="REV-API-1",
                product_id=product.id,
                buyer_external_id="BUY-API-1",
                rating=2,
                content="Broken product and late delivery",
                content_zh="商品损坏且配送延迟",
                language="English",
                sentiment_hint="negative",
                issue_type="product",
                source_created_at=now,
                source_type="simulated_experiment",
                is_mock_data=True,
                source_updated_at=now,
            )
        )
        await session.commit()


async def auth(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "review-api-admin", "password": TEST_PASSWORD},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def test_review_analysis_api_requires_authentication(client_bundle):
    client, _, _, _ = client_bundle
    assert (await client.get("/api/v1/review-analysis/reviews?product_id=P1")).status_code == 401
    assert (
        await client.post(
            "/api/v1/review-analysis/analyses",
            json={"idempotency_key": "review-api-auth-001", "product_id": "P1"},
        )
    ).status_code == 401


async def test_review_analysis_api_create_run_query_and_evidence(client_bundle):
    client, _, session_factory, _ = client_bundle
    await seed_api_data(session_factory)
    headers = await auth(client)

    reviews = await client.get(
        "/api/v1/review-analysis/reviews",
        params={"product_id": "REV-API-P1", "site": "sg", "limit": 20},
        headers=headers,
    )
    assert reviews.status_code == 200
    assert reviews.json()["data"][0]["review_id"] == "REV-API-1"

    created = await client.post(
        "/api/v1/review-analysis/analyses",
        json={
            "idempotency_key": "review-api-create-001",
            "product_id": "REV-API-P1",
            "site": "sg",
            "batch_size": 1,
            "maximum_reviews": 10,
        },
        headers=headers,
    )
    assert created.status_code == 202
    payload = created.json()["data"]
    assert payload["status"] == "PENDING"

    pending = await client.get(
        f"/api/v1/review-analysis/analyses/{payload['analysis_id']}",
        headers=headers,
    )
    assert pending.status_code == 200
    assert pending.json()["data"]["quality"] is None
    assert pending.json()["data"]["progress"] == 0
    assert len(pending.json()["data"]["steps"]) == 3

    run = await client.post(
        f"/api/v1/review-analysis/analyses/{payload['analysis_id']}/run",
        headers=headers,
    )
    assert run.status_code == 200
    assert run.json()["data"]["status"] == "SUCCEEDED"
    assert run.json()["data"]["progress"] == 100
    assert run.json()["data"]["analysis_mode"] == "rule"
    assert run.json()["data"]["prompt_version"] is None
    assert run.json()["data"]["model_version"] is None

    evidence = await client.get(
        f"/api/v1/review-analysis/analyses/{payload['analysis_id']}/evidence",
        params={"page": 1, "page_size": 1},
        headers=headers,
    )
    assert evidence.status_code == 200
    assert evidence.json()["data"]["total"] >= 1
    assert len(evidence.json()["data"]["items"]) == 1
    evidence_item = evidence.json()["data"]["items"][0]

    filtered_evidence = await client.get(
        f"/api/v1/review-analysis/analyses/{payload['analysis_id']}/evidence",
        params={
            "page": 1,
            "page_size": 20,
            "evidence_type": "topic",
            "label": evidence_item["label"],
        },
        headers=headers,
    )
    assert filtered_evidence.status_code == 200
    assert filtered_evidence.json()["data"]["total"] >= 1
    assert all(
        item["evidence_type"] == "topic" and item["label"] == evidence_item["label"]
        for item in filtered_evidence.json()["data"]["items"]
    )

    improvement = await client.post(
        "/api/v1/product-improvement/reports",
        json={"analysis_id": payload["analysis_id"]},
        headers=headers,
    )
    assert improvement.status_code == 200
    report = improvement.json()["data"]
    assert report["source_product_id"] == "REV-API-P1"
    assert report["algorithm_version"] == "product-improvement-rule-v1.2.0"
    assert report["suggestions"]
    suggestion = report["suggestions"][0]
    assert suggestion["evidence_review_ids"]["items"] == ["REV-API-1"]

    accepted = await client.patch(
        f"/api/v1/product-improvement/suggestions/{suggestion['id']}",
        json={"status": "ACCEPTED", "title": "Accepted evidence-based improvement"},
        headers=headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "ACCEPTED"

    exported = await client.get(
        f"/api/v1/product-improvement/reports/{report['id']}/export",
        headers=headers,
    )
    assert exported.status_code == 200
    export_data = exported.json()["data"]
    assert export_data["format"] == "markdown"
    assert export_data["filename"].endswith(".md")
    assert "# REV-API-P1 产品改良报告" in export_data["content"]

    draft_request = await client.post(
        f"/api/v1/product-improvement/reports/{report['id']}/draft-confirmations",
        json={
            "idempotency_key": "review-api-improvement-draft-001",
            "site": "sg",
            "target_language": "en",
            "suggestion_ids": [suggestion["id"]],
        },
        headers=headers,
    )
    assert draft_request.status_code == 200
    confirmation = draft_request.json()["data"]
    assert confirmation["status"] == "pending"
    assert confirmation["execution_result"] is None
    repeated_request = await client.post(
        f"/api/v1/product-improvement/reports/{report['id']}/draft-confirmations",
        json={
            "idempotency_key": "review-api-improvement-draft-001",
            "site": "sg",
            "target_language": "en",
            "suggestion_ids": [suggestion["id"]],
        },
        headers=headers,
    )
    assert repeated_request.status_code == 200
    assert repeated_request.json()["data"]["id"] == confirmation["id"]

    confirmed = await client.post(
        f"/api/v1/confirmations/{confirmation['id']}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "succeeded"
    assert confirmed.json()["data"]["execution_result"]["status"] == "DRAFT"


async def test_review_analysis_api_validates_schema_and_missing_resources(client_bundle):
    client, _, session_factory, _ = client_bundle
    await seed_api_data(session_factory)
    headers = await auth(client)

    invalid = await client.post(
        "/api/v1/review-analysis/analyses",
        json={
            "idempotency_key": "review-api-invalid-001",
            "product_id": "REV-API-P1",
            "min_rating": 5,
            "max_rating": 1,
        },
        headers=headers,
    )
    assert invalid.status_code == 422

    missing = await client.post(
        "/api/v1/review-analysis/analyses",
        json={
            "idempotency_key": "review-api-missing-001",
            "product_id": "DOES-NOT-EXIST",
        },
        headers=headers,
    )
    assert missing.status_code == 404
