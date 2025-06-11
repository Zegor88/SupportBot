# TODO: Retrieve and Generation

# TODO: Graph creation

import os
from typing import List, Dict, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import logging
import logging.config
from dotenv import load_dotenv
from utils.config import (
    LOGGING_CONFIG, EMBEDDING_MODEL, VECTOR_STORE_PATH,
    RAG_SETTINGS, RetrievalError
)

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

class DocumentRetriever:
    def __init__(self, vector_store_path: str = VECTOR_STORE_PATH):
        """
        Инициализация retriever'а для поиска документов
        
        Args:
            vector_store_path: путь к сохраненному векторному хранилищу
            
        Raises:
            RetrievalError: при ошибках инициализации
        """
        try:
            self.vector_store_path = vector_store_path
            self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
            self.vector_store = None
            self._load_vector_store()
            logger.info("DocumentRetriever успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации DocumentRetriever: {str(e)}")
            raise RetrievalError(f"Ошибка инициализации: {str(e)}")
    
    def _load_vector_store(self) -> None:
        """
        Загружает векторное хранилище из файловой системы
        
        Raises:
            RetrievalError: при ошибках загрузки векторного хранилища
        """
        try:
            logger.info(f"Загрузка векторного хранилища из {self.vector_store_path}")
            self.vector_store = FAISS.load_local(
                self.vector_store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("Векторное хранилище успешно загружено")
        except Exception as e:
            logger.error(f"Ошибка при загрузке векторного хранилища: {str(e)}")
            raise RetrievalError(f"Ошибка загрузки векторного хранилища: {str(e)}")

    def search_similar_documents(
        self,
        query: str,
        k: int = RAG_SETTINGS['k'],
        score_threshold: float = RAG_SETTINGS['score_threshold']
    ) -> List[Dict]:
        """
        Поиск похожих документов по запросу
        
        Args:
            query: текст запроса
            k: количество документов для возврата
            score_threshold: минимальный порог схожести (0-1)
            
        Returns:
            List[Dict]: список найденных документов с их метаданными и score
            
        Raises:
            RetrievalError: при ошибках поиска документов
        """
        try:
            logger.info(f"Поиск документов по запросу: {query}")
            
            # Получаем документы с их score
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query,
                k=k
            )
            
            # Фильтруем и форматируем результаты
            results = []
            for doc, score in docs_and_scores:
                # FAISS возвращает L2 distance, конвертируем в косинусное сходство
                normalized_score = 1.0 / (1.0 + score)
                
                if normalized_score >= score_threshold:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": normalized_score
                    })
            
            logger.info(f"Найдено {len(results)} релевантных документов")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {str(e)}")
            raise RetrievalError(f"Ошибка поиска документов: {str(e)}")

    def get_relevant_context(
        self,
        query: str,
        max_tokens: int = RAG_SETTINGS['max_tokens']
    ) -> Optional[str]:
        """
        Получение релевантного контекста для запроса с учетом ограничения токенов
        
        Args:
            query: текст запроса
            max_tokens: максимальное количество токенов для контекста
            
        Returns:
            Optional[str]: объединенный контекст из релевантных документов
            
        Raises:
            RetrievalError: при ошибках получения контекста
        """
        try:
            # Получаем документы
            documents = self.search_similar_documents(query)
            
            if not documents:
                logger.info("Релевантные документы не найдены")
                return None
            
            # Сортируем по релевантности
            documents.sort(key=lambda x: x["score"], reverse=True)
            
            # Объединяем контекст
            context = "\n\n".join([
                f"Релевантность: {doc['score']:.2f}\n{doc['content']}"
                for doc in documents
            ])
            
            # TODO: Добавить обрезку контекста по токенам
            
            return context
            
        except Exception as e:
            logger.error(f"Ошибка при получении контекста: {str(e)}")
            raise RetrievalError(f"Ошибка получения контекста: {str(e)}")