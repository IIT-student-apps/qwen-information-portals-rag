// Chat Sidebar Component
const ChatSidebar = {
    props: {
        chats: {
            type: Array,
            required: true
        },
        currentChatId: {
            type: String,
            default: null
        },
        isExpanded: {
            type: Boolean,
            default: true
        }
    },
    methods: {
        // Create a new chat
        createChat() {
            this.$emit('create-chat');
        },

        // Delete a chat
        deleteChat(chatId, event) {
            event.stopPropagation(); // Prevent selecting the chat
            this.$emit('delete-chat', chatId);
        },

        // Switch to a different chat
        switchChat(chatId) {
            this.$emit('switch-chat', chatId);
        },

        // Toggle sidebar expansion
        toggleSidebar() {
            this.$emit('toggle-sidebar');
        },

        // Format date for display
        formatDate(isoString) {
            if (!isoString) return '';
            const date = new Date(isoString);
            return date.toLocaleDateString();
        }
    },
    template: `
        <div class="sidebar" :class="{ 'collapsed': !isExpanded }">
            <div class="sidebar-header">
                <h2 class="sidebar-title" v-if="isExpanded">News Chat</h2>
                <button class="toggle-button" @click="toggleSidebar">
                    <i class="fas" :class="isExpanded ? 'fa-chevron-left' : 'fa-chevron-right'"></i>
                </button>
            </div>
            
            <div class="chat-list">
                <div 
                    v-for="chat in chats" 
                    :key="chat.id"
                    class="chat-item"
                    :class="{ 'active': chat.id === currentChatId }"
                    @click="switchChat(chat.id)"
                >
                    <div class="chat-item-content">
                        <div class="chat-icon">
                            <i class="fas fa-comment"></i>
                        </div>
                        <div class="chat-info" v-if="isExpanded">
                            <div class="chat-title">{{ chat.title }}</div>
                            <div class="chat-date">{{ formatDate(chat.created) }}</div>
                        </div>
                    </div>
                    
                    <button 
                        v-if="isExpanded" 
                        class="delete-chat-btn"
                        @click="deleteChat(chat.id, $event)"
                    >
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            
            <button class="new-chat-btn" @click="createChat">
                <i class="fas fa-plus"></i>
                <span v-if="isExpanded">New Chat</span>
            </button>
        </div>
    `
}; 