// Main Vue.js application

const { createApp, ref, reactive, onMounted, computed } = Vue;

const app = createApp({
    setup() {
        // State
        const chats = ref([]);
        const currentChatId = ref(null);
        const isLoading = ref(false);
        const isSidebarExpanded = ref(false);

        // Get the current chat
        const currentChat = computed(() => {
            if (!currentChatId.value) return null;
            return chats.value.find(chat => chat.id === currentChatId.value) || null;
        });

        // Chat messages for the current chat
        const messages = computed(() => {
            if (!currentChat.value) return [];
            return currentChat.value.messages || [];
        });

        // Initialize the application
        onMounted(() => {
            loadChatsFromLocalStorage();

            // Create a new chat if none exists
            if (chats.value.length === 0) {
                createNewChat();
            } else {
                // Set the current chat to the most recent one
                currentChatId.value = chats.value[0].id;
            }
        });

        // Load chats from localStorage
        const loadChatsFromLocalStorage = () => {
            const savedChats = localStorage.getItem('vue-news-chats');
            if (savedChats) {
                chats.value = JSON.parse(savedChats);
            }
        };

        // Save chats to localStorage
        const saveChatsToLocalStorage = () => {
            localStorage.setItem('vue-news-chats', JSON.stringify(chats.value));
        };

        // Create a new chat
        const createNewChat = () => {
            const newChat = {
                id: Date.now().toString(),
                title: `Chat ${chats.value.length + 1}`,
                messages: [],
                created: new Date().toISOString()
            };

            chats.value.unshift(newChat);
            currentChatId.value = newChat.id;
            saveChatsToLocalStorage();
        };

        // Delete a chat
        const deleteChat = (chatId) => {
            const index = chats.value.findIndex(chat => chat.id === chatId);
            if (index !== -1) {
                chats.value.splice(index, 1);

                // If the deleted chat was the current one, set a new current chat
                if (currentChatId.value === chatId) {
                    currentChatId.value = chats.value.length > 0 ? chats.value[0].id : null;

                    // If no chats left, create a new one
                    if (currentChatId.value === null) {
                        createNewChat();
                    }
                }

                saveChatsToLocalStorage();
            }
        };

        // Switch to a different chat
        const switchChat = (chatId) => {
            currentChatId.value = chatId;
        };

        // Send a message
        const sendMessage = async (text) => {
            if (!text.trim() || !currentChatId.value) return;

            // Add user message
            const userMessage = {
                id: Date.now().toString(),
                sender: 'user',
                text: text,
                timestamp: new Date().toISOString()
            };

            const chat = chats.value.find(chat => chat.id === currentChatId.value);
            if (!chat) return;

            if (!chat.messages) chat.messages = [];
            chat.messages.push(userMessage);

            // Update chat title if it's the first message
            if (chat.messages.length === 1) {
                chat.title = text.length > 20 ? text.substring(0, 20) + '...' : text;
            }

            saveChatsToLocalStorage();

            // Show loading state
            isLoading.value = true;

            try {
                // Send request to API
                const response = await fetch('http://localhost:8000/news-chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        question: text,
                        session_id: currentChatId.value,
                        model: 'llama3.2:3b'
                    })
                });

                if (!response.ok) {
                    throw new Error('API request failed');
                }

                const data = await response.json();
                console.log('API response:', data);

                // Add bot message
                const botMessage = {
                    id: Date.now().toString(),
                    sender: 'bot',
                    text: data.answer,
                    sources: data.sources || [],
                    timestamp: new Date().toISOString()
                };

                chat.messages.push(botMessage);
                saveChatsToLocalStorage();
            } catch (error) {
                console.error('Error sending message:', error);

                // Add error message
                const errorMessage = {
                    id: Date.now().toString(),
                    sender: 'bot',
                    text: 'Sorry, there was an error processing your request. Please try again.',
                    timestamp: new Date().toISOString()
                };

                chat.messages.push(errorMessage);
                saveChatsToLocalStorage();
            } finally {
                isLoading.value = false;
            }
        };

        // Toggle sidebar expansion
        const toggleSidebar = () => {
            isSidebarExpanded.value = !isSidebarExpanded.value;
        };

        return {
            chats,
            currentChatId,
            currentChat,
            messages,
            isLoading,
            isSidebarExpanded,
            createNewChat,
            deleteChat,
            switchChat,
            sendMessage,
            toggleSidebar
        };
    },
    template: `
        <div class="app-container" :class="{ 'sidebar-expanded': isSidebarExpanded }">
            <chat-sidebar 
                :chats="chats" 
                :currentChatId="currentChatId"
                :isExpanded="isSidebarExpanded"
                @create-chat="createNewChat" 
                @delete-chat="deleteChat" 
                @switch-chat="switchChat"
                @toggle-sidebar="toggleSidebar"
            />
            
            <div class="chat-container">
                <div class="messages-container">
                    <chat-message 
                        v-for="message in messages" 
                        :key="message.id" 
                        :message="message" 
                    />
                    <div v-if="isLoading" class="loading-indicator">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
                
                <chat-input @send="sendMessage" :isLoading="isLoading" />
            </div>
        </div>
    `
});

// Mount the Vue application
app.component('ChatSidebar', ChatSidebar);
app.component('ChatMessage', ChatMessage);
app.component('ChatInput', ChatInput);
app.mount('#app'); 