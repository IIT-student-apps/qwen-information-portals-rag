from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine.types import ChatMessage
import logging
from news_db_utils import fetch_news_from_db

logger = logging.getLogger("llama_index_utils")

def setup_settings():
    Settings.llm = Ollama(model="llama3.2:3b", request_timeout=60.0)
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50
    logger.info("Настройки LLM и эмбеддингов инициализированы")

def process_news_with_llm(query: str, chat_history: list = None) -> str:
    try:
        news_results = fetch_news_from_db(query, top_k=3)
        if not news_results:
            logger.warning(f"Новости для запроса '{query}' не найдены")
            return f"Не удалось найти новости по запросу '{query}'. Попробуйте изменить запрос."
        
        docs = [
            Document(
                text=news["content"][:1000] + "..." if len(news["content"]) > 1000 else news["content"],
                metadata={"source_url": news["url"], "title": news["title"]}
            ) for news in news_results
        ]
        
        index = VectorStoreIndex.from_documents(docs, embed_model=Settings.embed_model)
        
        memory = ChatMemoryBuffer.from_defaults(token_limit=2000)
        if chat_history:
            formatted_history = [
                ChatMessage(role="user" if msg["role"] == "human" else "assistant", content=msg["content"])
                for msg in chat_history
            ]
            memory.set(formatted_history)
            logger.info(f"Установлена история чата: {len(formatted_history)} сообщений")
        
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=(
                "Отвечай на русском. Используй предоставленный контекст и историю чата. "
                "Указывай источники в формате: [Источник: <URL>]."
            ),
            similarity_top_k=3,
            verbose=True
        )
        
        llm_query = f"На основе предоставленных новостей ответь на вопрос: {query}"
        response = chat_engine.chat(llm_query)
        
        # Извлекаем использованные документы из ответа
        used_nodes = response.source_nodes
        used_urls = {node.metadata.get("source_url") for node in used_nodes if node.metadata.get("source_url")}
        logger.debug(f"Использованные источники: {used_urls}")
        
        # Формируем ответ, избегая дублирования ссылок
        final_response = response.response
        if used_urls:
            # Добавляем только те источники, которые не упомянуты в тексте ответа
            existing_sources = set()
            for url in used_urls:
                if f"[Источник: {url}]" not in final_response:
                    existing_sources.add(url)
            if existing_sources:
                final_response += "\n\n" + "\n".join(f"[Источник: {url}]" for url in existing_sources)
        
        logger.info("Ответ от LLM успешно получен")
        return final_response
    
    except Exception as e:
        logger.error(f"Ошибка LLM: {str(e)}")
        return f"Ошибка при обработке запроса: {str(e)}"