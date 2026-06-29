from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlexibleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class OkResponse(FlexibleResponse):
    ok: bool = True


class AuthStatusResponse(FlexibleResponse):
    authenticated: bool


class HealthResponse(OkResponse):
    framework: str
    database_backend: str


class DataResponse(FlexibleResponse):
    data: Any


class OkDataResponse(OkResponse):
    data: Any


class DatabaseRelationalResponse(OkResponse):
    database_backend: str
    tables: dict[str, int] = Field(default_factory=dict)


class DataQueryResponse(OkResponse):
    resource: str
    data: Any
    filters: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = ""


class GrowthDashboardResponse(OkResponse):
    product_code: str
    report_timezone: str
    source_timezone: str
    date_from: str
    date_to: str
    latest: dict[str, Any] = Field(default_factory=dict)
    series: list[dict[str, Any]] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    generated_at: str


class BusinessMaterialReportResponse(OkResponse):
    product_code: str
    mode: str
    report_timezone: str
    source_timezone: str
    mixpanel: dict[str, Any] = Field(default_factory=dict)
    date_from: str
    date_to: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    generated_at: str


class RecordsResponse(OkResponse):
    count: int = 0
    records: list[dict[str, Any]] = Field(default_factory=list)


class ApiKeysResponse(OkResponse):
    keys: list[dict[str, Any]] = Field(default_factory=list)


class ApiKeyMutationResponse(OkResponse):
    record: dict[str, Any] = Field(default_factory=dict)


class FeishuPreviewResponse(OkResponse):
    report: dict[str, Any] = Field(default_factory=dict)
    message: str
    message_preview: str


class SyncResultResponse(OkResponse):
    source: str = ""
    status: str = ""
    product_code: str = ""
    country_code: str = ""
    records_count: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
