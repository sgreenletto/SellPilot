from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.repositories.replenishment import (
    ReplenishmentRepository,
    ReplenishmentSourceRow,
)
from sellpilot.schemas.replenishment import (
    ReplenishmentAnalysisOutput,
    ReplenishmentAnalysisRequest,
    ReplenishmentRecommendation,
    ReplenishmentSummary,
)

FOUR_PLACES = Decimal("0.0001")


class ReplenishmentService:
    """确定性补货计算核心；不调用大模型，也不修改库存。"""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = ReplenishmentRepository(session)

    async def analyze(
        self,
        request: ReplenishmentAnalysisRequest,
        *,
        now: datetime | None = None,
    ) -> ReplenishmentAnalysisOutput:
        """读取指定窗口的 SKU 数据，计算建议并返回带版本的结构化结果。"""
        analysis_time = now or datetime.now(UTC)
        rows = await self.repository.list_source_rows(
            shop_external_id=request.shop_external_id,
            sales_since=analysis_time - timedelta(days=request.analysis_days),
        )
        recommendations = [self.calculate_recommendation(row, request) for row in rows]
        # 汇总始终基于全部 SKU，列表可按请求只展示存在补货缺口的 SKU。
        visible = (
            [item for item in recommendations if item.recommended_quantity > 0]
            if request.only_replenishment
            else recommendations
        )
        return ReplenishmentAnalysisOutput(
            shop_external_id=request.shop_external_id,
            analysis_days=request.analysis_days,
            lead_time_days=request.lead_time_days,
            safety_factor=request.safety_factor,
            formula_version="replenishment-v1.0.0",
            summary=ReplenishmentSummary(
                analyzed_skus=len(recommendations),
                replenishment_skus=sum(item.recommended_quantity > 0 for item in recommendations),
                critical_skus=sum(item.risk_level == "critical" for item in recommendations),
                recommended_units=sum(item.recommended_quantity for item in recommendations),
            ),
            recommendations=visible,
            is_mock_data=all(item.is_mock_data for item in recommendations),
        )

    @staticmethod
    def calculate_recommendation(
        row: ReplenishmentSourceRow,
        request: ReplenishmentAnalysisRequest,
    ) -> ReplenishmentRecommendation:
        """根据销量、提前期和安全系数计算单个 SKU 的补货建议。"""
        # 日均销量 = 分析周期内非取消订单销量 / 分析天数。
        average = (Decimal(row.units_sold) / Decimal(request.analysis_days)).quantize(FOUR_PLACES)
        # 目标库存 = ceil(日均销量 * 补货提前期 * 安全系数)。
        demand_target = (
            average * Decimal(request.lead_time_days) * request.safety_factor
        ).to_integral_value(rounding=ROUND_CEILING)
        target_stock = int(demand_target)
        # 建议补货量不会为负数；当前库存已覆盖目标时返回 0。
        recommended = max(target_stock - row.available_stock, 0)
        # 零销量无法定义可售天数，使用 None 避免除零并明确表达“无近期需求”。
        days_of_supply = (
            (Decimal(row.available_stock) / average).quantize(FOUR_PLACES) if average > 0 else None
        )
        # 有销量且库存无法覆盖提前期属于严重风险；仅有缺口则为预警。
        # 静态 safety_stock 不直接进入公式，只作为阈值复核证据。
        if average > 0 and (
            row.available_stock == 0
            or (days_of_supply is not None and days_of_supply <= Decimal(request.lead_time_days))
        ):
            risk_level = "critical"
        elif recommended > 0:
            risk_level = "warning"
        else:
            risk_level = "healthy"
        reason = (
            f"{request.analysis_days}日销量{row.units_sold}件，日均{average}件；"
            f"按{request.lead_time_days}天提前期和{request.safety_factor}安全系数，"
            f"目标库存{target_stock}件，当前可用{row.available_stock}件。"
        )
        if (
            recommended == 0
            and row.available_stock <= row.safety_stock
            and days_of_supply is not None
        ):
            reason += (
                f"虽低于静态预警阈值{row.safety_stock}件，但可覆盖约"
                f"{days_of_supply}天，当前无需补货，建议复核阈值。"
            )
        return ReplenishmentRecommendation(
            product_id=row.product_id,
            product_title=row.product_title,
            sku_id=row.sku_id,
            seller_sku=row.seller_sku,
            site=row.site,
            available_stock=row.available_stock,
            safety_stock=row.safety_stock,
            units_sold=row.units_sold,
            average_daily_sales=average,
            days_of_supply=days_of_supply,
            target_stock=target_stock,
            recommended_quantity=recommended,
            risk_level=risk_level,
            reason=reason,
            is_mock_data=row.is_mock_data,
        )
