from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from app.services.mcp_integration import mcp_service
from app.api.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/servers", response_model=Dict[str, Any])
def get_mcp_servers(current_user: User = Depends(get_current_active_user)):
    """Get all MCP servers and their tools with status."""
    servers = {}
    for name, server in mcp_service.get_all_servers().items():
        servers[name] = {
            "name": name,
            "description": server.description,
            "disabled": server.disabled,
            "tools": [
                {"name": t["name"], "description": t.get("description", ""), "disabled": t.get("disabled", False)}
                for t in server.tools
            ]
        }
    return servers

@router.post("/servers/{server_name}/enable")
def enable_server(server_name: str, current_user: User = Depends(get_current_active_user)):
    if not mcp_service.enable_server(server_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return {"message": f"Server '{server_name}' enabled."}

@router.post("/servers/{server_name}/disable")
def disable_server(server_name: str, current_user: User = Depends(get_current_active_user)):
    if not mcp_service.disable_server(server_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return {"message": f"Server '{server_name}' disabled."}

@router.post("/servers/{server_name}/tools/{tool_name}/enable")
def enable_tool(server_name: str, tool_name: str, current_user: User = Depends(get_current_active_user)):
    if not mcp_service.enable_tool(server_name, tool_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool or server not found")
    return {"message": f"Tool '{tool_name}' on server '{server_name}' enabled."}

@router.post("/servers/{server_name}/tools/{tool_name}/disable")
def disable_tool(server_name: str, tool_name: str, current_user: User = Depends(get_current_active_user)):
    if not mcp_service.disable_tool(server_name, tool_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool or server not found")
    return {"message": f"Tool '{tool_name}' on server '{server_name}' disabled."} 