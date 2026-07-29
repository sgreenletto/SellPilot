from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.exceptions import ResourceNotFoundError
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.commerce import (
    InventoryResponse,
    LogisticsResponse,
    MessageResponse,
    OrderResponse,
    ProductResponse,
    ReturnRefundResponse,
)
from sellpilot.schemas.commerce_operations import (
    CandidateRequest,
    CandidateResponse,
    InventoryUpdateRequest,
    OperationRequest,
    PriceUpdateRequest,
    ProductDraftRequest,
    ProductImportRequest,
)
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.services.commerce_operations import CommerceOperationService
from sellpilot.services.commerce_query import CommerceQueryService

router = APIRouter()


@router.get("/selection-candidates", response_model=ApiResponse[list[CandidateResponse]])
async def list_selection_candidates(
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[list[CandidateResponse]]:
    data = await CommerceOperationService(session, settings).list_candidates(user.id)
    return success_response(
        [CandidateResponse.model_validate(item) for item in data], get_request_id(request)
    )


@router.post(
    "/selection-candidates/{product_id}/add-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_add_selection_candidate(
    product_id: str,
    payload: CandidateRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_candidate_change(
        product_id=product_id,
        add=True,
        title=payload.title,
        source_type=payload.source_type,
        is_mock_data=payload.is_mock_data,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/selection-candidates/{product_id}/remove-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_remove_selection_candidate(
    product_id: str,
    payload: CandidateRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_candidate_change(
        product_id=product_id,
        add=False,
        title=payload.title,
        source_type=payload.source_type,
        is_mock_data=payload.is_mock_data,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/products/draft-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_save_product_draft(
    payload: ProductDraftRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_product_draft(
        product=payload.product.model_dump(mode="json"),
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/products/import-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_import_products(
    payload: ProductImportRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_product_import(
        products=[item.model_dump(mode="json") for item in payload.products],
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.get("/products", response_model=ApiResponse[list[ProductResponse]])
async def list_products(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    status: str | None = None,
    site: str | None = None,
    shop_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[ProductResponse]]:
    data = await CommerceQueryService(session, settings).list_products(
        status=status, site=site, shop_id=shop_id, offset=offset, limit=limit
    )
    return success_response(
        [ProductResponse.model_validate(item) for item in data], get_request_id(request)
    )


@router.get("/products/{product_id}", response_model=ApiResponse[ProductResponse])
async def get_product(
    product_id: str,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ProductResponse]:
    data = await CommerceQueryService(session, settings).get_product(product_id)
    if not data:
        raise ResourceNotFoundError("Product not found")
    return success_response(ProductResponse.model_validate(data), get_request_id(request))


@router.get("/orders", response_model=ApiResponse[list[OrderResponse]])
async def list_orders(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    status: str | None = None,
    shop_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[OrderResponse]]:
    data = await CommerceQueryService(session, settings).list_orders(
        status=status, shop_id=shop_id, offset=offset, limit=limit
    )
    return success_response(
        [OrderResponse.model_validate(item) for item in data], get_request_id(request)
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[OrderResponse])
async def get_order(
    order_id: str,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[OrderResponse]:
    data = await CommerceQueryService(session, settings).get_order(order_id)
    if not data:
        raise ResourceNotFoundError("Order not found")
    return success_response(OrderResponse.model_validate(data), get_request_id(request))


@router.get(
    "/orders/{order_id}/logistics",
    response_model=ApiResponse[LogisticsResponse],
)
async def get_logistics(
    order_id: str,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[LogisticsResponse]:
    data = await CommerceQueryService(session, settings).get_logistics(order_id)
    if not data:
        raise ResourceNotFoundError("Logistics record not found")
    return success_response(LogisticsResponse.model_validate(data), get_request_id(request))


@router.get("/messages", response_model=ApiResponse[list[MessageResponse]])
async def list_messages(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    session_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> ApiResponse[list[MessageResponse]]:
    data = await CommerceQueryService(session, settings).list_messages(
        session_id=session_id, limit=limit
    )
    return success_response(
        [MessageResponse.model_validate(item) for item in data], get_request_id(request)
    )


@router.get("/inventory", response_model=ApiResponse[list[InventoryResponse]])
async def list_inventory(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    status: str | None = None,
    shop_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[InventoryResponse]]:
    data = await CommerceQueryService(session, settings).list_inventory(
        status=status, shop_id=shop_id, offset=offset, limit=limit
    )
    return success_response(
        [InventoryResponse.model_validate(item) for item in data], get_request_id(request)
    )


@router.get("/returns", response_model=ApiResponse[list[ReturnRefundResponse]])
async def list_returns(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    status: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[ReturnRefundResponse]]:
    data = await CommerceQueryService(session, settings).list_returns(
        status=status, offset=offset, limit=limit
    )
    return success_response(
        [ReturnRefundResponse.model_validate(item) for item in data],
        get_request_id(request),
    )


@router.post(
    "/products/{product_id}/publish-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_publish(
    product_id: str,
    payload: OperationRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_product_status(
        product_id=product_id,
        publish=True,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/products/{product_id}/unpublish-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_unpublish(
    product_id: str,
    payload: OperationRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_product_status(
        product_id=product_id,
        publish=False,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/products/{product_id}/price-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_price_update(
    product_id: str,
    payload: PriceUpdateRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_price_update(
        product_id=product_id,
        sku_id=payload.sku_id,
        price=payload.price,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


@router.post(
    "/products/{product_id}/inventory-request",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_inventory_update(
    product_id: str,
    payload: InventoryUpdateRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await CommerceOperationService(session, settings).request_inventory_update(
        product_id=product_id,
        sku_id=payload.sku_id,
        available_stock=payload.available_stock,
        idempotency_key=payload.idempotency_key,
        created_by=user.id,
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation), get_request_id(request)
    )


# ---- 客服统计 ----

@router.get(
    "/customer-service/stats",
    response_model=ApiResponse[dict],
)
async def get_customer_service_stats(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
) -> ApiResponse[dict]:
    """待处理客服会话统计。"""
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from sellpilot.db.models.commerce import CustomerSession

    total = await session.scalar(
        sa_select(func.count()).select_from(CustomerSession).where(
            CustomerSession.status == "open"
        )
    )
    return success_response(
        {"pending_count": total or 0},
        get_request_id(request),
    )
