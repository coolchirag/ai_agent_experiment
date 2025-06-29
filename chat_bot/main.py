from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import logging
import os

from app.config import settings
from app.database import create_tables
from app.api import auth, chat, llm_config
from app.api import mcp_api
from app.services.mcp_integration import mcp_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create FastAPI app
app = FastAPI(
    title="AI Chat Application",
    description="A comprehensive chat application with multiple LLM providers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
create_tables()

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chats", tags=["Chat"])
app.include_router(llm_config.router, prefix="/api/llm-configs", tags=["LLM Configuration"])
app.include_router(mcp_api.router, prefix="/api/mcp", tags=["MCP Management"])

# Create static and templates directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "AI Chat Application is running"}

@app.get("/api/info")
async def app_info():
    """Get application information"""
    return {
        "name": "AI Chat Application",
        "version": "1.0.0",
        "description": "A comprehensive chat application with multiple LLM providers",
        "supported_providers": ["OpenAI", "Anthropic", "Google", "Groq"],
        "features": [
            "Multiple LLM providers",
            "Real-time streaming",
            "Chat history",
            "User authentication",
            "Temperature control",
            "MCP server integration"
        ]
    }

def extract_llm_response(response):
    # If response is a simple string
    if isinstance(response, str):
        return response
    # If response is a dict with 'parts'
    if isinstance(response, dict):
        if 'parts' in response:
            return ''.join(part.get('text', '') for part in response['parts'])
        if 'candidates' in response:
            # Take the first candidate, then its content.parts
            candidate = response['candidates'][0]
            parts = candidate['content']['parts']
            return ''.join(part.get('text', '') for part in parts)
    # Fallback
    return str(response)

@app.on_event("startup")
async def refresh_all_mcp_tools():
    for server in mcp_service.get_all_servers().values():
        await server.refresh_tools()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )