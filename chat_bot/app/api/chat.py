from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import json
import asyncio
import logging

from app.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.chat import Chat, Message
from app.models.llm_config import LLMConfig
from app.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    MessageCreate, MessageResponse, ChatStreamRequest
)
from app.services.llm_interface import LLMMessage
from app.services.llm_factory import LLMFactory
from app.config import settings
from app.services.mcp_integration import mcp_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
def create_chat(
    chat: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat"""
    # Validate provider and model
    if not LLMFactory.validate_provider_config(chat.llm_provider, chat.model_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model {chat.model_name} for provider {chat.llm_provider}"
        )
    
    db_chat = Chat(
        title=chat.title,
        user_id=current_user.id,
        llm_provider=chat.llm_provider,
        model_name=chat.model_name,
        temperature=chat.temperature,
        max_tokens=chat.max_tokens,
        system_prompt=chat.system_prompt
    )
    
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    
    return db_chat


@router.get("/", response_model=List[ChatListResponse])
def get_chats(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's chats with pagination"""
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(desc(Chat.updated_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Add message count to each chat
    chat_responses = []
    for chat in chats:
        message_count = db.query(func.count(Message.id)).filter(Message.chat_id == chat.id).scalar()
        chat_response = ChatListResponse(
            id=chat.id,
            title=chat.title,
            llm_provider=chat.llm_provider,
            model_name=chat.model_name,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            message_count=message_count
        )
        chat_responses.append(chat_response)
    
    return chat_responses


@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat with all messages"""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return chat


@router.put("/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a chat"""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Update fields
    update_data = chat_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chat, field, value)
    
    db.commit()
    db.refresh(chat)
    
    return chat


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat"""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully"}


@router.post("/{chat_id}/messages", response_model=MessageResponse)
def add_message(
    chat_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a message to a chat"""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    db_message = Message(
        chat_id=chat_id,
        role=message.role,
        content=message.content,
        message_metadata=message.message_metadata
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_message


@router.post("/{chat_id}/stream")
async def stream_chat(
    chat_id: int,
    request: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Stream chat with LLM and tool use support"""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    api_key = None
    if chat.llm_provider == "openai":
        api_key = settings.OPENAI_API_KEY
    elif chat.llm_provider == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
    elif chat.llm_provider == "google":
        api_key = settings.GOOGLE_API_KEY
    elif chat.llm_provider == "groq":
        api_key = settings.GROQ_API_KEY
    if not api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No API key configured for {chat.llm_provider}")
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .all()
    )
    llm_messages = []
    if chat.system_prompt:
        llm_messages.append(LLMMessage(role="system", content=chat.system_prompt))
    for msg in messages:
        llm_messages.append(LLMMessage(role=msg.role, content=msg.content))
    # --- MCP context injection ---
    enabled_servers = mcp_service.get_enabled_servers()
    mcp_context = {
        "servers": [
            {
                "name": s.name,
                "description": s.description,
                "tools": s.tools
            }
            for s in enabled_servers.values()
        ]
    }
    # --- End MCP context injection ---
    try:
        llm_provider = LLMFactory.create_provider(
            provider_type=chat.llm_provider,
            api_key=api_key,
            model=chat.model_name
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initialize LLM provider: {str(e)}")
    try:
        # --- Tool call loop ---
        final_response = None
        tool_call_chain = []
        current_messages = llm_messages.copy()
        while True:
            response = await llm_provider.generate_response(
                messages=current_messages,
                temperature=request.temperature or chat.temperature,
                max_tokens=request.max_tokens or chat.max_tokens,
                mcp_context=mcp_context
            )
            # Check if response requests a tool call (assume response.content is a dict if tool call is needed)
            if isinstance(response.content, dict) and response.content.get("tool_call"):
                tool_call = response.content["tool_call"]
                tool_call_chain.append(tool_call)
                # Find the server/tool
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                server = next((s for s in enabled_servers.values() if any(t["name"] == tool_name for t in s.tools)), None)
                if not server:
                    raise HTTPException(status_code=500, detail=f"Tool server for '{tool_name}' not found or not enabled.")
                # Simulate tool call (replace with actual tool call logic)
                tool_result = {"result": f"Simulated result for {tool_name} with args {tool_args}"}
                # Add tool result as a message
                current_messages.append(LLMMessage(role="tool", content=json.dumps({"tool_name": tool_name, "result": tool_result})))
                continue  # Loop again, send tool result to LLM
            else:
                final_response = response
                break
        # Save assistant message
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=final_response.content if hasattr(final_response, "content") else str(final_response)
        )
        db.add(assistant_message)
        db.commit()
        return {"content": final_response.content, "done": True, "tool_calls": tool_call_chain}
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating response: {str(e)}")


@router.websocket("/{chat_id}/ws")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Validate token and get user
            token = message_data.get("token")
            if not token:
                await websocket.send_text(json.dumps({"error": "Token required"}))
                continue
            
            try:
                from app.services.auth import AuthService
                current_user = AuthService.get_current_user(db, token)
            except Exception:
                await websocket.send_text(json.dumps({"error": "Invalid token"}))
                continue
            
            # Get chat
            chat = (
                db.query(Chat)
                .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
                .first()
            )
            
            if not chat:
                await websocket.send_text(json.dumps({"error": "Chat not found"}))
                continue
            
            # Process message and stream response
            user_content = message_data.get("message", "")
            if not user_content:
                await websocket.send_text(json.dumps({"error": "Message content required"}))
                continue
            
            # Add user message to database
            user_message = Message(
                chat_id=chat_id,
                role="user",
                content=user_content
            )
            db.add(user_message)
            db.commit()
            
            # Send user message confirmation
            await websocket.send_text(json.dumps({
                "type": "user_message",
                "content": user_content
            }))
            
            # Get LLM provider and stream response
            try:
                llm_config = (
                    db.query(LLMConfig)
                    .filter(
                        LLMConfig.user_id == current_user.id,
                        LLMConfig.provider == chat.llm_provider
                    )
                    .first()
                )
                
                if not llm_config or not llm_config.api_key:
                    await websocket.send_text(json.dumps({
                        "error": f"No API key configured for {chat.llm_provider}"
                    }))
                    continue
                
                llm_provider = LLMFactory.create_provider(
                    provider_type=chat.llm_provider,
                    api_key=llm_config.api_key,
                    model=chat.model_name
                )
                
                # Get chat history and convert to LLM format
                messages = (
                    db.query(Message)
                    .filter(Message.chat_id == chat_id)
                    .order_by(Message.created_at)
                    .all()
                )
                
                llm_messages = []
                if chat.system_prompt:
                    llm_messages.append(LLMMessage(role="system", content=chat.system_prompt))
                
                for msg in messages:
                    llm_messages.append(LLMMessage(role=msg.role, content=msg.content))
                
                assistant_content = ""
                
                # Stream response
                async for chunk in llm_provider.stream_response(
                    messages=llm_messages,
                    temperature=chat.temperature,
                    max_tokens=chat.max_tokens
                ):
                    assistant_content += chunk
                    await websocket.send_text(json.dumps({
                        "type": "assistant_chunk",
                        "content": chunk
                    }))
                
                # Save assistant response
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=assistant_content
                )
                db.add(assistant_message)
                db.commit()
                
                # Send completion signal
                await websocket.send_text(json.dumps({
                    "type": "assistant_complete",
                    "content": assistant_content
                }))
                
            except Exception as e:
                logger.error(f"Error in websocket chat: {e}")
                await websocket.send_text(json.dumps({
                    "error": f"Failed to generate response: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for chat {chat_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close() 