from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb
import os
import logging

logging.basicConfig(
    filename="chroma.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("chroma_utils")

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "rag_collection"

def initialize_embedding_model():
    return HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

def load_documents(pdf_path: str):
    return SimpleDirectoryReader(input_files=[pdf_path]).load_data()

def create_index(pdf_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> VectorStoreIndex | None:
    try:
        embed_model = initialize_embedding_model()

        db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        logger.info(f"Создание нового индекса для {pdf_path}...")
        documents = load_documents(pdf_path)
        logger.info(f"Загружено {len(documents)} страниц из PDF: {pdf_path}")
        index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=storage_context,
            embed_model=embed_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        logger.info(f"Индекс создан и сохранён в {CHROMA_DB_PATH}")
        print(f"Индекс создан и сохранён в {CHROMA_DB_PATH}")

        return index
    except Exception as e:
        logger.error(f"Ошибка при создании индекса: {e}")
        print(f"Ошибка при создании индекса: {e}")
        return None

def load_index() -> VectorStoreIndex | None:
    try:
        embed_model = initialize_embedding_model()

        db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        if not (os.path.exists(CHROMA_DB_PATH) and chroma_collection.count() > 0):
            logger.warning(f"Индекс в {CHROMA_DB_PATH} не найден или пуст")
            print(f"Индекс в {CHROMA_DB_PATH} не найден или пуст")
            return None

        logger.info(f"Загрузка существующего индекса из {CHROMA_DB_PATH}")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model
        )
        logger.info("Существующий индекс успешно загружен")
        print("Загрузка существующего индекса из Chroma...")

        return index
    except Exception as e:
        logger.error(f"Ошибка при загрузке индекса: {e}")
        print(f"Ошибка при загрузке индекса: {e}")
        return None

def create_or_load_index(pdf_path: str, chunk_size: int = 512, chunk_overlap: int = 50, force_rebuild: bool = False) -> VectorStoreIndex | None:
    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection(COLLECTION_NAME)

    if force_rebuild or not (os.path.exists(CHROMA_DB_PATH) and chroma_collection.count() > 0):
        return create_index(pdf_path, chunk_size, chunk_overlap)
    else:
        return load_index()

def add_to_index(path: str, is_directory: bool = False, chunk_size: int = 512, chunk_overlap: int = 50) -> bool:
    try:
        index = load_index()
        if index is None:
            logger.error("Не удалось добавить содержимое: индекс не существует. Сначала создайте индекс с помощью create_index.")
            print("Ошибка: индекс не существует. Сначала создайте индекс.")
            return False

        db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        logger.info(f"Добавление содержимого из {path} (директория: {is_directory})...")
        documents = load_documents(path, is_directory)
        logger.info(f"Загружено {len(documents)} документов из {path}")

        for doc in documents:
            index.insert(
                documents=[doc],
                storage_context=storage_context,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                show_progress=False
            )

        logger.info(f"Содержимое из {path} успешно добавлено в индекс в {CHROMA_DB_PATH}")
        print(f"Содержимое из {path} успешно добавлено в индекс")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении содержимого в индекс: {e}")
        print(f"Ошибка при добавлении: {e}")
        return False