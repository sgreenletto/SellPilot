from sellpilot.core.security import hash_password
from sellpilot.db.models.user import User

PASSWORD = "CorrectHorseBattery1!"


async def test_product_translation_contract_and_confirmation_boundary(client_bundle) -> None:
    client, _, session_factory, _ = client_bundle
    async with session_factory() as session:
        session.add(
            User(
                username="translation-admin",
                password_hash=hash_password(PASSWORD),
                role="ADMIN",
                is_active=True,
            )
        )
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "translation-admin", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    status = await client.get("/api/v1/product-translations/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["data"] == {
        "configured": False,
        "provider": None,
        "supported_languages": [
            "en",
            "zh-CN",
            "zh-TW",
            "ms",
            "id",
            "th",
            "vi",
            "tl",
            "pt-BR",
        ],
    }

    requested = await client.post(
        "/api/v1/product-translations/requests",
        headers=headers,
        json={
            "source": {
                "product_id": "PROD0001",
                "source_language": "en",
                "title": "Compact USB-C Hub",
                "description": "Six-port hub for laptop workflows.",
                "category_name": "Consumer Electronics",
                "specifications": [{"name": "Ports", "value": "6-in-1"}],
            },
            "target_languages": ["zh-CN"],
            "fields": ["title", "description", "category_name", "specifications"],
            "idempotency_key": "translation-contract-001",
        },
    )
    assert requested.status_code == 200
    task = requested.json()["data"]
    assert task["status"] == "pending_confirmation"
    assert task["results"] == []

    fetched = await client.get(
        f"/api/v1/product-translations/tasks/{task['task_id']}", headers=headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["data"]["confirmation_task_id"] == task["confirmation_task_id"]
