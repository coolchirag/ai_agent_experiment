from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .chat import LLMProvider


class LLMConfigBase(BaseModel):
    provider: LLMProvider
    model_name: str = Field(..., max_length=100)
    is_default: bool = False
    config_data: Optional[Dict[str, Any]] = None


class LLMConfigCreate(LLMConfigBase):
    api_key: Optional[str] = None


class LLMConfigUpdate(BaseModel):
    model_name: Optional[str] = Field(None, max_length=100)
    api_key: Optional[str] = None
    is_default: Optional[bool] = None
    config_data: Optional[Dict[str, Any]] = None


class LLMConfigResponse(LLMConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    has_api_key: bool = False  # Don't expose actual API key
    
    class Config:
        from_attributes = True


class LLMProviderInfo(BaseModel):
    provider: LLMProvider
    name: str
    description: str
    models: List[str]
    default_model: str
    requires_api_key: bool = True


class LLMProvidersResponse(BaseModel):
    providers: List[LLMProviderInfo] 