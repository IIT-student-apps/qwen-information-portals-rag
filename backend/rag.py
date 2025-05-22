import logging
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from llama_index_utils import setup_settings, process_news_with_llm
from pars import search_ria_simple, search_newsapi_simple
from db_utils import create_application_logs, insert_application_logs, get_chat_history
from news_db_utils import initialize_database, update_database_schema


# Инициализируем логгер глобально или передаем его
logger = None


def configure_logging():
    global logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("rag.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("main")
    return logger


# Раскомментируем FastAPI приложение
app = FastAPI()

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    configure_logging()
    if logger:
        logger.info("Запуск приложения и инициализация настроек...")
    else:
        print("Logger не сконфигурирован перед startup_event")

    setup_settings()
    create_application_logs()
    initialize_database()
    update_database_schema()
    if logger:
        logger.info("Инициализация завершена.")
    else:
        print("Инициализация завершена (logger не доступен).")


@app.post("/search-ria")
def search_ria(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")

    if not isinstance(question, str) or not question.strip():
        raise HTTPException(
            status_code=422, detail="Field 'question' must be a non-empty string"
        )
    if model not in ["llama3.2:3b"]:
        raise HTTPException(
            status_code=422, detail="Field 'model' must be 'llama3.2:3b'"
        )

    if logger:
        logger.info(f"Session ID: {session_id}, RIA Search Query: {question}")
    else:
        print(
            f"Session ID: {session_id}, RIA Search Query: {question} (logger не доступен)"
        )

    try:
        results, meta = search_ria_simple(question, limit=3)
        if meta["status"] == "error":
            if logger:
                logger.error(f"RIA Search failed: {meta['message']}")
            raise HTTPException(
                status_code=500, detail=f"RIA Search failed: {meta['message']}"
            )

        if logger:
            logger.info(
                f"Session ID: {session_id}, RIA Search Results: {meta['results_count']} articles found"
            )
        return {
            "message": f"Found {meta['results_count']} articles from RIA.ru",
            "results": [
                {
                    "title": doc.metadata["title"],
                    "url": doc.metadata["url"],
                    "content": doc.text[:200] + "...",
                }
                for doc in results
            ],
            "session_id": session_id,
        }
    except Exception as e:
        if logger:
            logger.error(f"Session ID: {session_id}, RIA Search error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing RIA search: {str(e)}"
        )


@app.post("/search-newsapi")
def search_newsapi(
    body: Dict[str, Any] = Body(...),
    from_date: str = datetime.now().strftime("%Y-%m-%d"),
) -> Dict[str, Any]:
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")

    if not isinstance(question, str) or not question.strip():
        raise HTTPException(
            status_code=422, detail="Field 'question' must be a non-empty string"
        )
    if model not in ["llama3.2:3b"]:
        raise HTTPException(
            status_code=422, detail="Field 'model' must be 'llama3.2:3b'"
        )

    if logger:
        logger.info(
            f"Session ID: {session_id}, NewsAPI Search Query: {question}, From Date: {from_date}"
        )
    else:
        print(
            f"Session ID: {session_id}, NewsAPI Search Query: {question}, From Date: {from_date} (logger не доступен)"
        )

    try:
        results, meta = search_newsapi_simple(question, limit=5)
        if meta["status"] == "error":
            if logger:
                logger.error(f"NewsAPI Search failed: {meta['message']}")
            raise HTTPException(
                status_code=500, detail=f"NewsAPI Search failed: {meta['message']}"
            )

        if logger:
            logger.info(
                f"Session ID: {session_id}, NewsAPI Search Results: {meta['results_count']} articles found"
            )
        return {
            "message": f"Found {meta['results_count']} articles from NewsAPI.org",
            "results": [
                {
                    "title": doc.metadata["title"],
                    "url": doc.metadata["url"],
                    "content": doc.text[:200] + "...",
                }
                for doc in results
            ],
            "session_id": session_id,
        }
    except Exception as e:
        if logger:
            logger.error(f"Session ID: {session_id}, NewsAPI Search error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing NewsAPI search: {str(e)}"
        )


@app.post("/news-chat")
def news_chat(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    question = body.get("question")
    session_id = body.get("session_id") or str(uuid.uuid4())
    model = body.get("model", "llama3.2:3b")

    if not isinstance(question, str) or not question.strip():
        raise HTTPException(
            status_code=422, detail="Field 'question' must be a non-empty string"
        )
    if model not in ["llama3.2:3b"]:
        raise HTTPException(
            status_code=422, detail="Field 'model' must be 'llama3.2:3b'"
        )

    if logger:
        logger.info(
            f"Session ID: {session_id}, News Chat Query: {question}, Model: {model}"
        )
    else:
        print(
            f"Session ID: {session_id}, News Chat Query: {question}, Model: {model} (logger не доступен)"
        )

    chat_history_for_llm = get_chat_history(session_id)

    try:
        llm_query = f"Что нового в теме '{question}'?"
        llm_result = process_news_with_llm(llm_query, chat_history_for_llm)
        answer_text = llm_result.get("answer", "")
        answer_sources = llm_result.get("sources", [])

        insert_application_logs(
            session_id, question, answer_text, answer_sources, model
        )

        if logger:
            log_answer_preview = (
                answer_text[:150] + "..." if len(answer_text) > 150 else answer_text
            )
            logger.info(
                f"Session ID: {session_id}, News Chat Response: {log_answer_preview}, Sources: {len(answer_sources)}"
            )
        else:
            print(
                f"Session ID: {session_id}, News Chat Response Preview (logger not available)"
            )

        return {
            "answer": answer_text,
            "sources": answer_sources,
            "session_id": session_id,
            "model": model,
        }
    except Exception as e:
        if logger:
            logger.error(
                f"Session ID: {session_id}, News Chat error: {str(e)}", exc_info=True
            )
        raise HTTPException(
            status_code=500, detail=f"Error processing news chat: {str(e)}"
        )


@app.get("/chat-history")
def get_selected_chat_history(session_id: str):
    chat_history_data = get_chat_history(session_id=session_id)
    if logger:
        logger.info(
            f"Retrieved chat history for session_id: {session_id}, records: {len(chat_history_data)}"
        )
    else:
        print(
            f"Retrieved chat history for session_id: {session_id} (logger не доступен)"
        )
    return chat_history_data
