import openai
import anthropic
from google import genai
from groq import Groq
from typing import List, Dict, Any, AsyncGenerator
import asyncio
import logging
from .llm_interface import LLMInterface, LLMMessage, LLMResponse
from google.genai import types
import json

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """OpenAI GPT provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_models = [
            "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]
    
    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        try:
            formatted_messages = self.format_messages(messages)
            mcp_context = kwargs.get("mcp_context")
            # For future: inject mcp_context into the payload if model supports it
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                # For OpenAI, mcp_context is not used, but pass for future
                **kwargs
            )
            content = response.choices[0].message.content
            # Tool call detection: if content looks like a tool call JSON, parse it
            if isinstance(content, str) and content.strip().startswith('{') and 'tool_call' in content:
                import json
                try:
                    content = json.loads(content)
                except Exception:
                    pass
            return LLMResponse(
                content=content,
                usage=response.usage.dict() if response.usage else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming is disabled. Use generate_response instead.")
    
    def get_available_models(self) -> List[str]:
        return self.default_models
    
    def get_provider_name(self) -> str:
        return "OpenAI"
    
    def validate_api_key(self) -> bool:
        try:
            # Simple validation by making a small request
            asyncio.run(self.client.models.list())
            return True
        except:
            return False


class AnthropicProvider(LLMInterface):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
    
    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        try:
            # Anthropic expects system message separately
            system_message = None
            formatted_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    formatted_messages.append({"role": msg.role, "content": msg.content})
            
            mcp_context = kwargs.get("mcp_context")
            # For future: inject mcp_context into the payload if model supports it
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=formatted_messages,
                # For Anthropic, mcp_context is not used, but pass for future
                **kwargs
            )
            
            content = response.content[0].text
            if isinstance(content, str) and content.strip().startswith('{') and 'tool_call' in content:
                import json
                try:
                    content = json.loads(content)
                except Exception:
                    pass
            return LLMResponse(
                content=content,
                usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
                model=response.model,
                finish_reason=response.stop_reason
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def stream_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming is disabled. Use generate_response instead.")
    
    def get_available_models(self) -> List[str]:
        return self.default_models
    
    def get_provider_name(self) -> str:
        return "Anthropic"
    
    def validate_api_key(self) -> bool:
        try:
            # Simple validation
            asyncio.run(self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            ))
            return True
        except:
            return False


class GoogleProvider(LLMInterface):
    """Google Gemini provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        super().__init__(api_key, model)
        self.client = genai.Client(api_key=api_key)
        self.default_models = ["gemini-2.5-pro", "gemini-pro", "gemini-pro-vision"]

    def _format_contents_for_gemini(self, messages: List[LLMMessage]) -> list:
        contents = []
        for msg in messages:
            parts = [types.Part.from_text(text=msg.content)]
            contents.append(types.Content(role=msg.role, parts=parts))
        return contents

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        try:
            mcp_context = kwargs.get("mcp_context")
            # Format messages as types.Content
            contents = self._format_contents_for_gemini(messages)
            # Prepare system_instruction if present
            system_instruction = None
            if mcp_context:
                # If mcp_context is a dict, convert to JSON string
                # if isinstance(mcp_context, dict):
                    # mcp_context = json.dumps(mcp_context)
                system_instruction = [types.Part.from_text(text=str(mcp_context))]
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="text/plain",
                system_instruction=system_instruction,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            # Extract text from response
            text = ""
            if hasattr(response, "text"):
                text = response.text
            elif hasattr(response, "candidates") and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                text += part.text
            return LLMResponse(
                content=text,
                usage=None,
                model=self.model,
                finish_reason=None
            )
        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise

    async def stream_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ):
        try:
            mcp_context = kwargs.get("mcp_context")
            if mcp_context:
                # Insert as system message at the start
                messages = [LLMMessage(role="system", content=mcp_context)] + messages
            contents = self._format_contents_for_gemini(messages)
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="text/plain",
            )
            stream = self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            for chunk in stream:
                if hasattr(chunk, "text"):
                    yield chunk.text
        except Exception as e:
            logger.error(f"Google API error (stream): {e}")
            raise

    def get_available_models(self) -> List[str]:
        return self.default_models

    def get_provider_name(self) -> str:
        return "Google"

    def validate_api_key(self) -> bool:
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="test")],
                )
            ]
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="text/plain",
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            return hasattr(response, "text")
        except Exception:
            return False


class GroqProvider(LLMInterface):
    """Groq provider implementation"""
    
    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        super().__init__(api_key, model)
        self.client = Groq(api_key=api_key)
        self.default_models = [
            "mixtral-8x7b-32768",
            "llama2-70b-4096",
            "gemma-7b-it"
        ]
    
    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        try:
            formatted_messages = self.format_messages(messages)
            mcp_context = kwargs.get("mcp_context")
            # For future: inject mcp_context into the payload if model supports it
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                # For Groq, mcp_context is not used, but pass for future
                **kwargs
            )
            content = response.choices[0].message.content
            if isinstance(content, str) and content.strip().startswith('{') and 'tool_call' in content:
                import json
                try:
                    content = json.loads(content)
                except Exception:
                    pass
            return LLMResponse(
                content=content,
                usage=response.usage.dict() if response.usage else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
    
    async def stream_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming is disabled. Use generate_response instead.")
    
    def get_available_models(self) -> List[str]:
        return self.default_models
    
    def get_provider_name(self) -> str:
        return "Groq"
    
    def validate_api_key(self) -> bool:
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except:
            return False 