import requests
import logging
import re
from bs4 import BeautifulSoup
from llama_index.core import Document
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from news_db_utils import save_to_database

logger = logging.getLogger("pars")


def search_ria_simple(query: str, limit: int = 3):
    try:
        session = requests.Session()
        retries = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = session.get(
            f"https://ria.ru/search/?query={query}", headers=headers, timeout=15
        )
        soup = BeautifulSoup(response.text, "lxml")
        results = []
        news_data = []

        for item in soup.find_all("div", class_="list-item", limit=limit):
            try:
                title = item.find("a", class_="list-item__title").get_text(strip=True)
                url = item.find("a")["href"]
                content = fetch_with_selenium(url)

                if not content:
                    logger.warning(f"Контент отсутствует для статьи: {url}")
                    content = extract_meta_description(url) or "Контент недоступен"

                news_data.append(
                    {"title": title, "url": url, "content": content[:2000], "date": ""}
                )
                results.append(
                    Document(text=content, metadata={"title": title, "url": url})
                )
                time.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка обработки статьи {url}: {str(e)}")
                continue

        if news_data:
            logger.debug(f"Подготовлено {len(news_data)} статей для сохранения из RIA")
            save_to_database(news_data)

        return results, {"status": "success", "results_count": len(results)}

    except Exception as e:
        logger.error(f"Ошибка RIA: {str(e)}")
        return [], {"status": "error", "message": str(e)}


def extract_meta_description(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        session = requests.Session()
        retries = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")
        meta = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", attrs={"property": "og:description"})
            or soup.find("meta", attrs={"name": "twitter:description"})
        )
        return meta["content"] if meta and meta.get("content") else ""
    except Exception as e:
        logger.error(f"Ошибка извлечения meta-описания для {url}: {str(e)}")
        return ""


def fetch_with_selenium(url: str) -> str:
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--enable-unsafe-swiftshader")  # Подавление ошибок WebGL
        driver = webdriver.Chrome(options=options)

        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    'div.article__body, article, div[class*="article"], div[class*="content"]',
                )
            )
        )
        soup = BeautifulSoup(driver.page_source, "lxml")
        driver.quit()

        return extract_content(soup, url)

    except Exception as e:
        logger.error(f"Ошибка Selenium для {url}: {str(e)}")
        return ""


def extract_content(soup: BeautifulSoup, url: str) -> str:
    try:
        for element in soup(
            [
                "script",
                "style",
                "iframe",
                "img",
                "footer",
                "nav",
                "button",
                "form",
                "input",
                "select",
            ]
        ):
            element.decompose()

        article_body = (
            soup.find("div", class_="article__body")
            or soup.find(
                "div",
                class_=[
                    "article__text",
                    "article__content",
                    "article__intro",
                    "article__block",
                    "news__content",
                    "content",
                ],
            )
            or soup.find("div", {"itemprop": "articleBody"})
            or soup.find("article")
            or soup.find(class_=["article-body", "text"])
            or soup.body
        )

        if article_body:
            for class_name in [
                "ad",
                "banner",
                "subscribe",
                "related",
                "comments",
                "article__announce",
                "article__meta",
                "article__tags",
            ]:
                for element in article_body.find_all(class_=class_name):
                    element.decompose()

            text = article_body.get_text(separator="\n", strip=True)
            return text if len(text) > 50 else ""

        logger.warning(f"Не удалось найти тело статьи: {url}")
        debug_filename = f"debug_{url.replace('/', '_')}.html"
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(str(soup))
        logger.info(f"Сохранен HTML для отладки: {debug_filename}")
        return ""

    except Exception as e:
        logger.error(f"Ошибка извлечения контента для {url}: {str(e)}")
        return ""


NEWSAPI_KEY = "c8a806f519af421d831c8cdc2de5b2ce"
BASE_URL = "https://newsapi.org/v2/everything"


def search_newsapi_simple(query: str, limit: int = 5):
    try:
        logger.info(f"Поиск через NewsAPI.org: {query}")
        params = {
            "q": query,
            "apiKey": NEWSAPI_KEY,
            "sortBy": "publishedAt",
            "pageSize": limit,
            "language": "ru",
        }
        session = requests.Session()
        retries = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data["status"] != "ok":
            raise Exception(f"Ошибка API: {data.get('message', 'Неизвестная ошибка')}")

        results = []
        news_data = []

        for article in data.get("articles", [])[:limit]:
            try:
                if not isinstance(article, dict):
                    logger.error(f"Некорректная структура статьи: {article}")
                    continue

                title = article.get("title", "Без заголовка")
                url = article.get("url", "")
                if title == "Без заголовка":
                    logger.warning(
                        f"Заголовок отсутствует для статьи: {url or 'unknown'}"
                    )
                if not url:
                    logger.warning(f"URL отсутствует для статьи: {title}")
                    continue

                date = article.get("publishedAt", "")
                content = clean_content(article.get("content", ""))
                description = clean_content(article.get("description", ""))

                logger.debug(
                    f"Обработка статьи: title={title[:50]}..., url={url}, content_len={len(content)}, description_len={len(description)}"
                )

                selected_text = (
                    description if len(description) > len(content) else content
                )
                if not selected_text or len(selected_text) < 50:
                    logger.warning(
                        f"Контент и описание слишком короткие для статьи: {url}"
                    )
                    selected_text = (
                        extract_meta_description(url) or "Контент недоступен"
                    )

                news_entry = {
                    "title": title,
                    "content": selected_text[:2000],
                    "url": url,
                    "date": date,
                }
                news_data.append(news_entry)

                results.append(
                    Document(
                        text=selected_text,
                        metadata={"title": title, "url": url, "date": date},
                    )
                )

            except Exception as e:
                logger.error(
                    f"Ошибка обработки статьи {article.get('url', 'unknown')}: {str(e)}, article={article}"
                )
                continue

        logger.debug(f"Подготовлено {len(news_data)} статей для сохранения из NewsAPI")
        if news_data:
            save_to_database(news_data)

        return results, {"status": "success", "results_count": len(results)}

    except Exception as e:
        logger.error(f"Ошибка при запросе к NewsAPI.org: {str(e)}")
        return [], {"status": "error", "message": str(e)}


def clean_content(text: str) -> str:
    """Очистка текста от [+X chars] и лишних пробелов."""
    if not text:
        return ""
    text = re.sub(r"\[.*?\]", "", text).strip()
    return text
