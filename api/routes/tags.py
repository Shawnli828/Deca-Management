from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import AccountIssueRequest, AccountTagRequest, ProductTagRequest
from server_modules.services.tag_runtime import (
    account_issues_payload,
    account_tags_payload,
    add_account_issue,
    add_account_tag,
    create_product_tag,
    delete_account_issue,
    delete_account_tag,
    delete_product_tag,
    product_tags_payload,
)

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/account-tags")
def get_account_tags(request: Request, account_ids: str = ""):
    require_dashboard_auth(request)
    ids = [item.strip() for item in account_ids.split(",") if item.strip()]
    return account_tags_payload(ids)


@router.post("/api/account-tags")
def post_account_tags(request: Request, payload: AccountTagRequest = Body(default_factory=AccountTagRequest)):
    require_dashboard_auth(request)
    try:
        return add_account_tag(payload.account_id, payload.tag)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/account-tags/delete")
def post_account_tags_delete(request: Request, payload: AccountTagRequest = Body(default_factory=AccountTagRequest)):
    require_dashboard_auth(request)
    try:
        return delete_account_tag(payload.account_id, payload.tag)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/account-issues")
def get_account_issues(request: Request, account_ids: str = ""):
    require_dashboard_auth(request)
    ids = [item.strip() for item in account_ids.split(",") if item.strip()]
    return account_issues_payload(ids)


@router.post("/api/account-issues")
def post_account_issues(request: Request, payload: AccountIssueRequest = Body(default_factory=AccountIssueRequest)):
    require_dashboard_auth(request)
    try:
        return add_account_issue(payload.account_id, payload.issue)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/account-issues/delete")
def post_account_issues_delete(request: Request, payload: AccountIssueRequest = Body(default_factory=AccountIssueRequest)):
    require_dashboard_auth(request)
    try:
        return delete_account_issue(payload.account_id, payload.issue)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/product-tags")
def get_product_tags(request: Request, product_code: str = ""):
    require_dashboard_auth(request)
    try:
        return product_tags_payload(product_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/product-tags")
def post_product_tags(request: Request, payload: ProductTagRequest = Body(default_factory=ProductTagRequest)):
    require_dashboard_auth(request)
    try:
        return create_product_tag(payload.product_code, payload.tag)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/product-tags/delete")
def post_product_tags_delete(request: Request, payload: ProductTagRequest = Body(default_factory=ProductTagRequest)):
    require_dashboard_auth(request)
    try:
        return delete_product_tag(payload.product_code, payload.tag, payload.remove_assignments)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
