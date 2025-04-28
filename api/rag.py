from llama_index_utils import setup_settings, process_news_with_llm
from pars import search_ria_simple
from db_utils import create_application_logs, insert_application_logs, get_chat_history
import logging
import uuid

logging.basicConfig(
    filename="rag.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("main")

def main():
    setup_settings()
    
    create_application_logs()
    
    session_id = str(uuid.uuid4())
    
    print("=== Поиск новостей на RIA.ru и обработка через LLM ===")
    
    while True:
        query = input("\nВведите поисковый запрос для новостей (или 'выход' для завершения): ")
        if query.lower() == "выход":
            break
        
        
        insert_application_logs(session_id, query, "Поиск новостей выполнен", "llama3.2:3b")
        
        
        results, meta = search_ria_simple(query)
        
        if meta['status'] == 'success':
            print(f"\nНайдено результатов: {meta['results_count']}")
            for i, item in enumerate(results, 1):
                print(f"\nРезультат {i}:\n{item[:500]}...")  
        else:
            print(f"\nОшибка: {meta['message']}")
        
        
        if results:
            llm_query = input("\nВведите вопрос для LLM (например, 'Что нового в этой теме?'): ")
            if not llm_query:
                llm_query = f"Что нового в теме '{query}'?"
            
            
            chat_history = get_chat_history(session_id)
            
            llm_response = process_news_with_llm(results, llm_query, chat_history=chat_history)
            print(f"\nОтвет от LLM:\n{llm_response}")
            
            insert_application_logs(session_id, llm_query, llm_response, "llama3.2:3b")
        else:
            print("\nНет данных для обработки в LLM.")
    
    print("\nДетали в файле news_api.log")

if __name__ == "__main__":
    main()