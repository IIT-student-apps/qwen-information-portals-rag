from news_db_utils import rebuild_embeddings, initialize_faiss_index

# Перестроить эмбеддинги с учётом title
rebuild_embeddings()

# Перестроить индекс FAISS
initialize_faiss_index(force=True)