from typing import Any

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class DataUpdateRequest(BaseModel):
    data: list[Any] | None = None


class GrowthSyncProductRequest(BaseModel):
    product_code: str = ""
    days: int = 30


class GrowthSyncProductsRequest(BaseModel):
    product_codes: list[str] = Field(default_factory=list)
    days: int = 30


class PublishCheckStateRequest(BaseModel):
    state: dict[str, Any] | None = None


class ReelfarmConfigRequest(BaseModel):
    api_key: str = ""


class ApiKeyCreateRequest(BaseModel):
    name: str = ""


class ApiKeyRevokeRequest(BaseModel):
    id: str = ""


class AccountTagRequest(BaseModel):
    account_id: str = ""
    tag: str = ""


class AccountIssueRequest(BaseModel):
    account_id: str = ""
    issue: str = ""


class ProductTagRequest(BaseModel):
    product_code: str = ""
    tag: str = ""
    remove_assignments: bool = True


class ReelfarmSyncPrefixRequest(BaseModel):
    prefix: str = ""
    product_id: str = ""
    country_id: str = ""
    concept_id: str = ""
    product_code: str = ""
    country_code: str = ""


class ReelfarmSyncCountryRequest(BaseModel):
    prefix: str = ""
    product_id: str = ""
    country_id: str = ""
    product_code: str = ""
    country_code: str = ""


class MuseonSyncCountryRequest(BaseModel):
    product_id: str = ""
    country_id: str = ""
    product_code: str = ""
    country_code: str = ""
