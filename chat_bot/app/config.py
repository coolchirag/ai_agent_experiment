from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_chat"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # MCP Server Configuration
    MCP_CONFIG_PATH: str = "mcp_config.json"
    
    # Application settings
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 