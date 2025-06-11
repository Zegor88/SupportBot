import logging

from src.bot.config import logger
from src.bot.telegram_bot import TelegramBot, Config

def main():
    """Основная синхронная функция для запуска бота."""
    try:
        bot_token = Config.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.critical("Критическая ошибка: TELEGRAM_BOT_TOKEN отсутствует в src/main.py.")
            return

        bot = TelegramBot(token=bot_token)
        logger.info("Запуск бота из src/main.py...")
        bot.run()

    # Обработка ошибок
    except ValueError as e:
        logger.critical(f"Ошибка конфигурации или инициализации при запуске бота: {e}")
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка при запуске бота из main: {e}", exc_info=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Критическая ошибка на верхнем уровне выполнения src/main.py: {e}", exc_info=True) 