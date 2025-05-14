import sqlite3
import logging
import numpy as np
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import pickle
import faiss
import os

logger = logging.getLogger("news_db_utils")

def get_db_connection():
    conn = sqlite3.connect("news_database.db")
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS news
                       (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT,
                        url TEXT UNIQUE,
                        embedding BLOB)''')
        conn.commit()
    initialize_faiss_index()

def update_database_schema():
    with get_db_connection() as conn:
        try:
            conn.execute("ALTER TABLE news ADD COLUMN embedding BLOB")
            logger.info("Столбец 'embedding' добавлен в таблицу 'news'")
        except sqlite3.OperationalError:
            logger.info("Столбец 'embedding' уже существует")
        conn.commit()

def rebuild_embeddings():
    """Перестраивает эмбеддинги для всех новостей, включая title."""
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, content FROM news')
        rows = cursor.fetchall()
        
        for row in rows:
            id, title, content = row['id'], row['title'], row['content']
            # Комбинируем title и content
            text = f"{title}\n{content or ''}"
            embedding = embed_model.get_text_embedding(text)
            embedding_bytes = pickle.dumps(np.array(embedding))
            cursor.execute('UPDATE news SET embedding = ? WHERE id = ?', (embedding_bytes, id))
        
        conn.commit()
        logger.info(f"Перестроены эмбеддинги для {len(rows)} новостей")

def initialize_faiss_index(force=False):
    """Инициализирует или перестраивает индекс FAISS."""
    if force:
        rebuild_embeddings()  # Перестраиваем эмбеддинги с учётом title
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, embedding FROM news WHERE embedding IS NOT NULL ORDER BY id')
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("Нет данных для создания индекса FAISS")
            return
        
        d = 384  # Размерность эмбеддинга
        embeddings = []
        ids = []
        for row in rows:
            embedding = pickle.loads(row['embedding'])
            embeddings.append(embedding)
            ids.append(row['id'])
        
        embeddings = np.array(embeddings, dtype=np.float32)
        embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        nlist = min(100, len(embeddings))  
        index = faiss.IndexFlatIP(d)  
        if len(embeddings) > 1000:  
            quantizer = faiss.IndexFlatIP(d)
            index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
            index.train(embeddings)
            index.nprobe = 10
        
        index.add(embeddings)
        
        faiss.write_index(index, "faiss_index.bin")
        
        faiss_to_db = {i: db_id for i, db_id in enumerate(ids)}
        with open("faiss_to_db.json", "w") as f:
            import json
            json.dump(faiss_to_db, f)
        
        logger.info(f"FAISS индекс создан: {index.ntotal} векторов")

def save_to_database(news_data):
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        new_embeddings = []
        new_ids = []
        updated_ids = []
        inserted_count = 0
        updated_count = 0
        
        for news in news_data:
            title = news["title"]
            content = news["content"]
            url = news["url"]
            text = f"{title}\n{content or ''}"
            embedding = embed_model.get_text_embedding(text) if text.strip() else None
            embedding_bytes = pickle.dumps(np.array(embedding)) if embedding is not None else None
            
            # Проверяем наличие записи с таким title
            cursor.execute('SELECT id, url FROM news WHERE title = ?', (title,))
            existing_by_title = cursor.fetchone()
            
            if existing_by_title:
                # Обновляем запись с совпадающим title
                existing_id, existing_url = existing_by_title['id'], existing_by_title['url']
                if existing_url == url:
                    # Тот же url, обновляем content и embedding
                    cursor.execute('''UPDATE news SET content = ?, embedding = ? WHERE id = ?''',
                                  (content, embedding_bytes, existing_id))
                    updated_count += cursor.rowcount
                    updated_ids.append(existing_id)
                    new_embeddings.append(embedding)
                    logger.debug(f"Обновлена запись по title: {title[:50]}..., id: {existing_id}")
                else:
                    # Разный url, проверяем конфликт UNIQUE
                    cursor.execute('SELECT id FROM news WHERE url = ?', (url,))
                    existing_by_url = cursor.fetchone()
                    if existing_by_url:
                        # Конфликт url, обновляем запись с этим url
                        cursor.execute('''UPDATE news SET title = ?, content = ?, embedding = ? WHERE url = ?''',
                                      (title, content, embedding_bytes, url))
                        updated_count += cursor.rowcount
                        updated_ids.append(existing_by_url['id'])
                        new_embeddings.append(embedding)
                        logger.debug(f"Обновлена запись по url: {url}, id: {existing_by_url['id']}")
                    else:
                        # Обновляем url для записи с совпадающим title
                        cursor.execute('''UPDATE news SET content = ?, url = ?, embedding = ? WHERE id = ?''',
                                      (content, url, embedding_bytes, existing_id))
                        updated_count += cursor.rowcount
                        updated_ids.append(existing_id)
                        new_embeddings.append(embedding)
                        logger.debug(f"Обновлена запись по title с новым url: {title[:50]}..., id: {existing_id}")
            else:
                # Проверяем конфликт url
                cursor.execute('SELECT id FROM news WHERE url = ?', (url,))
                existing_by_url = cursor.fetchone()
                if existing_by_url:
                    # Обновляем запись с совпадающим url
                    cursor.execute('''UPDATE news SET title = ?, content = ?, embedding = ? WHERE url = ?''',
                                  (title, content, embedding_bytes, url))
                    updated_count += cursor.rowcount
                    updated_ids.append(existing_by_url['id'])
                    new_embeddings.append(embedding)
                    logger.debug(f"Обновлена запись по url: {url}, id: {existing_by_url['id']}")
                else:
                    # Вставляем новую запись
                    cursor.execute('''INSERT INTO news (title, content, url, embedding)
                                   VALUES (?, ?, ?, ?)''',
                                  (title, content, url, embedding_bytes))
                    inserted_count += cursor.rowcount
                    cursor.execute('SELECT id FROM news WHERE url = ?', (url,))
                    news_id = cursor.fetchone()['id']
                    new_ids.append(news_id)
                    new_embeddings.append(embedding)
                    logger.debug(f"Вставлена новая запись: {title[:50]}..., id: {news_id}")
        
        conn.commit()
        logger.info(f"Сохранено {inserted_count} новых и обновлено {updated_count} записей в базе данных")
        
        # Обновляем FAISS для новых и изменённых записей
        if new_embeddings and (new_ids or updated_ids):
            update_faiss_index(new_embeddings, new_ids + updated_ids)

def update_faiss_index(new_embeddings, new_ids):
    """Добавляет новые эмбеддинги в индекс FAISS."""
    new_embeddings = np.array(new_embeddings, dtype=np.float32)
    new_embeddings /= np.linalg.norm(new_embeddings, axis=1, keepdims=True)
    
    index_file = "faiss_index.bin"
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
    else:
        d = 384
        nlist = 100
        quantizer = faiss.IndexFlatIP(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
        index.train(new_embeddings)
    
    # Загрузка текущего отображения
    faiss_to_db = {}
    if os.path.exists("faiss_to_db.json"):
        with open("faiss_to_db.json", "r") as f:
            import json
            faiss_to_db = json.load(f)
        faiss_to_db = {int(k): v for k, v in faiss_to_db.items()}
    
    # Добавление новых векторов
    start_idx = index.ntotal
    index.add(new_embeddings)
    
    # Обновление отображения
    for i, db_id in enumerate(new_ids):
        faiss_to_db[start_idx + i] = db_id
    
    # Сохранение
    faiss.write_index(index, index_file)
    with open("faiss_to_db.json", "w") as f:
        json.dump(faiss_to_db, f)
    
    logger.info(f"FAISS индекс обновлён: добавлено {len(new_ids)} векторов")

def fetch_news_from_db(query: str, top_k: int = 5):
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    query_embedding = np.array(embed_model.get_text_embedding(query), dtype=np.float32)
    query_embedding /= np.linalg.norm(query_embedding)
    
    index_file = "faiss_index.bin"
    if not os.path.exists(index_file):
        logger.warning("FAISS индекс не найден, создаётся новый")
        initialize_faiss_index()
    
    index = faiss.read_index(index_file)
    
    with open("faiss_to_db.json", "r") as f:
        import json
        faiss_to_db = json.load(f)
        faiss_to_db = {int(k): v for k, v in faiss_to_db.items()}
    
    distances, faiss_indices = index.search(query_embedding.reshape(1, -1), top_k)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        db_indices = [faiss_to_db.get(i, -1) for i in faiss_indices[0]]
        placeholders = ','.join('?' * len(db_indices))
        cursor.execute(f'SELECT id, title, content, url FROM news WHERE id IN ({placeholders})', db_indices)
        rows = cursor.fetchall()
        
        results = []
        for row, similarity in zip(rows, distances[0]):
            results.append({
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "url": row["url"],
                "similarity": similarity
            })
        
        logger.info(f"Найдено {len(results)} похожих статей для запроса: {query}")
        return results