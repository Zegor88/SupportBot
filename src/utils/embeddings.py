import os
from typing import List, Optional
from dotenv import load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import logging.config
from config import (
    LOGGING_CONFIG, EMBEDDING_MODEL, VECTOR_STORE_PATH, CSV_PATH,
    TEXT_SPLITTER_SETTINGS, CSV_SETTINGS, VectorizationError
)

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Проверяем наличие API ключа
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY не установлен в переменных окружения")

class DocumentVectorizer:
    def __init__(self, csv_path: str = CSV_PATH, vector_store_path: str = VECTOR_STORE_PATH):
        """
        Инициализация векторизатора документов
        
        Args:
            csv_path: путь к CSV файлу с данными
            vector_store_path: путь для сохранения векторного хранилища
            
        Raises:
            VectorizationError: при ошибках инициализации
        """
        try:
            self.csv_path = csv_path
            self.vector_store_path = vector_store_path
            self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
            logger.info("DocumentVectorizer успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации DocumentVectorizer: {str(e)}")
            raise VectorizationError(f"Ошибка инициализации: {str(e)}")
        
    def load_documents(self) -> List:
        """
        Загружает документы из CSV файла
        
        Returns:
            List: список загруженных документов
            
        Raises:
            VectorizationError: при ошибках загрузки документов
        """
        try:
            logger.info(f"Загрузка документов из {self.csv_path}")
            loader = CSVLoader(
                file_path=self.csv_path,
                csv_args=CSV_SETTINGS
            )
            documents = loader.load()
            logger.info(f"Успешно загружено {len(documents)} документов")
            return documents
        except Exception as e:
            logger.error(f"Ошибка при загрузке документов: {str(e)}")
            raise VectorizationError(f"Ошибка загрузки документов: {str(e)}")

    def split_documents(self, documents: List) -> List:
        """
        Разделяет документы на части
        
        Args:
            documents: список документов для разделения
            
        Returns:
            List: список разделенных документов
            
        Raises:
            VectorizationError: при ошибках разделения документов
        """
        try:
            logger.info("Разделение документов на части")
            text_splitter = RecursiveCharacterTextSplitter(
                **TEXT_SPLITTER_SETTINGS,
                add_start_index=True
            )
            splits = text_splitter.split_documents(documents)
            logger.info(f"Создано {len(splits)} частей документов")
            return splits
        except Exception as e:
            logger.error(f"Ошибка при разделении документов: {str(e)}")
            raise VectorizationError(f"Ошибка разделения документов: {str(e)}")

    def create_vector_store(self, documents: List) -> FAISS:
        """
        Создает векторное хранилище из документов
        
        Args:
            documents: список документов для векторизации
            
        Returns:
            FAISS: векторное хранилище
            
        Raises:
            VectorizationError: при ошибках создания векторного хранилища
        """
        try:
            logger.info("Создание векторного хранилища")
            vector_store = FAISS.from_documents(documents, self.embeddings)
            logger.info("Векторное хранилище успешно создано")
            return vector_store
        except Exception as e:
            logger.error(f"Ошибка при создании векторного хранилища: {str(e)}")
            raise VectorizationError(f"Ошибка создания векторного хранилища: {str(e)}")

    def save_vector_store(self, vector_store: FAISS) -> None:
        """
        Сохраняет векторное хранилище локально
        
        Args:
            vector_store: векторное хранилище для сохранения
            
        Raises:
            VectorizationError: при ошибках сохранения
        """
        try:
            logger.info(f"Сохранение векторного хранилища в {self.vector_store_path}")
            vector_store.save_local(self.vector_store_path)
            logger.info("Векторное хранилище успешно сохранено")
        except Exception as e:
            logger.error(f"Ошибка при сохранении векторного хранилища: {str(e)}")
            raise VectorizationError(f"Ошибка сохранения векторного хранилища: {str(e)}")

    def process(self) -> None:
        """
        Выполняет полный процесс векторизации и сохранения
        
        Raises:
            VectorizationError: при любых ошибках в процессе векторизации
        """
        try:
            # Загружаем документы
            documents = self.load_documents()
            
            # Разделяем на части
            splits = self.split_documents(documents)
            
            # Создаем векторное хранилище
            vector_store = self.create_vector_store(splits)
            
            # Сохраняем локально
            self.save_vector_store(vector_store)
            
            logger.info("Векторизация успешно завершена")
            
        except VectorizationError:
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при векторизации: {str(e)}")
            raise VectorizationError(f"Неожиданная ошибка: {str(e)}")

def main() -> None:
    """Основная функция для запуска векторизации"""
    try:
        vectorizer = DocumentVectorizer()
        vectorizer.process()
    except VectorizationError as e:
        logger.error(f"Ошибка при векторизации: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        raise

if __name__ == "__main__":
    main()