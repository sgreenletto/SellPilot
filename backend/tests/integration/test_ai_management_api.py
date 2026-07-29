from sellpilot.core.security import hash_password
from sellpilot.db.models.model_management import PromptTemplate, PromptVersion
from sellpilot.db.models.user import User

PASSWORD = "CorrectHorseBattery1!"


async def test_ai_management_exposes_safe_runtime_and_real_evaluation(client_bundle) -> None:
    client, _, session_factory, settings = client_bundle
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


async def test_prompt_changes_require_confirmation_and_preserve_versions(client_bundle) -> None:
    client, _, session_factory, _ = client_bundle
    async with session_factory() as session:
        user = User(
            username="prompt-admin",
            password_hash=hash_password(PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        template = PromptTemplate(
            key="selection-explanation",
            name="Selection explanation",
            purpose="Explain deterministic selection scores.",
            task_type="PRODUCT_SELECTION",
            language="zh-CN",
            status="ACTIVE",
            created_by=user.id,
        )
        session.add(template)
        await session.flush()
        session.add(
            PromptVersion(
                template_id=template.id,
                version=1,
                content="Explain only the supplied deterministic metrics.",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                model_config={"temperature": 0},
                change_summary="Initial version",
                checksum="a" * 64,
                created_by=user.id,
            )
        )
        template_id = template.id
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "prompt-admin", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    version_payload = {
        "content": "Explain supplied deterministic metrics and cite every numeric value.",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "model_parameters": {"temperature": 0},
        "change_summary": "Require numeric citations",
        "idempotency_key": "prompt-version-0001",
    }
    request = await client.post(
        f"/api/v1/ai-management/prompts/{template_id}/versions",
        headers=headers,
        json=version_payload,
    )
    assert request.status_code == 200
    confirmation = request.json()["data"]
    assert confirmation["status"] == "pending"

    before = await client.get(
        f"/api/v1/ai-management/prompts/{template_id}/versions", headers=headers
    )
    assert len(before.json()["data"]) == 1

    confirmed = await client.post(
        f"/api/v1/confirmations/{confirmation['id']}/confirm", headers=headers
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "succeeded"
    after = await client.get(
        f"/api/v1/ai-management/prompts/{template_id}/versions", headers=headers
    )
    assert [item["version"] for item in after.json()["data"]] == [2, 1]

    status_request = await client.post(
        f"/api/v1/ai-management/prompts/{template_id}/status",
        headers=headers,
        json={"status": "INACTIVE", "idempotency_key": "prompt-status-0001"},
    )
    status_confirmation = status_request.json()["data"]
    await client.post(f"/api/v1/confirmations/{status_confirmation['id']}/confirm", headers=headers)
    templates = await client.get("/api/v1/ai-management/prompts", headers=headers)
    assert templates.json()["data"][0]["status"] == "INACTIVE"
