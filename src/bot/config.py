import os
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Вывод в консоль
        # Можно добавить FileHandler для записи в файл
        # logging.FileHandler('bot.log') 
    ]
)

logger = logging.getLogger(__name__)

class Config:
    """Класс для хранения конфигурации бота."""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    @staticmethod
    def validate_token():
        """Проверяет наличие токена."""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле или переменных окружения.")
            raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN")
        logger.info("Конфигурация успешно загружена.")

# Валидация токена при импорте модуля
Config.validate_token() 