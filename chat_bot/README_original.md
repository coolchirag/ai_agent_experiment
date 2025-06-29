# AI Chat Application

A comprehensive Python web application similar to Claude with multiple LLM provider support, built with FastAPI and modern web technologies.

## Features

- 🤖 **Multiple LLM Providers**: Support for OpenAI, Anthropic, Google Gemini, and Groq
- 💬 **Real-time Chat**: Streaming responses with WebSocket support
- 🔐 **User Authentication**: JWT-based authentication system
- 📊 **Chat History**: Persistent chat storage and management
- ⚙️ **Temperature Control**: Adjustable creativity settings
- 🔌 **MCP Integration**: Model Context Protocol server support like Claude Desktop
- 🎨 **Modern UI**: Beautiful, responsive interface with Tailwind CSS
- 🚀 **High Performance**: Built with FastAPI for maximum speed
- 🛡️ **Security**: Encrypted API key storage and secure authentication

## Architecture

### Backend (FastAPI)
- **Models**: SQLAlchemy ORM models for users, chats, messages, and LLM configurations
- **Services**: Modular services for authentication, LLM providers, and MCP integration
- **APIs**: RESTful APIs with automatic OpenAPI documentation
- **LLM Interface**: Abstract interface with concrete implementations for each provider

### Frontend (Vanilla JavaScript)
- **Modern UI**: Responsive design with Tailwind CSS
- **Real-time Chat**: Streaming responses and WebSocket support
- **Configuration Management**: Easy LLM provider setup and management
- **Chat History**: Persistent chat sessions with search and organization

### Database (MySQL)
- **Users**: User accounts and authentication
- **Chats**: Chat sessions with metadata
- **Messages**: Individual messages with role and content
- **LLM Configs**: User-specific LLM provider configurations

## Quick Start

### Prerequisites

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Node.js (for MCP servers)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Configure database**
   ```bash
   # Create MySQL database
   mysql -u root -p
   CREATE DATABASE ai_chat;
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the application**
   Open http://127.0.0.1:8000 in your browser

## Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ai_chat

# JWT
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM API Keys (optional - can be set per user)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
GROQ_API_KEY=your-groq-key
```

### LLM Provider Setup

Each user can configure their own API keys through the web interface:

1. Click the settings icon in the top navigation
2. Enter API keys for desired providers
3. Select default models for each provider
4. Test configurations to ensure they work

### MCP Server Integration

Configure MCP servers in `mcp_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": ["npx"],
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
      "description": "File system access"
    }
  }
}
```

## API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Chat Endpoints

- `GET /api/chats/` - List user's chats
- `POST /api/chats/` - Create new chat
- `GET /api/chats/{id}` - Get specific chat
- `POST /api/chats/{id}/stream` - Stream chat response
- `WebSocket /api/chats/{id}/ws` - Real-time chat

### LLM Configuration Endpoints

- `GET /api/llm-configs/providers` - List available providers
- `GET /api/llm-configs/` - Get user's configurations
- `POST /api/llm-configs/` - Create new configuration
- `PUT /api/llm-configs/{id}` - Update configuration

## Development

### Project Structure

```
ai_agent/
├── app/
│   ├── api/           # API routes
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── config.py      # Configuration
│   └── database.py    # Database setup
├── static/            # Frontend assets
├── templates/         # HTML templates
├── main.py           # Application entry point
└── requirements.txt  # Python dependencies
```

### Adding New LLM Providers

1. **Create provider implementation**
   ```python
   # app/services/llm_providers.py
   class NewProvider(LLMInterface):
       def __init__(self, api_key: str, model: str):
           super().__init__(api_key, model)
           # Initialize provider client
   
       async def generate_response(self, messages, **kwargs):
           # Implement response generation
   
       async def stream_response(self, messages, **kwargs):
           # Implement streaming response
   ```

2. **Register in factory**
   ```python
   # app/services/llm_factory.py
   _providers = {
       # ... existing providers
       "new_provider": NewProvider,
   }
   ```

3. **Add to enum**
   ```python
   # app/schemas/chat.py
   class LLMProvider(str, Enum):
       # ... existing providers
       NEW_PROVIDER = "new_provider"
   ```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Database Migrations

```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

## Deployment

### Production Setup

1. **Use production database**
   ```env
   DATABASE_URL=mysql+pymysql://user:pass@prod-host:3306/ai_chat
   ```

2. **Set secure secret key**
   ```env
   SECRET_KEY=your-very-secure-production-secret
   ```

3. **Configure CORS**
   ```python
   # main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Specific domains
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE"],
       allow_headers=["*"],
   )
   ```

4. **Use production ASGI server**
   ```bash
   pip install gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Security Considerations

- API keys are encrypted before storage
- JWT tokens have configurable expiration
- Input validation on all endpoints
- SQL injection protection via ORM
- CORS configuration for production
- Rate limiting recommended for production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the configuration examples

## Roadmap

- [ ] Voice input/output support
- [ ] File upload and processing
- [ ] Advanced MCP server management
- [ ] Chat export functionality
- [ ] Multi-language support
- [ ] Advanced search and filtering
- [ ] Plugin system for custom integrations 