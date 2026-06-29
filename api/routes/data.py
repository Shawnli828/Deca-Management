from fastapi import APIRouter, Body, Header, HTTPException, Request

from api.schemas.requests import DataUpdateRequest, GrowthSyncProductRequest, GrowthSyncProductsRequest
from api.schemas.responses import (
    BusinessMaterialReportResponse,
    DataQueryResponse,
    DataResponse,
    DatabaseRelationalResponse,
    FlexibleResponse,
    GrowthDashboardResponse,
    OkDataResponse,
    RecordsResponse,
)
from server_modules.services.data_runtime import (
    ai_materials_payload,
    business_material_report_payload,
    connect_db,
    database_snapshot,
    data_query_payload,
    enriched_data,
    growth_dashboard_payload,
    init_relational_schema,
    product_registry_payload,
    relational_table_counts,
    reset_data as reset_data_payload,
    save_data,
    sync_party_a_growth_snapshots,
    sync_product_growth_snapshots,
    sync_products_growth_snapshots,
    using_postgres,
)

from .shared import (
    cron_authorized,
    query_as_lists,
    require_dashboard_auth,
    require_data_query_auth,
    require_materials_api_key,
)


router = APIRouter()


def _growth_codes_from_query(value: str):
    codes = []
    for item in str(value or "").split(","):
        code = item.strip().upper()
        if code and code not in codes:
            codes.append(code)
    return codes


@router.get("/api/data", response_model=DataResponse)
def get_data(request: Request):
    require_dashboard_auth(request)
    return {"data": enriched_data()}


@router.post("/api/data", response_model=OkDataResponse)
def post_data(request: Request, payload: DataUpdateRequest = Body(default_factory=DataUpdateRequest)):
    require_dashboard_auth(request)
    data = payload.data
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected { data: [...] }")

    save_data(data)
    return {"ok": True, "data": enriched_data(data)}


@router.get("/api/database", response_model=FlexibleResponse)
def get_database(request: Request):
    require_dashboard_auth(request)
    return database_snapshot()


@router.get("/api/database/relational", response_model=DatabaseRelationalResponse)
def get_relational_database(request: Request):
    require_dashboard_auth(request)
    with connect_db() as conn:
        init_relational_schema(conn)
        return {
            "ok": True,
            "database_backend": "postgres" if using_postgres() else "sqlite",
            "tables": relational_table_counts(conn),
        }


@router.get("/api/product-registry", response_model=FlexibleResponse)
def get_product_registry(request: Request):
    require_dashboard_auth(request)
    return product_registry_payload()


@router.post("/api/reset", response_model=OkDataResponse)
def reset_data(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "data": reset_data_payload()}


@router.get("/api/ai/materials", response_model=FlexibleResponse)
def get_ai_materials(request: Request, authorization: str | None = Header(default=None)):
    require_materials_api_key(authorization)
    return ai_materials_payload(query_as_lists(request))


@router.get("/api/data/query", response_model=DataQueryResponse)
def get_data_query(request: Request, authorization: str | None = Header(default=None)):
    require_data_query_auth(request, authorization)
    try:
        return data_query_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Data query failed: {error}") from error


@router.get("/api/growth", response_model=GrowthDashboardResponse)
def get_growth_dashboard(request: Request):
    require_dashboard_auth(request)
    try:
        return growth_dashboard_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/business-material-report", response_model=BusinessMaterialReportResponse)
def get_business_material_report(request: Request):
    require_dashboard_auth(request)
    try:
        return business_material_report_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/growth/sync-product", response_model=RecordsResponse)
def post_growth_sync_product(request: Request, payload: GrowthSyncProductRequest = Body(default_factory=GrowthSyncProductRequest)):
    require_dashboard_auth(request)
    try:
        records = sync_product_growth_snapshots(
            payload.product_code.strip(),
            payload.days,
        )
        return {"ok": True, "count": len(records), "records": records}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/growth/sync-products", response_model=FlexibleResponse)
def post_growth_sync_products(request: Request, payload: GrowthSyncProductsRequest = Body(default_factory=GrowthSyncProductsRequest)):
    require_dashboard_auth(request)
    try:
        result = sync_products_growth_snapshots(
            payload.product_codes,
            payload.days,
        )
        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/growth/sync-products", response_model=FlexibleResponse, operation_id="get_growth_sync_products")
def get_growth_sync_products(request: Request, product_codes: str = "", days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        return sync_products_growth_snapshots(_growth_codes_from_query(product_codes), days)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/growth/sync-party-a", response_model=FlexibleResponse, operation_id="get_growth_sync_party_a")
def get_growth_sync_party_a(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        return sync_party_a_growth_snapshots(days)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/growth/sync-db", response_model=FlexibleResponse, operation_id="get_growth_sync_db")
def get_growth_sync_db(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        return sync_products_growth_snapshots(("DB",), days)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/growth/sync-dm", response_model=FlexibleResponse, operation_id="get_growth_sync_dm")
def get_growth_sync_dm(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        return sync_products_growth_snapshots(("DM",), days)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/growth/sync-dl", response_model=FlexibleResponse, operation_id="get_growth_sync_dl")
def get_growth_sync_dl(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        return sync_products_growth_snapshots(("DL",), days)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
