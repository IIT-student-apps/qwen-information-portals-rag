import streamlit as st
import requests
import uuid
from datetime import datetime
import re
import json
from streamlit.components.v1 import html

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_MODEL = "llama3.2:3b"
SAMPLE_QUESTIONS = [
    "Какие главные новости за сегодня?",
    "Что происходит в экономике?",
    "Новости о технологиях и ИИ",
    "Последние события в международной политике",
]


# --- Helper Functions ---
@st.cache_data(show_spinner=False)
def clean_source_markers(text: str) -> str:
    """Remove source markers and format text with Markdown."""
    cleaned = re.sub(r"\[Источник:.*?\]", "", text).strip()
    return cleaned


def format_message(text: str) -> str:
    """Format message text with Markdown support."""
    # Convert URLs to markdown links
    text = re.sub(r"(https?://\S+)", r"[\1](\1)", text)
    # Improve numbering format
    text = re.sub(r"(\d+)\.", r"\1\\.", text)
    return text


@st.cache_data(ttl=3600)
def post_to_backend(endpoint: str, data: dict, params: dict = None):
    """Post data to the backend with caching."""
    try:
        response = requests.post(
            f"{BACKEND_URL}{endpoint}", json=data, params=params, timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка соединения с сервером: {str(e)}")
        return None


def create_new_chat():
    """Create a new chat with unique IDs and default settings."""
    frontend_chat_id = str(uuid.uuid4())
    backend_session_id = str(uuid.uuid4())
    st.session_state.chats[frontend_chat_id] = {
        "name": "Чат",
        "messages": [],
        "backend_session_id": backend_session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "news_source": "RIA",
        "model": DEFAULT_MODEL,
    }
    st.session_state.current_chat_id = frontend_chat_id


def get_sorted_chat_ids():
    """Return sorted chat IDs by creation time."""
    return sorted(
        st.session_state.chats.keys(),
        key=lambda cid: st.session_state.chats[cid]["created_at"],
        reverse=True,
    )


def handle_user_input(user_input, news_source):
    """Process user input and handle backend communication."""
    current_chat = st.session_state.chats[st.session_state.current_chat_id]

    # Add user message
    current_chat["messages"].append(
        {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime("%H:%M"),
        }
    )

    backend_session_id = current_chat["backend_session_id"]

    with st.spinner("🔍 Ищем актуальные новости..."):
        search_payload = {
            "question": user_input,
            "session_id": backend_session_id,
            "model": current_chat["model"],
        }

        try:
            # Call the correct endpoint based on the selected news source
            endpoint = (
                "/search-ria" if news_source.lower() == "ria" else "/search-newsapi"
            )
            if news_source.lower() == "newsapi":
                search_payload["from_date"] = datetime.now().strftime("%Y-%m-%d")

            news_data = post_to_backend(endpoint, search_payload)

            if not news_data:
                raise ValueError("Новости не найдены")

            # Get AI response
            chat_response = post_to_backend("/news-chat", search_payload)

            if chat_response:
                answer = format_message(
                    clean_source_markers(chat_response.get("answer", ""))
                )
                sources = chat_response.get("sources", [])

                current_chat["messages"].append(
                    {
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )
            else:
                raise ValueError("Ошибка генерации ответа")

        except Exception as e:
            current_chat["messages"].append(
                {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": f"⚠️ Ошибка: {str(e)}",
                    "timestamp": datetime.now().strftime("%H:%M"),
                }
            )


def delete_chat_confirmation(chat_id):
    """Directly delete chat without confirmation."""
    del st.session_state.chats[chat_id]
    if st.session_state.current_chat_id == chat_id:
        st.session_state.current_chat_id = None
    st.rerun()


def render_message(message):
    """Render chat message with styling and interactions."""
    col = st.columns([0.1, 0.9])
    with col[0]:
        st.markdown("👤" if message["role"] == "user" else "🤖")

    with col[1]:
        msg_class = "user-message" if message["role"] == "user" else "bot-message"
        with st.container():
            st.markdown(
                f"<div class='chat-message {msg_class}'>"
                f"<div class='message-text'>{message['content']}</div>"
                f"<div class='message-time'>{message['timestamp']}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            if message["role"] == "assistant" and message.get("sources"):
                with st.expander("📚 Источники информации", expanded=False):
                    for i, source in enumerate(message["sources"]):
                        if isinstance(source, dict):
                            st.markdown(
                                f"{i+1}. [{source.get('title', 'Ссылка')}]({source.get('url', '#')})"
                            )
                        else:
                            st.markdown(f"{i+1}. {source}")


# --- Session State Initialization ---
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- Custom CSS ---
st.markdown(
    """
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background: #e8f4ff;
        border-left: 4px solid #2b73b7;
    }
    .bot-message {
        background: #f5f7fa;
        border-left: 4px solid #4a5568;
    }
    .message-text {
        margin-bottom: 0.5rem;
        line-height: 1.6;
    }
    .message-time {
        color: #718096;
        font-size: 0.8rem;
        text-align: right;
    }
    .stButton>button {
        min-width: 40px;
        padding: 0.2rem 0.5rem;
    }
    .sample-question {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    .sample-question:hover {
        background: #f7fafc;
        transform: translateY(-2px);
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Sidebar ---
with st.sidebar:
    st.title("💬 Мои чаты")

    # New Chat Button
    if st.button("✨ Новый чат", use_container_width=True, type="primary"):
        create_new_chat()
        st.rerun()

    # Chat List
    st.write("---")
    if st.session_state.chats:
        search_query = st.text_input(
            "Поиск по чатам", placeholder="Введите ключевые слова..."
        )

    for chat_id in get_sorted_chat_ids():
        chat = st.session_state.chats[chat_id]

        if search_query and search_query.lower() not in json.dumps(chat).lower():
            continue

        cols = st.columns([0.8, 0.2])
        with cols[0]:
            btn_type = (
                "primary"
                if chat_id == st.session_state.current_chat_id
                else "secondary"
            )
            if st.button(
                f"{chat['name']}",
                key=f"btn_{chat_id}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state.current_chat_id = chat_id
                st.rerun()

        with cols[1]:
            if st.button("🗑️", key=f"del_{chat_id}", help="Удалить чат"):
                delete_chat_confirmation(chat_id)

# --- Main Interface ---
if st.session_state.current_chat_id in st.session_state.chats:
    current_chat = st.session_state.chats[st.session_state.current_chat_id]

    # Chat Header with Settings
    header_cols = st.columns([0.8, 0.2])
    with header_cols[0]:
        st.subheader(current_chat["name"])
    with header_cols[1]:
        current_chat["news_source"] = st.selectbox(
            "Источник новостей",
            ["RIA", "newsapi"],
            format_func=lambda x: "RIA Новости" if x == "RIA" else "NewsAPI",
            label_visibility="collapsed",
        )

    # Chat History
    for msg in current_chat["messages"]:
        render_message(msg)

    # Sample Questions
    st.write("---")
    st.markdown("**Примеры запросов:**")
    cols = st.columns(2)
    for i, question in enumerate(SAMPLE_QUESTIONS):
        with cols[i % 2]:
            if st.button(question, key=f"sample_{i}"):
                handle_user_input(question, current_chat["news_source"])
                st.rerun()

    # User Input
    user_input = st.chat_input("Задайте вопрос о новостях...")
    if user_input:
        handle_user_input(user_input, current_chat["news_source"])
        st.rerun()

else:
    st.markdown(
        "<h2 style='text-align: center; margin-top: 3rem'>Добро пожаловать в NewsChat! 📰</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center'>Начните новый чат, чтобы получить актуальные новости</p>",
        unsafe_allow_html=True,
    )

    # Center the button with columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Начать новый чат", use_container_width=True, type="primary"):
            create_new_chat()
            st.rerun()
