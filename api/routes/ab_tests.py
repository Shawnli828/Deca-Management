from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import ABTestRequest
from api.schemas.responses import FlexibleResponse
from api.routes.shared import require_dashboard_auth
from server_modules.services import ab_test_service


router = APIRouter()


@router.get("/api/ab-tests", response_model=FlexibleResponse)
def get_ab_tests(request: Request):
    require_dashboard_auth(request)
    return ab_test_service.list_tests()


@router.post("/api/ab-tests", response_model=FlexibleResponse)
def post_ab_test(request: Request, payload: ABTestRequest = Body(default_factory=ABTestRequest)):
    require_dashboard_auth(request)
    try:
        return ab_test_service.create_test(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/ab-tests/{test_id}", response_model=FlexibleResponse)
def get_ab_test(request: Request, test_id: str):
    require_dashboard_auth(request)
    try:
        return ab_test_service.get_test(test_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.patch("/api/ab-tests/{test_id}", response_model=FlexibleResponse)
def patch_ab_test(request: Request, test_id: str, payload: ABTestRequest = Body(default_factory=ABTestRequest)):
    require_dashboard_auth(request)
    try:
        return ab_test_service.update_test(test_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.delete("/api/ab-tests/{test_id}", response_model=FlexibleResponse)
def delete_ab_test(request: Request, test_id: str):
    require_dashboard_auth(request)
    try:
        return ab_test_service.delete_test(test_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
