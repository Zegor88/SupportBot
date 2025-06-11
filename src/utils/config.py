import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Определение пользовательского исключения для ошибок векторизации
class VectorizationError(Exception):
    """Исключение для ошибок, возникающих при векторизации документов."""
    pass

# Определение пользовательского исключения для ошибок поиска документов
class RetrievalError(Exception):
    """Исключение для ошибок, возникающих при поиске документов в векторном хранилище."""
    pass

# Определение пользовательского исключения для ошибок генерации ответов
class ResponseGenerationError(Exception):
    """Исключение для ошибок, возникающих при генерации ответов на запросы пользователей."""
    pass

# Загружаем переменные окружения
load_dotenv()

# Настройки логирования
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'bot.log',
            'formatter': 'standard',
            'level': 'INFO',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

# OpenAI настройки
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен в переменных окружения")

# Настройки моделей
EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o-mini"

# Настройки векторизации
VECTOR_STORE_PATH = "data/vectorstore"
CSV_PATH = "data/answers_table.csv"

# Настройки RAG
RAG_SETTINGS = {
    'k': 5,  # количество документов для возврата
    'score_threshold': 0.3,  # минимальный порог схожести
    'max_tokens': 2000,  # максимальное количество токенов для контекста
}

# Настройки разделения текста
TEXT_SPLITTER_SETTINGS = {
    'chunk_size': 1000,
    'chunk_overlap': 100,
}

# Настройки CSV
CSV_SETTINGS = {
    'delimiter': ',',
    'quotechar': '"',
    'fieldnames': [
        "Sender_Name",
        "Sender_ID",
        "Date",
        "Text",
        "Reply_To_Message_ID",
        "Question"
    ],
}