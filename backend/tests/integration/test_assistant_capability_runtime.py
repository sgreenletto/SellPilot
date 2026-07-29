from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from sellpilot.core.security import create_access_token
from sellpilot.db.models.commerce import CustomerMessage, CustomerSession
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.services.commerce_import import CommerceImportService
from sellpilot.services.knowledge_ingestion import KnowledgeIngestionService

DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "demo"
COMMERCE_DATA = DATA_ROOT / "shopee_mock"
POLICY_DATA = DATA_ROOT / "knowledge_mock" / "return-policy.md"


def auth_headers(user, settings) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


async def import_demo_data(session_factory, admin_user, *, knowledge: bool = False) -> None:
    async with session_factory() as session:
        await CommerceImportService(session).import_package(COMMERCE_DATA)
        if knowledge:
            await KnowledgeIngestionService(session).ensure_assistant_demo_policy(
                POLICY_DATA,
                created_by=admin_user.id,
            )
        await session.commit()


async def test_selection_assistant_searches_real_candidates_before_scoring(
    client_bundle,
    admin_user,
) -> None:
    client, _, session_factory, settings = client_bundle
    await import_demo_data(session_factory, admin_user)
    headers = auth_headers(admin_user, settings)

    created = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "分析新加坡站婴儿产品的选品机会",
            "execution_mode": "create_and_run",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["data"]["task_id"]
    task = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    result = task.json()["data"]["result"]
    assert task.json()["data"]["status"] == "succeeded"
    assert result["no_data"] is False
    assert result["candidate_search"]["count"] == 3
    assert result["analysis"]["ranked_count"] == 3
    assert [item["product_id"] for item in result["analysis"]["results"]] == [
        "PROD0102",
        "PROD0101",
        "PROD0103",
    ]
    assert all(
        Decimal(item["data_completeness"]) < Decimal("1") for item in result["analysis"]["results"]
    )
    steps = await client.get(f"/api/v1/tasks/{task_id}/steps", headers=headers)
    assert [item["node_name"] for item in steps.json()["data"]] == [
        "search_market_products",
        "select_selection_candidates",
        "score_product_opportunity",
        "finish_selection_success",
    ]


async def test_knowledge_assistant_returns_sources_and_refuses_unknown_basis(
    client_bundle,
    admin_user,
) -> None:
    client, _, session_factory, settings = client_bundle
    await import_demo_data(session_factory, admin_user, knowledge=True)
    headers = auth_headers(admin_user, settings)

    hit = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "在知识库中检索退货政策",
            "execution_mode": "create_and_run",
        },
    )
    miss = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "在知识库中检索火星仓库量子运输规则",
            "execution_mode": "create_and_run",
        },
    )

    assert hit.status_code == miss.status_code == 201
    hit_task = await client.get(
        f"/api/v1/tasks/{hit.json()['data']['task_id']}",
        headers=headers,
    )
    miss_task = await client.get(
        f"/api/v1/tasks/{miss.json()['data']['task_id']}",
        headers=headers,
    )
    assert hit_task.json()["data"]["result"]["sources"][0]["source_doc"] == (
        "knowledge_mock/return-policy.md"
    )
    assert hit_task.json()["data"]["result"]["no_reliable_source"] is False
    assert miss_task.json()["data"]["result"] == {
        "answer": "当前知识库中没有找到可靠依据。",
        "sources": [],
        "answer_mode": "no_reliable_source",
        "no_reliable_source": True,
    }


async def test_product_improvement_can_start_from_product_reviews(
    client_bundle,
    admin_user,
) -> None:
    client, _, session_factory, settings = client_bundle
    await import_demo_data(session_factory, admin_user)
    headers = auth_headers(admin_user, settings)

    created = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "根据商品 PROD-001 的评论生成产品改良建议",
            "execution_mode": "create_and_run",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["data"]["task_id"]
    task = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    report = task.json()["data"]["result"]["report"]
    assert task.json()["data"]["status"] == "succeeded"
    assert report["source_product_id"] == "PROD0001"
    assert len(report["suggestions"]) > 0
    steps = await client.get(f"/api/v1/tasks/{task_id}/steps", headers=headers)
    assert [item["node_name"] for item in steps.json()["data"]] == [
        "select_improvement_source",
        "analyze_reviews_for_improvement",
        "load_reviews",
        "analyze_reviews",
        "persist_results",
        "generate_product_improvement_plan",
    ]


async def test_customer_branches_and_mock_send_confirmation_are_audited_once(
    client_bundle,
    admin_user,
) -> None:
    client, _, session_factory, settings = client_bundle
    await import_demo_data(session_factory, admin_user, knowledge=True)
    headers = auth_headers(admin_user, settings)

    normal = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "为会话 SES00003 生成客服回复建议",
            "execution_mode": "create_and_run",
        },
    )
    high_risk = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "为会话 SES00004 生成退款投诉客服回复建议",
            "execution_mode": "create_and_run",
        },
    )
    send = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "为会话 SES00003 生成客服回复建议并模拟发送",
            "execution_mode": "create_and_run",
        },
    )

    assert normal.status_code == high_risk.status_code == 201
    normal_task = await client.get(
        f"/api/v1/tasks/{normal.json()['data']['task_id']}",
        headers=headers,
    )
    high_risk_task = await client.get(
        f"/api/v1/tasks/{high_risk.json()['data']['task_id']}",
        headers=headers,
    )
    assert normal_task.json()["data"]["result"]["draft"]["requires_human"] is False
    assert high_risk_task.json()["data"]["result"]["classification"]["branch"] == "human"
    assert high_risk_task.json()["data"]["result"]["draft"]["requires_human"] is True

    assert send.status_code == 202
    send_data = send.json()["data"]
    assert send_data["task_status"] == "waiting_confirmation"
    assert send_data["confirmation_required"] is True
    confirmation_id = send_data["confirmation_id"]
    task_id = send_data["task_id"]

    async with session_factory() as session:
        customer_session = await session.scalar(
            select(CustomerSession).where(CustomerSession.external_id == "SES00003")
        )
        before = await session.scalar(
            select(func.count())
            .select_from(CustomerMessage)
            .where(CustomerMessage.session_id == customer_session.id)
        )

    first = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    repeated = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    resumed = await client.post(f"/api/v1/tasks/{task_id}/resume", headers=headers)
    assert first.status_code == repeated.status_code == resumed.status_code == 200
    assert first.json()["data"]["status"] == repeated.json()["data"]["status"] == "succeeded"
    assert resumed.json()["data"]["status"] == "succeeded"

    async with session_factory() as session:
        after = await session.scalar(
            select(func.count())
            .select_from(CustomerMessage)
            .where(CustomerMessage.session_id == customer_session.id)
        )
        calls = list(
            (
                await session.execute(
                    select(ToolCall).where(
                        ToolCall.task_id == UUID(task_id),
                        ToolCall.tool_name == "mock_send_customer_reply",
                    )
                )
            ).scalars()
        )
        logs = list(
            (
                await session.execute(
                    select(OperationLog).where(
                        OperationLog.agent_task_id == UUID(task_id),
                        OperationLog.action == "tool.execute",
                    )
                )
            ).scalars()
        )
    assert after == before + 1
    assert len(calls) == 1
    assert calls[0].status == "succeeded"
    assert any(log.tool_call_id == calls[0].id for log in logs)
