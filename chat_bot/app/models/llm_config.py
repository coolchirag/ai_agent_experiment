from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # openai, anthropic, google, groq
    api_key = Column(Text)  # Encrypted API key
    # Suppress Pydantic warning: model_name is not a protected attribute in this context
    model_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    config_data = Column(JSON)  # Additional configuration parameters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="llm_configs")
    
    def __repr__(self):
        return f"<LLMConfig(id={self.id}, provider='{self.provider}', model='{self.model_name}')>" 