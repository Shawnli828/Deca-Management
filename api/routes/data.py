from fastapi import APIRouter, Body, Header, HTTPException, Request

from api.schemas.requests import DataUpdateRequest, GrowthSyncProductRequest
from server_modules.services.data_runtime import (
    ai_materials_payload,
    business_material_report_payload,
    connect_db,
    database_snapshot,
    data_query_payload,
    enriched_data,
    growth_dashboard_payload,
    init_relational_schema,
    relational_table_counts,
    reset_data as reset_data_payload,
    save_data,
    sync_product_growth_snapshots,
    using_postgres,
)

from .shared import (
    query_as_lists,
    require_dashboard_auth,
    require_data_query_auth,
    require_materials_api_key,
)


router = APIRouter()


@router.get("/api/data")
def get_data(request: Request):
    require_dashboard_auth(request)
    return {"data": enriched_data()}


@router.post("/api/data")
def post_data(request: Request, payload: DataUpdateRequest = Body(default_factory=DataUpdateRequest)):
    require_dashboard_auth(request)
    data = payload.data
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected { data: [...] }")

    save_data(data)
    return {"ok": True, "data": enriched_data(data)}


@router.get("/api/database")
def get_database(request: Request):
    require_dashboard_auth(request)
    return database_snapshot()


@router.get("/api/database/relational")
def get_relational_database(request: Request):
    require_dashboard_auth(request)
    with connect_db() as conn:
        init_relational_schema(conn)
        return {
            "ok": True,
            "database_backend": "postgres" if using_postgres() else "sqlite",
            "tables": relational_table_counts(conn),
        }


@router.post("/api/reset")
def reset_data(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "data": reset_data_payload()}


@router.get("/api/ai/materials")
def get_ai_materials(request: Request, authorization: str | None = Header(default=None)):
    require_materials_api_key(authorization)
    return ai_materials_payload(query_as_lists(request))


@router.get("/api/data/query")
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


@router.get("/api/growth")
def get_growth_dashboard(request: Request):
    require_dashboard_auth(request)
    try:
        return growth_dashboard_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/business-material-report")
def get_business_material_report(request: Request):
    require_dashboard_auth(request)
    try:
        return business_material_report_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/growth/sync-product")
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
