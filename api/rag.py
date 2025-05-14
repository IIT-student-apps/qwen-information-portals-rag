from llama_index_utils import setup_settings, process_news_with_llm
from pars import search_ria_simple, search_newsapi
from db_utils import create_application_logs, insert_application_logs, get_chat_history
from news_db_utils import initialize_database, update_database_schema
import logging
import uuid
from fastapi import FastAPI, HTTPException,Body
from db_utils import insert_application_logs, get_chat_history
from pars import search_ria_simple, search_newsapi
from llama_index_utils import process_news_with_llm
from datetime import datetime
from typing import  Dict, Any
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("rag.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("main")
app = FastAPI()

# Инициализация настроек LlamaIndex
setup_settings()

@app.post("/search-ria")
def search_ria(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # Валидация входных данных
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")
    
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=422, detail="Field 'question' must be a non-empty string")
    if model not in ["llama3.2:3b"]:
        raise HTTPException(status_code=422, detail="Field 'model' must be 'llama3.2:3b'")
    
    logging.info(f"Session ID: {session_id}, RIA Search Query: {question}")
    
    try:
        results, meta = search_ria_simple(question, limit=3)
        if meta['status'] == 'error':
            logging.error(f"RIA Search failed: {meta['message']}")
            raise HTTPException(status_code=500, detail=f"RIA Search failed: {meta['message']}")
        
        logging.info(f"Session ID: {session_id}, RIA Search Results: {meta['results_count']} articles found")
        return {
            "message": f"Found {meta['results_count']} articles from RIA.ru",
            "results": [
                {"title": doc.metadata["title"], "url": doc.metadata["url"], "content": doc.text[:200] + "..."}
                for doc in results
            ],
            "session_id": session_id
        }
    except Exception as e:
        logging.error(f"Session ID: {session_id}, RIA Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing RIA search: {str(e)}")

@app.post("/search-newsapi")
def search_newsapi(body: Dict[str, Any] = Body(...), from_date: str = datetime.now().strftime("%Y-%m-%d")) -> Dict[str, Any]:
    # Валидация входных данных
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")
    
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=422, detail="Field 'question' must be a non-empty string")
    if model not in ["llama3.2:3b"]:
        raise HTTPException(status_code=422, detail="Field 'model' must be 'llama3.2:3b'")
    
    logging.info(f"Session ID: {session_id}, NewsAPI Search Query: {question}, From Date: {from_date}")
    
    try:
        results, meta = search_newsapi(question, limit=5, from_date=from_date)
        if meta['status'] == 'error':
            logging.error(f"NewsAPI Search failed: {meta['message']}")
            raise HTTPException(status_code=500, detail=f"NewsAPI Search failed: {meta['message']}")
        
        logging.info(f"Session ID: {session_id}, NewsAPI Search Results: {meta['results_count']} articles found")
        return {
            "message": f"Found {meta['results_count']} articles from NewsAPI.org",
            "results": [
                {"title": doc.metadata["title"], "url": doc.metadata["url"], "content": doc.text[:200] + "..."}
                for doc in results
            ],
            "session_id": session_id
        }
    except Exception as e:
        logging.error(f"Session ID: {session_id}, NewsAPI Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing NewsAPI search: {str(e)}")

@app.post("/news-chat")
def news_chat(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # Валидация входных данных
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")
    
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=422, detail="Field 'question' must be a non-empty string")
    if model not in ["llama3.2:3b"]:
        raise HTTPException(status_code=422, detail="Field 'model' must be 'llama3.2:3b'")
    
    logging.info(f"Session ID: {session_id}, News Chat Query: {question}, Model: {model}")
    
    chat_history = get_chat_history(session_id)
    try:
        answer = process_news_with_llm(question, chat_history)
        insert_application_logs(session_id, question, answer, model)
        logging.info(f"Session ID: {session_id}, News Chat Response: {answer[:200]}...")
        return {
            "answer": answer,
            "session_id": session_id,
            "model": model
        }
    except Exception as e:
        logging.error(f"Session ID: {session_id}, News Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing news chat: {str(e)}")
    
@app.get("/chat-history")
def get_selected_chat_history(session_id: str):
    chat_history = get_chat_history(session_id=session_id)
    logging.info(f"Retrieved chat history for session_id: {session_id}, messages: {len(chat_history)}")
    return chat_history




def main():
    logger = configure_logging()
    setup_settings()
    create_application_logs()
    initialize_database()
    update_database_schema()
    
    session_id = str(uuid.uuid4())
    logger.info(f"Начало сессии: {session_id}")
    
    print("=== Поиск новостей и обработка через LLM ===")
    
    while True:
        query = input("\nПоисковый запрос (или 'выход'): ")
        if query.lower() == "выход":
            break
        
        try:
            source_choice = input("Источник (1-RIA.ru, 2-NewsAPI.org): ")
            results, meta = search_newsapi(query) if source_choice == "2" else search_ria_simple(query)
            
            if not process_search_results(results, meta, session_id, query, logger):
                continue
                
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            print(f"Ошибка: {str(e)}")

def process_search_results(results, meta, session_id, query, logger):
    if meta['status'] != 'success':
        print(f"Ошибка: {meta['message']}")
        logger.error(f"Ошибка поиска: {meta['message']}")
        return False
    
    for i, item in enumerate(results, 1):
        print(f"\nРезультат {i}:\nTitle: {item.metadata['title']}\nURL: {item.metadata['url']}")
    
    llm_query = input("\nВопрос для LLM: ") or f"Что нового в теме '{query}'?"
    llm_response = process_news_with_llm(llm_query, get_chat_history(session_id))
    print(f"\nОтвет:\n{llm_response}")
    
    insert_application_logs(session_id, llm_query, llm_response, "llama3.2:3b")
    return True

if __name__ == "__main__":
    main()