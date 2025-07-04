class ChatApp {
    constructor() {
        this.token = localStorage.getItem("token");
        this.currentChatId = null;
        this.providers = [];
        this.configs = [];
        this.isStreaming = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAxiosInterceptors();
        
        if (this.token) {
            this.hideLoginModal();
            this.loadProviders();
            this.loadConfigs();
            this.loadChatHistory();
        } else {
            this.showLoginModal();
        }
    }

    setupEventListeners() {
        // Authentication
        document.getElementById("loginForm").addEventListener("submit", (e) => this.handleLogin(e));
        document.getElementById("registerForm").addEventListener("submit", (e) => this.handleRegister(e));
        document.getElementById("showRegisterBtn").addEventListener("click", () => this.showRegisterModal());
        document.getElementById("showLoginBtn").addEventListener("click", () => this.showLoginModal());
        document.getElementById("logoutBtn").addEventListener("click", () => this.handleLogout());

        // Chat functionality
        document.getElementById("newChatBtn").addEventListener("click", () => this.createNewChat());
        document.getElementById("sendBtn").addEventListener("click", () => this.sendMessage());
        document.getElementById("messageInput").addEventListener("keypress", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Settings
        document.getElementById("providerSelect").addEventListener("change", (e) => this.onProviderChange(e));
        document.getElementById("temperatureSlider").addEventListener("input", (e) => this.onTemperatureChange(e));
        document.getElementById("configBtn").addEventListener("click", () => this.showConfigModal());
        document.getElementById("closeConfigBtn").addEventListener("click", () => this.hideConfigModal());

        // Enable/disable send button based on input
        document.getElementById("messageInput").addEventListener("input", (e) => {
            const sendBtn = document.getElementById("sendBtn");
            sendBtn.disabled = !e.target.value.trim() || this.isStreaming;
        });
    }

    setupAxiosInterceptors() {
        // Add token to all requests
        axios.interceptors.request.use((config) => {
            if (this.token) {
                config.headers.Authorization = `Bearer ${this.token}`;
            }
            return config;
        });

        // Handle authentication errors
        axios.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response?.status === 401) {
                    this.handleLogout();
                }
                return Promise.reject(error);
            }
        );
    }

    // Authentication Methods
    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById("loginUsername").value;
        const password = document.getElementById("loginPassword").value;

        try {
            const response = await axios.post("/api/auth/login-json", {
                username,
                password
            });
            console.log("Login response:", response);
            this.token = response.data.access_token;
            console.log("Access token:", this.token);
            localStorage.setItem("token", this.token);
            
            this.hideLoginModal();
            this.loadProviders();
            this.loadConfigs();
            this.loadChatHistory();
            
            this.showNotification("Login successful!", "success");
        } catch (error) {
            console.log("Login error:", error);
            this.showNotification("Login failed: " + (error.response?.data?.detail || "Unknown error"), "error");
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const username = document.getElementById("registerUsername").value;
        const email = document.getElementById("registerEmail").value;
        const fullName = document.getElementById("registerFullName").value;
        const password = document.getElementById("registerPassword").value;

        try {
            await axios.post("/api/auth/register", {
                username,
                email,
                full_name: fullName,
                password
            });

            this.showNotification("Registration successful! Please login.", "success");
            this.showLoginModal();
        } catch (error) {
            this.showNotification("Registration failed: " + (error.response?.data?.detail || "Unknown error"), "error");
        }
    }

    handleLogout() {
        this.token = null;
        localStorage.removeItem("token");
        this.currentChatId = null;
        this.showLoginModal();
        this.clearChatMessages();
        this.clearChatHistory();
    }

    // Provider and Configuration Methods
    async loadProviders() {
        try {
            const response = await axios.get("/api/llm-configs/providers");
            this.providers = response.data.providers;
            this.populateProviderSelect();
        } catch (error) {
            console.error("Failed to load providers:", error);
        }
    }

    async loadConfigs() {
        try {
            const response = await axios.get("/api/llm-configs/");
            this.configs = response.data;
        } catch (error) {
            console.error("Failed to load configs:", error);
        }
    }

    populateProviderSelect() {
        const select = document.getElementById("providerSelect");
        select.innerHTML = "<option value=\"\">Select Provider</option>";
        
        this.providers.forEach(provider => {
            const option = document.createElement("option");
            option.value = provider.provider;
            option.textContent = provider.name;
            select.appendChild(option);
        });
    }

    onProviderChange(e) {
        const providerId = e.target.value;
        const modelSelect = document.getElementById("modelSelect");
        
        modelSelect.innerHTML = "<option value=\"\">Select Model</option>";
        
        if (providerId) {
            const provider = this.providers.find(p => p.provider === providerId);
            if (provider) {
                provider.models.forEach(model => {
                    const option = document.createElement("option");
                    option.value = model;
                    option.textContent = model;
                    modelSelect.appendChild(option);
                });
                
                // Set default model
                modelSelect.value = provider.default_model;
            }
        }
        
        this.updateSendButtonState();
    }

    onTemperatureChange(e) {
        document.getElementById("tempValue").textContent = e.target.value;
    }

    updateSendButtonState() {
        const sendBtn = document.getElementById("sendBtn");
        const messageInput = document.getElementById("messageInput");
        const provider = document.getElementById("providerSelect").value;
        const model = document.getElementById("modelSelect").value;
        
        sendBtn.disabled = !messageInput.value.trim() || !provider || !model || this.isStreaming;
    }

    // Chat Methods
    async createNewChat() {
        const provider = document.getElementById("providerSelect").value;
        const model = document.getElementById("modelSelect").value;
        const temperature = parseFloat(document.getElementById("temperatureSlider").value);
        const maxTokens = parseInt(document.getElementById("maxTokens").value);

        if (!provider || !model) {
            this.showNotification("Please select a provider and model first", "error");
            return;
        }

        try {
            const response = await axios.post("/api/chats/", {
                title: `New Chat - ${new Date().toLocaleString()}`,
                llm_provider: provider,
                model_name: model,
                temperature: temperature,
                max_tokens: maxTokens
            });

            this.currentChatId = response.data.id;
            this.clearChatMessages();
            this.loadChatHistory();
            this.showNotification("New chat created!", "success");
        } catch (error) {
            this.showNotification("Failed to create chat: " + (error.response?.data?.detail || "Unknown error"), "error");
        }
    }

    showNotification(message, type = "info") {
        // Create notification element
        const notification = document.createElement("div");
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === "success" ? "bg-green-500 text-white" :
            type === "error" ? "bg-red-500 text-white" :
            "bg-blue-500 text-white"
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showLoginModal() {
        document.getElementById("loginModal").classList.remove("hidden");
        document.getElementById("registerModal").classList.add("hidden");
    }

    hideLoginModal() {
        document.getElementById("loginModal").classList.add("hidden");
    }

    showRegisterModal() {
        document.getElementById("registerModal").classList.remove("hidden");
        document.getElementById("loginModal").classList.add("hidden");
    }

    clearChatMessages() {
        const chatMessages = document.getElementById("chatMessages");
        chatMessages.innerHTML = `
            <div class="text-center text-gray-500 mt-20">
                <i class="fas fa-comments text-4xl mb-4"></i>
                <p class="text-lg">Welcome to AI Chat!</p>
                <p class="text-sm">Select a provider and start a conversation.</p>
            </div>
        `;
    }

    clearChatHistory() {
        document.getElementById("chatHistory").innerHTML = "";
    }

    // Chat History Methods
    async loadChatHistory() {
        try {
            const response = await axios.get("/api/chats/");
            const chatHistory = response.data;
            const chatHistoryElem = document.getElementById("chatHistory");
            if (!chatHistoryElem) return;
            chatHistoryElem.innerHTML = "";
            chatHistory.forEach(chat => {
                const chatItem = document.createElement("div");
                chatItem.className = "chat-history-item cursor-pointer p-2 hover:bg-gray-200";
                chatItem.textContent = chat.title || `Chat ${chat.id}`;
                chatItem.onclick = () => this.loadChat(chat.id);
                chatHistoryElem.appendChild(chatItem);
            });
        } catch (error) {
            this.showNotification("Failed to load chat history", "error");
        }
    }

    async loadChat(chatId) {
        try {
            const response = await axios.get(`/api/chats/${chatId}`);
            this.currentChatId = chatId;
            this.renderChatMessages(response.data.messages || []);
        } catch (error) {
            this.showNotification("Failed to load chat messages", "error");
        }
    }

    renderChatMessages(messages) {
        const chatMessages = document.getElementById("chatMessages");
        if (!chatMessages) return;
        chatMessages.innerHTML = "";
        messages.forEach(msg => {
            const msgDiv = document.createElement("div");
            msgDiv.className = `chat-message mb-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`;
            msgDiv.textContent = msg.content;
            chatMessages.appendChild(msgDiv);
        });
    }

    // Modal Methods
    async showConfigModal() {
        const modal = document.getElementById("configModal");
        if (modal) modal.classList.remove("hidden");
        // Load and render MCP server/tool config
        await this.loadAndRenderMcpConfig();
    }

    async loadAndRenderMcpConfig() {
        const container = document.getElementById("mcpServerToolConfig");
        if (!container) return;
        container.innerHTML = '<div class="text-gray-500">Loading MCP servers...</div>';
        try {
            const response = await axios.get("/api/mcp/servers");
            const servers = response.data;
            if (Object.keys(servers).length === 0) {
                container.innerHTML = '<div class="text-gray-500">No MCP servers configured.</div>';
                return;
            }
            let html = '<ul class="space-y-2">';
            for (const [serverName, server] of Object.entries(servers)) {
                html += `<li class="border rounded p-2">
                    <div class="flex items-center justify-between">
                        <div>
                            <span class="font-semibold">${serverName}</span>
                            <span class="ml-2 text-sm text-gray-500">${server.description || ''}</span>
                        </div>
                        <button class="ml-4 px-2 py-1 rounded text-xs ${server.disabled ? 'bg-gray-300 text-gray-700' : 'bg-green-500 text-white'}" data-server="${serverName}" data-action="${server.disabled ? 'enable' : 'disable'}">
                            ${server.disabled ? 'Enable' : 'Disable'}
                        </button>
                    </div>`;
                if (server.tools && server.tools.length > 0) {
                    html += '<ul class="ml-6 mt-2 space-y-1">';
                    for (const tool of server.tools) {
                        html += `<li class="flex items-center justify-between">
                            <div>
                                <span class="text-sm">${tool.name}</span>
                                <span class="ml-2 text-xs text-gray-500">${tool.description || ''}</span>
                            </div>
                            <button class="ml-2 px-2 py-0.5 rounded text-xs ${tool.disabled ? 'bg-gray-300 text-gray-700' : 'bg-blue-500 text-white'}" data-server="${serverName}" data-tool="${tool.name}" data-action="${tool.disabled ? 'enable-tool' : 'disable-tool'}">
                                ${tool.disabled ? 'Enable' : 'Disable'}
                            </button>
                        </li>`;
                    }
                    html += '</ul>';
                }
                html += '</li>';
            }
            html += '</ul>';
            container.innerHTML = html;
            // Add event listeners for enable/disable buttons
            container.querySelectorAll('button[data-server][data-action]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const server = btn.getAttribute('data-server');
                    const action = btn.getAttribute('data-action');
                    await this.toggleMcpServer(server, action);
                });
            });
            container.querySelectorAll('button[data-server][data-tool][data-action]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const server = btn.getAttribute('data-server');
                    const tool = btn.getAttribute('data-tool');
                    const action = btn.getAttribute('data-action');
                    await this.toggleMcpTool(server, tool, action);
                });
            });
        } catch (err) {
            container.innerHTML = '<div class="text-red-500">Failed to load MCP servers.</div>';
        }
    }

    async toggleMcpServer(server, action) {
        try {
            await axios.post(`/api/mcp/servers/${server}/${action}`);
            this.showNotification(`Server '${server}' ${action === 'enable' ? 'enabled' : 'disabled'}.`, 'success');
            await this.loadAndRenderMcpConfig();
        } catch (err) {
            this.showNotification(`Failed to ${action} server '${server}'.`, 'error');
        }
    }

    async toggleMcpTool(server, tool, action) {
        try {
            const endpoint = `/api/mcp/servers/${server}/tools/${tool}/${action === 'enable-tool' ? 'enable' : 'disable'}`;
            await axios.post(endpoint);
            this.showNotification(`Tool '${tool}' on server '${server}' ${action === 'enable-tool' ? 'enabled' : 'disabled'}.`, 'success');
            await this.loadAndRenderMcpConfig();
        } catch (err) {
            this.showNotification(`Failed to ${action} tool '${tool}' on server '${server}'.`, 'error');
        }
    }

    hideConfigModal() {
        const modal = document.getElementById("configModal");
        if (modal) modal.classList.add("hidden");
    }

    // Send Message
    async sendMessage() {
        const messageInput = document.getElementById("messageInput");
        const content = messageInput ? messageInput.value.trim() : "";
        if (!content || !this.currentChatId) {
            this.showNotification("Please select a chat and enter a message.", "error");
            return;
        }
        try {
            // 1. Post the user message to the DB
            await axios.post(`/api/chats/${this.currentChatId}/messages`, {
                content,
                role: "user"
            });
            messageInput.value = "";
            this.loadChat(this.currentChatId);

            // 2. Stream the LLM response
            this.streamLLMResponse();
        } catch (error) {
            this.showNotification("Failed to send message", "error");
        }
    }

    async streamLLMResponse() {
        const chatMessages = document.getElementById("chatMessages");
        if (!chatMessages) return;

        // Show a typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.className = "chat-message mb-2 text-left typing-indicator";
        typingDiv.textContent = "Assistant is typing...";
        chatMessages.appendChild(typingDiv);

        try {
            // Get temperature and max_tokens from UI if available
            const temperatureElem = document.getElementById("temperatureSlider");
            const maxTokensElem = document.getElementById("maxTokens");
            const temperature = temperatureElem ? parseFloat(temperatureElem.value) : 0.7;
            const max_tokens = maxTokensElem ? parseInt(maxTokensElem.value) : 1000;

            const response = await fetch(`/api/chats/${this.currentChatId}/stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${this.token}`
                },
                body: JSON.stringify({
                    message: "", // Backend will fetch full history
                    temperature: temperature,
                    max_tokens: max_tokens
                })
            });

            if (!response.body) throw new Error("No response body for streaming");

            const reader = response.body.getReader();
            let assistantMsg = "";
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                // Parse SSE data
                chunk.split("\n\n").forEach(line => {
                    if (line.startsWith("data:")) {
                        const data = JSON.parse(line.replace("data:", "").trim());
                        if (data.content) {
                            assistantMsg += data.content;
                            typingDiv.textContent = assistantMsg;
                        }
                        if (data.done) {
                            typingDiv.classList.remove("typing-indicator");
                        }
                    }
                });
            }
            // Optionally reload chat to show the full message history
            this.loadChat(this.currentChatId);
        } catch (err) {
            typingDiv.textContent = "Error receiving assistant response.";
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.chatApp = new ChatApp();
});
