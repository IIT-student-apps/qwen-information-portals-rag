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
        news_results = fetch_news_from_db(query)
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
            similarity_top_k=2,
            verbose=True
        )
        llm_query = f"На основе предоставленных новостей ответь на вопрос: {query}"
        response = chat_engine.chat(llm_query)
        used_nodes = response.source_nodes
        used_urls = {node.metadata.get("source_url") for node in used_nodes if node.metadata.get("source_url")}
        logger.debug(f"Использованные источники: {used_urls}")
        
        logger.info("Ответ от LLM успешно получен")

        used_urls = set()
        if response.source_nodes:
            for node in response.source_nodes:
                source_url = node.metadata.get("source_url")
                if source_url:  # Добавляем только если URL не пустой
                    used_urls.add(source_url)
        logger.info(f"Использованные URL из source_nodes: {used_urls}")

        final_answer = response.response

        logger.info("Ответ от LLM успешно получен")
        return {"answer": final_answer, "sources": list(used_urls)}
    
    except Exception as e:
        logger.error(f"Ошибка LLM: {str(e)}")
        return f"Ошибка при обработке запроса: {str(e)}"