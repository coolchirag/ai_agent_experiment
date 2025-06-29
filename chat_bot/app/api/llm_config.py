from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from cryptography.fernet import Fernet
import base64
import os

from app.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse,
    LLMProvidersResponse, LLMProviderInfo
)
from app.services.llm_factory import LLMFactory
from app.config import settings

router = APIRouter()

# Simple encryption for API keys (in production, use proper key management)
def get_encryption_key():
    """Get or create encryption key for API keys"""
    key_file = "encryption.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        return key

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key"""
    if not api_key:
        return ""
    
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key"""
    if not encrypted_key:
        return ""
    
    key = get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_key.encode()).decode()


@router.get("/providers", response_model=LLMProvidersResponse)
def get_providers():
    """Get available LLM providers and their information"""
    providers = LLMFactory.get_provider_info()
    return LLMProvidersResponse(providers=providers)


@router.get("/", response_model=List[LLMConfigResponse])
def get_llm_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's LLM configurations"""
    configs = (
        db.query(LLMConfig)
        .filter(LLMConfig.user_id == current_user.id)
        .all()
    )
    
    # Convert to response format (don't expose actual API keys)
    response_configs = []
    for config in configs:
        response_config = LLMConfigResponse(
            id=config.id,
            user_id=config.user_id,
            provider=config.provider,
            model_name=config.model_name,
            is_default=config.is_default,
            config_data=config.config_data,
            created_at=config.created_at,
            updated_at=config.updated_at,
            has_api_key=bool(config.api_key)
        )
        response_configs.append(response_config)
    
    return response_configs


@router.post("/", response_model=LLMConfigResponse)
def create_llm_config(
    config: LLMConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new LLM configuration"""
    # Validate provider and model
    if not LLMFactory.validate_provider_config(config.provider, config.model_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model {config.model_name} for provider {config.provider}"
        )
    
    # Check if user already has a config for this provider
    existing_config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.user_id == current_user.id,
            LLMConfig.provider == config.provider
        )
        .first()
    )
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration for {config.provider} already exists"
        )
    
    # If this is the first config or marked as default, make it default
    if config.is_default:
        # Remove default from other configs
        db.query(LLMConfig).filter(
            LLMConfig.user_id == current_user.id,
            LLMConfig.is_default == True
        ).update({"is_default": False})
    
    # Check if this is the user's first config
    user_configs_count = (
        db.query(LLMConfig)
        .filter(LLMConfig.user_id == current_user.id)
        .count()
    )
    
    is_default = config.is_default or user_configs_count == 0
    
    # Encrypt API key
    encrypted_api_key = encrypt_api_key(config.api_key) if config.api_key else None
    
    db_config = LLMConfig(
        user_id=current_user.id,
        provider=config.provider,
        api_key=encrypted_api_key,
        model_name=config.model_name,
        is_default=is_default,
        config_data=config.config_data
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return LLMConfigResponse(
        id=db_config.id,
        user_id=db_config.user_id,
        provider=db_config.provider,
        model_name=db_config.model_name,
        is_default=db_config.is_default,
        config_data=db_config.config_data,
        created_at=db_config.created_at,
        updated_at=db_config.updated_at,
        has_api_key=bool(db_config.api_key)
    )


@router.get("/{config_id}", response_model=LLMConfigResponse)
def get_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific LLM configuration"""
    config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.id == config_id,
            LLMConfig.user_id == current_user.id
        )
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    return LLMConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        model_name=config.model_name,
        is_default=config.is_default,
        config_data=config.config_data,
        created_at=config.created_at,
        updated_at=config.updated_at,
        has_api_key=bool(config.api_key)
    )


@router.put("/{config_id}", response_model=LLMConfigResponse)
def update_llm_config(
    config_id: int,
    config_update: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an LLM configuration"""
    config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.id == config_id,
            LLMConfig.user_id == current_user.id
        )
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    # Validate model if provided
    if config_update.model_name:
        if not LLMFactory.validate_provider_config(config.provider, config_update.model_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model {config_update.model_name} for provider {config.provider}"
            )
    
    # Handle default flag
    if config_update.is_default is True:
        # Remove default from other configs
        db.query(LLMConfig).filter(
            LLMConfig.user_id == current_user.id,
            LLMConfig.id != config_id,
            LLMConfig.is_default == True
        ).update({"is_default": False})
    
    # Update fields
    update_data = config_update.dict(exclude_unset=True, exclude={"api_key"})
    for field, value in update_data.items():
        setattr(config, field, value)
    
    # Handle API key separately (encrypt if provided)
    if config_update.api_key is not None:
        config.api_key = encrypt_api_key(config_update.api_key) if config_update.api_key else None
    
    db.commit()
    db.refresh(config)
    
    return LLMConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        model_name=config.model_name,
        is_default=config.is_default,
        config_data=config.config_data,
        created_at=config.created_at,
        updated_at=config.updated_at,
        has_api_key=bool(config.api_key)
    )


@router.delete("/{config_id}")
def delete_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an LLM configuration"""
    config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.id == config_id,
            LLMConfig.user_id == current_user.id
        )
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    db.delete(config)
    db.commit()
    
    return {"message": "Configuration deleted successfully"}


@router.post("/{config_id}/test")
def test_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Test an LLM configuration"""
    config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.id == config_id,
            LLMConfig.user_id == current_user.id
        )
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    if not config.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API key configured"
        )
    
    try:
        # Decrypt API key and test connection
        api_key = decrypt_api_key(config.api_key)
        llm_provider = LLMFactory.create_provider(
            provider_type=config.provider,
            api_key=api_key,
            model=config.model_name
        )
        
        # Test with a simple validation
        is_valid = llm_provider.validate_api_key()
        
        if is_valid:
            return {"status": "success", "message": "Configuration is valid"}
        else:
            return {"status": "error", "message": "Invalid API key or configuration"}
    
    except Exception as e:
        return {"status": "error", "message": f"Test failed: {str(e)}"}


@router.post("/{config_id}/set-default")
def set_default_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set a configuration as default"""
    config = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.id == config_id,
            LLMConfig.user_id == current_user.id
        )
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    # Remove default from all other configs
    db.query(LLMConfig).filter(
        LLMConfig.user_id == current_user.id,
        LLMConfig.id != config_id
    ).update({"is_default": False})
    
    # Set this config as default
    config.is_default = True
    db.commit()
    
    return {"message": "Configuration set as default"} 