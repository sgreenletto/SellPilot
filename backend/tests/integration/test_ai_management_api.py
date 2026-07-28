from sellpilot.core.security import hash_password
from sellpilot.db.models.user import User

PASSWORD = "CorrectHorseBattery1!"


async def test_ai_management_exposes_safe_runtime_and_real_evaluation(client_bundle) -> None:
    client, _, session_factory, _ = client_bundle
    async with session_factory() as session:
        session.add(
            User(
                username="ai-audit-admin",
                password_hash=hash_password(PASSWORD),
                role="ADMIN",
                is_active=True,
            )
        )
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "ai-audit-admin", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    runtime = await client.get("/api/v1/ai-management/model-runtime", headers=headers)
    assert runtime.status_code == 200
    runtime_data = runtime.json()["data"]
    assert "sk-" not in str(runtime_data).lower()
    assert runtime_data["provider"] == "offline_template"
    assert runtime_data["configured"] is True

    evaluation = await client.get("/api/v1/ai-management/evaluation/member3", headers=headers)
    assert evaluation.status_code == 200
    evaluation_data = evaluation.json()["data"]
    assert evaluation_data["dataset_version"] == "member3-eval-v1.0.0"
    assert evaluation_data["total_cases"] == 3
    assert 0 <= evaluation_data["pass_rate"] <= 1
    assert evaluation_data["failed_cases"] == (
        evaluation_data["total_cases"] - evaluation_data["passed_cases"]
    )

    prompts = await client.get("/api/v1/ai-management/prompts", headers=headers)
    assert prompts.status_code == 200
    assert prompts.json()["data"] == []
