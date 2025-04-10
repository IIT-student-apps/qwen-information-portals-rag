from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext
from llama_index.core import load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
import chromadb
import os
import logging
import shutil
import sys

logging.basicConfig(
    filename="rag.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("rag_system")

CHROMA_DB_PATH = "./chroma_db"
CHROMA_STORAGE_DIR = "./chroma_storage"
COLLECTION_NAME = "rag_collection"

def create_rag_system(pdf_path: str, chunk_size: int = 512, chunk_overlap: int = 50, force_rebuild: bool = False) -> VectorStoreIndex | None:
    """Создает или загружает RAG-систему из PDF с использованием Ollama Llama 3.2."""
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        if force_rebuild or not (os.path.exists(CHROMA_DB_PATH) and os.path.exists(CHROMA_STORAGE_DIR)):
            if os.path.exists(CHROMA_DB_PATH):
                shutil.rmtree(CHROMA_DB_PATH)
            if os.path.exists(CHROMA_STORAGE_DIR):
                shutil.rmtree(CHROMA_STORAGE_DIR)

            documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
            logger.info(f"Загружено {len(documents)} страниц из PDF: {pdf_path}")

            # Настройка эмбеддингов и LLM
            Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            Settings.chunk_size = chunk_size
            Settings.chunk_overlap = chunk_overlap
            Settings.llm = Ollama(model="llama3.2:3b", request_timeout=60.0)

            chroma_collection = chroma_client.create_collection(COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
            storage_context.persist(persist_dir=CHROMA_STORAGE_DIR)
            logger.info(f"Индекс сохранён в {CHROMA_DB_PATH} и {CHROMA_STORAGE_DIR}")
        else:
            logger.info(f"Загрузка существующего индекса из {CHROMA_STORAGE_DIR}")

            # Устанавливаем модель эмбеддингов перед загрузкой
            Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            Settings.llm = Ollama(model="llama3.2:3b", request_timeout=60.0)

            chroma_collection = chroma_client.get_collection(COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store, persist_dir=CHROMA_STORAGE_DIR)
            index = load_index_from_storage(storage_context=storage_context)
            logger.info("Существующий индекс успешно загружен")

        return index
    except Exception as e:
        logger.error(f"Ошибка при создании или загрузке RAG-системы: {e}")
        print(f"Ошибка: {e}")
        return None

def query_rag(index: VectorStoreIndex, question: str) -> str:
    """Выполняет запрос к RAG-системе с использованием Llama 3.2."""
    try:
        query_engine = index.as_query_engine(similarity_top_k=3, response_mode="compact")
        response = query_engine.query(question)
        logger.info(f"Запрос: {question}\nОтвет: {str(response)[:100]}...")
        return str(response)
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return f"Ошибка при обработке запроса: {e}"

def main():
    pdf_path = "example.pdf"
    if not os.path.exists(pdf_path):
        logger.error(f"Файл {pdf_path} не найден!")
        print(f"Файл {pdf_path} не найден!")
        return

    rag_index = create_rag_system(pdf_path, force_rebuild=False)
    if rag_index is None:
        return

    print("RAG-система готова с Llama 3.2. Задавайте вопросы или введите 'выход' для завершения.")
    try:
        while True:
            question = input("Введите ваш вопрос (или 'выход' для завершения): ")
            if question.lower() == "выход":
                logger.info("Завершение работы пользователем")
                break
            answer = query_rag(rag_index, question)
            print(f"Ответ: {answer}\n")
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем через Ctrl+C")
        sys.exit(0)

if __name__ == "__main__":
    try:
        logger.info("Запуск RAG-системы с Llama 3.2")
        main()
    except Exception as e:
        logger.error(f"Произошла ошибка в работе программы: {e}")
        print(f"Произошла ошибка: {e}")