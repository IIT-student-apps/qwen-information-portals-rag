from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.ollama import Ollama
from chromautils import create_index, load_index  
import logging
import sys
import os

logging.basicConfig(
    filename="rag.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("rag_system")

def initialize_llm():
    """Инициализация модели Llama 3.2 через Ollama."""
    return Ollama(model="llama3.2:3b", request_timeout=60.0)

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
    pdf_path = "documents/example.pdf"
    

    rag_index = load_index()
    if rag_index is None:
        rag_index = create_index(pdf_path, chunk_size=512, chunk_overlap=50)
        if rag_index is None:
            return

    Settings.llm = initialize_llm()

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
