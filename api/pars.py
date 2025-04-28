from bs4 import BeautifulSoup
import json
import os
import requests
from typing import List, Dict, Tuple
import logging 
from llama_index_utils import setup_settings, process_news_with_llm

logging.basicConfig(
    filename="news_api.log",
    level=logging.INFO,
    format="%(asctime)s-%(levelname)s-%(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("news_api")

NEWSAPI_KEY = "c8a806f519af421d831c8cdc2de5b2ce"  
BASE_URL = "https://newsapi.org/v2/everything"

HISTORY_FILE = "news_query_history.json"

def search_ria_simple(query: str, limit: int = 5) -> Tuple[List[str], Dict]:
    search_url = f"https://ria.ru/search/?query={query}"

    try:
        logger.info(f"Поиск: {query}")
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        results = []
        items = soup.find_all('div', class_='list-item', limit=limit)

        print(f"Найдено элементов на странице поиска: {len(items)}")  

        for item in items:
            try:
                title_tag = item.find('a', class_='list-item__title')
                if not title_tag:
                    print("Не найден заголовок новости")
                    continue
                
                title = title_tag.get_text(strip=True)
                url = title_tag['href']
                date_tag = item.find('div', class_='list-item__date')
                date = date_tag.get_text(strip=True) if date_tag else "No date"

                article_response = requests.get(url, timeout=10)
                if article_response.status_code != 200:
                    print(f"Не удалось загрузить статью {url}")
                    continue
                
                article_soup = BeautifulSoup(article_response.text, 'lxml')
                article_body = article_soup.find('div', class_='article__text')
                
                if not article_body:
                    print(f"Не найден текст статьи для {url}")
                    continue

                for elem in article_body(['script', 'style', 'iframe', 'img']):
                    elem.decompose()
                
                content = article_body.get_text(separator='\n', strip=True)

                results.append(
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Date: {date}\n"
                    f"Content: {content}"
                )
                print(f"Добавлена новость: {title}") 
            except Exception as e:
                logger.error(f"Ошибка обработки новости: {str(e)}")
                print(f"Ошибка обработки новости: {str(e)}")
                continue

        logger.info(f"Успешно обработано новостей: {len(results)}")
        return results, {'status': 'success', 'results_count': len(results)}
    
    except Exception as e:
        logger.error(f"Ошибка при поиске на RIA.ru: {str(e)}")
        return [], {'status': 'error', 'message': str(e)}

def search_newsapi(query: str, limit: int = 5) -> Tuple[List[str], Dict]:

    try:
        logger.info(f"Поиск через NewsAPI.org: {query}")
        # Параметры запроса
        params = {
            "q": query,
            "apiKey": NEWSAPI_KEY,
            "language": "ru",  
            "sortBy": "publishedAt",  
            "pageSize": limit,  
        }

        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()  

        data = response.json()

        if data["status"] != "ok":
            raise Exception(f"Ошибка API: {data.get('message', 'Неизвестная ошибка')}")

        articles = data.get("articles", [])
        results = []

        print(f"Найдено статей через NewsAPI.org: {len(articles)}") 

        for article in articles[:limit]:
            try:
                title = article.get("title", "Без заголовка")
                url = article.get("url", "Нет URL")
                date = article.get("publishedAt", "Нет даты")
                content = article.get("content", "Нет контента") or "Нет контента"
                result = (
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Date: {date}\n"
                    f"Content: {content[:500]}..."  
                )
                results.append(result)
                print(f"Добавлена статья: {title}")  
            except Exception as e:
                logger.error(f"Ошибка обработки статьи: {str(e)}")
                print(f"Ошибка обработки статьи: {str(e)}")
                continue

        logger.info(f"Успешно получено статей: {len(results)}")
        return results, {"status": "success", "results_count": len(results)}

    except Exception as e:
        logger.error(f"Ошибка при запросе к NewsAPI.org: {str(e)}")
        return [], {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("=== Поиск новостей и обработка через LLM ===")
    
   
    setup_settings()
    
    
    query = input("Введите поисковый запрос: ")
    
    print("\nВыберите источник новостей:")
    print("1. RIA.ru")
    print("2. NewsAPI.org")
    source_choice = input("Введите номер источника (1 или 2): ")

    if source_choice == "1":
        results, meta = search_ria_simple(query)
    elif source_choice == "2":
        results, meta = search_newsapi(query)
    else:
        print("Неверный выбор источника. Используется RIA.ru по умолчанию.")
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
        
        llm_response = process_news_with_llm(results, llm_query)
        print(f"\nОтвет от LLM:\n{llm_response}")
    else:
        print("\nНет данных для обработки в LLM.")
    
    print("\nДетали в файле news_api.log")