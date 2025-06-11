from typing import List, Dict
import logging
import logging.config
from utils.config import LOGGING_CONFIG, RetrievalError
from utils.rag_retriever import DocumentRetriever

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def test_retriever() -> None:
    """
    Тестирование функциональности DocumentRetriever
    
    Raises:
        RetrievalError: при ошибках в процессе тестирования
    """
    try:
        # Инициализация retriever'а
        logger.info("Инициализация DocumentRetriever для тестирования")
        retriever = DocumentRetriever()
        
        # Тестовые запросы
        test_queries = [
            "Как работает система RAG?",
            "Что такое векторное хранилище?",
            "Как использовать OpenAI API?",
            "Что такое embeddings?",
            "Как работает поиск похожих документов?"
        ]
        
        # Тестирование каждого запроса
        for query in test_queries:
            logger.info(f"\nТестирование запроса: {query}")
            
            # Поиск документов
            documents = retriever.search_similar_documents(query)
            
            # Вывод результатов
            print(f"\nРезультаты для запроса: {query}")
            print(f"Найдено документов: {len(documents)}")
            
            for i, doc in enumerate(documents, 1):
                print(f"\nДокумент {i}:")
                print(f"Релевантность: {doc['score']:.2f}")
                print(f"Контент: {doc['content'][:200]}...")
                print(f"Метаданные: {doc['metadata']}")
        
        logger.info("Тестирование успешно завершено")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {str(e)}")
        raise RetrievalError(f"Ошибка тестирования: {str(e)}")

if __name__ == "__main__":
    test_retriever() 