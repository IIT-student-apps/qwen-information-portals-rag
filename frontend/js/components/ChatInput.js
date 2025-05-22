// Chat Input Component
const ChatInput = {
    props: {
        isLoading: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            message: '',
            inputHeight: '50px'
        }
    },
    methods: {
        // Send the message
        sendMessage() {
            if (!this.message.trim() || this.isLoading) return;

            this.$emit('send', this.message);
            this.message = '';
            this.adjustInputHeight();
        },

        // Handle Enter key press (sends message)
        handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        },

        // Auto-resize the textarea based on content
        adjustInputHeight() {
            const textarea = this.$refs.messageInput;
            if (!textarea) return;

            // Reset height to recalculate
            textarea.style.height = 'auto';

            // Set new height based on scroll height (with min and max constraints)
            const newHeight = Math.min(Math.max(textarea.scrollHeight, 50), 150);
            textarea.style.height = `${newHeight}px`;
            this.inputHeight = `${newHeight}px`;
        }
    },
    template: `
        <div class="chat-input-container">
            <div class="input-wrapper">
                <textarea
                    ref="messageInput"
                    v-model="message"
                    :style="{ height: inputHeight }"
                    placeholder="Ask anything about recent news..."
                    @input="adjustInputHeight"
                    @keydown="handleKeyPress"
                    :disabled="isLoading"
                ></textarea>
                
                <button 
                    class="send-button" 
                    @click="sendMessage"
                    :disabled="!message.trim() || isLoading"
                >
                    <i class="fas" :class="isLoading ? 'fa-spinner fa-spin' : 'fa-paper-plane'"></i>
                </button>
            </div>
        </div>
    `,
    mounted() {
        // Initialize text area height
        this.$nextTick(() => {
            this.adjustInputHeight();
        });
    }
}; 