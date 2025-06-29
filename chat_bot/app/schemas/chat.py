from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatBase(BaseModel):
    title: str = Field(..., max_length=255)
    llm_provider: LLMProvider
    model_name: str = Field(..., max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    system_prompt: Optional[str] = None


class ChatCreate(ChatBase):
    pass


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    system_prompt: Optional[str] = None


class MessageBase(BaseModel):
    role: MessageRole
    content: str
    message_metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: int
    chat_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(ChatBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    id: int
    title: str
    llm_provider: LLMProvider
    model_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0
    
    class Config:
        from_attributes = True


class ChatStreamRequest(BaseModel):
    message: str
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000) 