# src/bot/config.py
# This file contains the configuration for the bot.
# It is used to load the environment variables and configure the logging.

import os
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z',
    handlers=[
        logging.StreamHandler() # Вывод в консоль
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Класс для хранения конфигурации бота
class Config:
    """Класс для хранения конфигурации бота."""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Настройки администраторов
    ADMIN_USER_IDS_RAW = os.getenv('ADMIN_USER_IDS', '')
    ADMIN_USER_IDS = []
    if ADMIN_USER_IDS_RAW:
        try:
            ADMIN_USER_IDS = [int(admin_id.strip()) for admin_id in ADMIN_USER_IDS_RAW.split(',') if admin_id.strip()]
            logger.info(f"Загружены ID администраторов: {ADMIN_USER_IDS}")
        except ValueError:
            logger.error(f"Некорректный формат ADMIN_USER_IDS: '{ADMIN_USER_IDS_RAW}'. Ожидались ID через запятую, например, '12345,67890'. Список администраторов будет пустым.")
            ADMIN_USER_IDS = []
    else:
        logger.warning("Переменная окружения ADMIN_USER_IDS не установлена или пуста. Команды администрирования будут недоступны.")

    # Настройки ответа сообщения, если нет совпадений с правилами
    REPLY_ON_NO_MATCH_RAW = os.getenv('REPLY_ON_NO_MATCH', 'false').lower()
    REPLY_ON_NO_MATCH = REPLY_ON_NO_MATCH_RAW in ('true', '1', 't')
    logger.info(f"REPLY_ON_NO_MATCH установлен в: {REPLY_ON_NO_MATCH}")

    # Настройки для Vision модели
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_VISION_MODEL = os.getenv('OPENAI_VISION_MODEL', 'gpt-4o-mini')
    OPENAI_VISION_PROMPT = os.getenv('OPENAI_VISION_PROMPT', 'Опиши, что изображено на этой картинке, кратко и по существу.')
    logger.info(f"Vision модель: {OPENAI_VISION_MODEL}")

    @staticmethod
    def validate_token():
        """Проверяет наличие токена."""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле или переменных окружения.")
            raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN")
        
        if not Config.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY не найден в .env файле или переменных окружения.")
            raise ValueError("Необходимо указать OPENAI_API_KEY")

        logger.info("Конфигурация успешно загружена.")

# Валидация токена при импорте модуля
Config.validate_token() 