from typing import Dict, Type, List
from .llm_interface import LLMInterface
from .llm_providers import OpenAIProvider, AnthropicProvider, GoogleProvider, GroqProvider
from app.schemas.chat import LLMProvider
from app.schemas.llm_config import LLMProviderInfo


class LLMFactory:
    """Factory class for creating LLM provider instances"""
    
    _providers: Dict[str, Type[LLMInterface]] = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider,
        LLMProvider.GOOGLE: GoogleProvider,
        LLMProvider.GROQ: GroqProvider,
    }
    
    _provider_info: Dict[str, LLMProviderInfo] = {
        LLMProvider.OPENAI: LLMProviderInfo(
            provider=LLMProvider.OPENAI,
            name="OpenAI",
            description="GPT models from OpenAI including GPT-4 and GPT-3.5",
            models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"],
            default_model="gpt-3.5-turbo",
            requires_api_key=True
        ),
        LLMProvider.ANTHROPIC: LLMProviderInfo(
            provider=LLMProvider.ANTHROPIC,
            name="Anthropic",
            description="Claude models from Anthropic",
            models=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            default_model="claude-3-sonnet-20240229",
            requires_api_key=True
        ),
        LLMProvider.GOOGLE: LLMProviderInfo(
            provider=LLMProvider.GOOGLE,
            name="Google",
            description="Gemini models from Google",
            models=[
                "gemini-2.5-pro",                # Most advanced reasoning model
                "gemini-2.5-flash",              # Best price-performance
                "gemini-2.5-flash-lite-preview-06-17", # Most cost-efficient, high throughput
                "gemini-2.0-flash",              # Next-gen multimodal
                "gemini-2.0-flash-lite",         # Cost-efficient, low latency
                "gemini-1.5-pro",                # Mid-size, complex reasoning
                "gemini-1.5-flash",              # Fast, versatile
                "gemini-1.5-flash-8b"            # Small, high volume, lower intelligence
            ],
            default_model="gemini-2.5-pro",
            requires_api_key=True
        ),
        LLMProvider.GROQ: LLMProviderInfo(
            provider=LLMProvider.GROQ,
            name="Groq",
            description="Fast inference models on Groq hardware",
            models=["mixtral-8x7b-32768", "llama2-70b-4096", "gemma-7b-it"],
            default_model="mixtral-8x7b-32768",
            requires_api_key=True
        ),
    }
    
    @classmethod
    def create_provider(
        self,
        provider_type: str,
        api_key: str,
        model: str = None
    ) -> LLMInterface:
        """Create an instance of the specified LLM provider"""
        if provider_type not in self._providers:
            raise ValueError(f"Unsupported provider: {provider_type}")
        
        provider_class = self._providers[provider_type]
        
        # Use default model if not specified
        if not model:
            model = self._provider_info[provider_type].default_model
        
        return provider_class(api_key=api_key, model=model)
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported provider names"""
        return list(cls._providers.keys())
    
    @classmethod
    def get_provider_info(cls, provider_type: str = None) -> LLMProviderInfo | List[LLMProviderInfo]:
        """Get information about a specific provider or all providers"""
        if provider_type:
            if provider_type not in cls._provider_info:
                raise ValueError(f"Unsupported provider: {provider_type}")
            return cls._provider_info[provider_type]
        
        return list(cls._provider_info.values())
    
    @classmethod
    def validate_provider_config(cls, provider_type: str, model: str) -> bool:
        """Validate if the provider supports the specified model"""
        if provider_type not in cls._provider_info:
            return False
        
        provider_info = cls._provider_info[provider_type]
        return model in provider_info.models 