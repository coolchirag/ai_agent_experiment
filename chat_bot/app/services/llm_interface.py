from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    finish_reason: Optional[str] = None


class LLMInterface(ABC):
    """Abstract interface for all LLM providers"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate a single response from the LLM"""
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the LLM"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider"""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate if the API key is valid"""
        pass
    
    def format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to provider-specific format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages] 