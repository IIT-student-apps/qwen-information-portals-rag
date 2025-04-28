from llama_index.core.settings import Settings
from llama_index.llms.ollama import Ollama
from llama_index.core.prompts import ChatPromptTemplate
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import VectorStoreIndex, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.chat_engine.types import ChatMessage 
import logging

logger = logging.getLogger("llama_index_utils")

def initialize_llm():
    return Ollama(model="llama3.2:3b", request_timeout=60.0)

def initialize_embedding_model():
    return HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_chat_prompt_template():
    return ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Use the context and chat history to answer questions in Russian."),
        ("user", "{input}"),
        ("assistant", "{response}"),
    ])

def create_chat_engine(index, memory_buffer=None, chat_history=None):
    if memory_buffer is None:
        memory_buffer = ChatMemoryBuffer.from_defaults(token_limit=2000)
    
    if chat_history:
        
        formatted_history = []
        for message in chat_history:
            if message["role"] == "human":
                formatted_history.append(ChatMessage(role="user", content=message["content"]))
            elif message["role"] == "ai":
                formatted_history.append(ChatMessage(role="assistant", content=message["content"]))
        
        memory_buffer.set(formatted_history)
    
    return index.as_chat_engine(
        chat_mode="context",
        memory=memory_buffer,
        similarity_top_k=3,
        system_prompt=(
            "Reformulate the question if needed to make it standalone. Answer in Russian."
        ),
        verbose=True
    )

def process_news_with_llm(news_results: list[str], user_query: str, chat_history: list[dict] = None) -> str:
    try:
        
        documents = [Document(text=news) for news in news_results]
        
        index = VectorStoreIndex.from_documents(documents, embed_model=Settings.embed_model)
        
        chat_engine = create_chat_engine(index, chat_history=chat_history)
        
        llm_query = f"На основе предоставленных новостей ответь на вопрос: {user_query}"
        
        logger.info(f"Отправка запроса в LLM: {llm_query}")
        response = chat_engine.chat(llm_query)
        
        logger.info("Ответ от LLM успешно получен")
        return response.response
    
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса в LLM: {str(e)}")
        return f"Ошибка при обработке запроса в LLM: {str(e)}"

def setup_settings():
    Settings.llm = initialize_llm()
    Settings.embed_model = initialize_embedding_model()
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50