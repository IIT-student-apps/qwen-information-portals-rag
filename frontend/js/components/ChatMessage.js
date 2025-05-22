// Chat Message Component
const ChatMessage = {
    props: {
        message: {
            type: Object,
            required: true
        }
    },
    computed: {
        // Format timestamp for display
        formattedTime() {
            if (!this.message.timestamp) return '';
            const date = new Date(this.message.timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        // Message classes based on sender
        messageClasses() {
            return {
                'message': true,
                'user-message': this.message.sender === 'user',
                'bot-message': this.message.sender === 'bot'
            }
        },

        // Check if message has sources
        hasSources() {
            return this.message.sources && this.message.sources.length > 0;
        }
    },
    methods: {
        // Format source URL for display
        formatSourceUrl(source) {
            // Check if source is a string or an object
            if (typeof source === 'string') {
                return source;
            }

            // If source is an object with url property
            if (source.url) {
                return source.url;
            }

            // If source is an object with title property (fallback to title if no url)
            if (source.title) {
                return source.title;
            }

            // Default case
            return "Unknown source";
        },

        // Get source URL for linking
        getSourceUrl(source) {
            if (typeof source === 'string') {
                return source;
            }
            return source.url || '#';
        },

        // Get source title for display
        getSourceTitle(source, index) {
            if (typeof source === 'string') {
                // Extract domain from URL for display
                try {
                    const url = new URL(source);
                    return url.hostname;
                } catch (e) {
                    return `Source ${index + 1}`;
                }
            }
            return source.title || `Source ${index + 1}`;
        }
    },
    template: `
        <div :class="messageClasses">
            <div class="message-avatar">
                <i class="fas" :class="message.sender === 'user' ? 'fa-user' : 'fa-robot'"></i>
            </div>
            <div class="message-content">
                <div class="message-text">{{ message.text }}</div>
                
                <div class="message-sources" v-if="hasSources">
                    <div class="sources-title">Sources:</div>
                    <div class="source-item" v-for="(source, index) in message.sources" :key="index">
                        <a :href="getSourceUrl(source)" target="_blank" class="source-link">
                            <i class="fas fa-external-link-alt"></i>
                            {{ getSourceTitle(source, index) }}
                        </a>
                    </div>
                </div>
                
                <div class="message-meta">
                    <span class="message-time">{{ formattedTime }}</span>
                </div>
            </div>
        </div>
    `
}; 