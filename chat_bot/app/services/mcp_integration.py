import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from app.config import settings
from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class MCPServer:
    """Represents an MCP server configuration"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.command = config.get("command", [])
        self.args = config.get("args", [])
        self.env = config.get("env", {})
        self.disabled = config.get("disabled", False)
        self.description = config.get("description", "")
        self.tools = config.get("tools", [])

    async def refresh_tools(self):
        from app.services.mcp_integration import fetch_tools_for_server
        try:
            tools = await fetch_tools_for_server(self.name)
            if tools:
                self.tools = tools
        except Exception as e:
            logger.error(f"Failed to refresh tools for server '{self.name}': {e}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "disabled": self.disabled,
            "description": self.description,
            "tools": self.tools
        }


class MCPService:
    """Service for managing MCP server configurations"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or settings.MCP_CONFIG_PATH
        self.servers: Dict[str, MCPServer] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load MCP configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Parse mcpServers section
                mcp_servers = config_data.get("mcpServers", {})
                for server_name, server_config in mcp_servers.items():
                    self.servers[server_name] = MCPServer(server_name, server_config)
                
                logger.info(f"Loaded {len(self.servers)} MCP servers from {self.config_path}")
            else:
                logger.warning(f"MCP config file not found: {self.config_path}")
                self.create_default_config()
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")
            self.create_default_config()
    
    def save_config(self) -> None:
        """Save current MCP configuration to JSON file"""
        try:
            config_data = {
                "mcpServers": {
                    name: server.to_dict() 
                    for name, server in self.servers.items()
                }
            }
            
            # Ensure directory exists
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved MCP config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving MCP config: {e}")
    
    def create_default_config(self) -> None:
        """Create a default MCP configuration"""
        self.servers = {
            "filesystem": MCPServer("filesystem", {
                "command": ["npx"],
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
                "description": "File system access server",
                "tools": [
                    {"name": "read_file", "description": "Read a file", "disabled": False},
                    {"name": "write_file", "description": "Write to a file", "disabled": False}
                ]
            }),
            "brave-search": MCPServer("brave-search", {
                "command": ["npx"],
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {
                    "BRAVE_API_KEY": "your-brave-api-key-here"
                },
                "description": "Brave search integration",
                "tools": [
                    {"name": "search", "description": "Web search", "disabled": False}
                ]
            }),
            "sqlite": MCPServer("sqlite", {
                "command": ["npx"],
                "args": ["-y", "@modelcontextprotocol/server-sqlite", "/path/to/database.db"],
                "description": "SQLite database access",
                "tools": [
                    {"name": "query", "description": "Run SQL query", "disabled": False}
                ]
            })
        }
        self.save_config()
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get MCP server by name"""
        return self.servers.get(name)
    
    def get_all_servers(self) -> Dict[str, MCPServer]:
        """Get all MCP servers"""
        return self.servers.copy()
    
    def get_enabled_servers(self) -> Dict[str, MCPServer]:
        """Get only enabled MCP servers"""
        return {
            name: server 
            for name, server in self.servers.items() 
            if not server.disabled
        }
    
    async def add_server(self, name: str, config: Dict[str, Any]) -> MCPServer:
        """Add a new MCP server"""
        server = MCPServer(name, config)
        self.servers[name] = server
        self.save_config()
        return server
    
    async def update_server(self, name: str, config: Dict[str, Any]) -> Optional[MCPServer]:
        """Update an existing MCP server"""
        if name not in self.servers:
            return None
        
        server = MCPServer(name, config)
        self.servers[name] = server
        self.save_config()
        return server
    
    def remove_server(self, name: str) -> bool:
        """Remove an MCP server"""
        if name in self.servers:
            del self.servers[name]
            self.save_config()
            return True
        return False
    
    def enable_server(self, name: str) -> bool:
        """Enable an MCP server"""
        if name in self.servers:
            self.servers[name].disabled = False
            self.save_config()
            return True
        return False
    
    def disable_server(self, name: str) -> bool:
        """Disable an MCP server"""
        if name in self.servers:
            self.servers[name].disabled = True
            self.save_config()
            return True
        return False
    
    def validate_server_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate MCP server configuration and return list of errors"""
        errors = []
        
        if not config.get("command"):
            errors.append("Command is required")
        
        command = config.get("command", [])
        if not isinstance(command, list):
            errors.append("Command must be a list")
        
        args = config.get("args", [])
        if not isinstance(args, list):
            errors.append("Args must be a list")
        
        env = config.get("env", {})
        if not isinstance(env, dict):
            errors.append("Environment variables must be a dictionary")
        
        return errors
    
    def get_server_status(self, name: str) -> Dict[str, Any]:
        """Get status information for an MCP server"""
        server = self.get_server(name)
        if not server:
            return {"error": "Server not found"}
        
        return {
            "name": name,
            "enabled": not server.disabled,
            "command": server.command,
            "args": server.args,
            "description": server.description,
            "env_vars": list(server.env.keys())
        }

    def get_enabled_tools(self, server_name: str) -> List[Dict[str, Any]]:
        server = self.get_server(server_name)
        if not server:
            return []
        return [tool for tool in server.tools if not tool.get("disabled", False)]

    def enable_tool(self, server_name: str, tool_name: str) -> bool:
        server = self.get_server(server_name)
        if not server:
            return False
        for tool in server.tools:
            if tool["name"] == tool_name:
                tool["disabled"] = False
                self.save_config()
                return True
        return False

    def disable_tool(self, server_name: str, tool_name: str) -> bool:
        server = self.get_server(server_name)
        if not server:
            return False
        for tool in server.tools:
            if tool["name"] == tool_name:
                tool["disabled"] = True
                self.save_config()
                return True
        return False


# Global MCP service instance
mcp_service = MCPService()

async def fetch_tools_for_server(server_name: str):
    """Fetch the list of tools from a running MCP server by name."""
    server = mcp_service.get_server(server_name)
    if not server:
        raise ValueError(f"Server '{server_name}' not found in MCP config.")
    if not server.command:
        raise ValueError(f"Server '{server_name}' has no command configured.")
    params = StdioServerParameters(
        command=server.command,
        args=server.args,
        env=server.env or None
    )

    server_params = StdioServerParameters(
                command="node",
                args=["D:\\mcp_workspace\\custom\\click-up_mcp_servers.js"]
            )
            
    try:
        print("Fetching tools for server: "+server.command)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                
                return tools
    except Exception as e:
        logger.error(f"Failed to fetch tools for server '{server_name}': {e}")
        raise e
        # return []

@asynccontextmanager
async def lifespan(app):
    for server in mcp_service.get_all_servers().values():
        await server.refresh_tools()
    yield

app = FastAPI(
    title="AI Chat Application",
    description="A comprehensive chat application with multiple LLM providers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

if __name__ == "__main__":
    asyncio.run(app.main())