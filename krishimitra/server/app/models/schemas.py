from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Location(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None
    village_or_mandal: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Crop(BaseModel):
    crop_id: Optional[str] = None
    crop_name: Optional[str] = None
    growth_stage: str = "unknown"
    sowing_date: Optional[str] = None


class SoilInput(BaseModel):
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    nitrogen_unit: Optional[str] = None
    phosphorus: Optional[float] = None
    phosphorus_unit: Optional[str] = None
    potassium: Optional[float] = None
    potassium_unit: Optional[str] = None
    organic_carbon: Optional[float] = None
    organic_carbon_unit: Optional[str] = None
    soil_source: str = "user_entered"


class ContextIn(BaseModel):
    language: str = "en"
    location: Location = Field(default_factory=Location)
    crop: Crop = Field(default_factory=Crop)
    soil: Optional[SoilInput] = None
    weather: Optional[dict[str, Any]] = None   # weather response the UI actually holds
    mandi: Optional[dict[str, Any]] = None     # mandi response the UI actually holds


class AdvisoryRequest(BaseModel):
    question: str = ""
    context: ContextIn = Field(default_factory=ContextIn)


class AdvisoryContext(ContextIn):
    """Input of ai_service.generate_advisory (question + validated context)."""
    question: str


class ActionItem(BaseModel):
    action: str
    reason: str
    urgency: Literal["low", "medium", "high"]


class SourceInfo(BaseModel):
    name: str
    timestamp: Optional[str] = None
    status: str


class AdvisoryResponse(BaseModel):
    summary: str
    actions: list[ActionItem]
    data_used: list[str]
    cautions: list[str]
    sources: list[SourceInfo]
    generated_at: str
    mode: Literal["ai", "rule_based_demo"]
    language: str = "en"
    request_id: Optional[str] = None
    status: Literal["success", "partial"] = "success"
    missing_sources: list[str] = []


class AIServiceStatus(BaseModel):
    configured: bool
    model: Optional[str] = None
    client_ready: bool = False
    mode: Literal["ai", "rule_based_demo"] = "rule_based_demo"
    check: str = "not_checked"   # deep check: ok | model_not_found | auth_failed | unreachable | error
