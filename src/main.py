import logging

from bot.config import logger # Импортируем настроенный логгер
from bot.telegram_bot import TelegramBot, Config

def main():
    """Основная синхронная функция для запуска бота."""
    try:
        # Валидация токена происходит при импорте Config из bot.config
        # и при инициализации TelegramBot, если токен пустой.
        bot_token = Config.TELEGRAM_BOT_TOKEN
        if not bot_token:
            # Эта проверка отчасти дублирует Config.validate_token(), 
            # но полезна как последняя линия обороны в main.
            logger.critical("Критическая ошибка: TELEGRAM_BOT_TOKEN отсутствует в src/main.py.")
            return

        bot = TelegramBot(token=bot_token)
        logger.info("Запуск бота из src/main.py...")
        bot.run() # bot.run() вызывает self.application.run_polling(), который блокирующий

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
        # Этот блок перехватит ошибки, которые могли возникнуть 
        # до или после вызова main(), но не внутри него (те уже обработаны).
        logger.critical(f"Критическая ошибка на верхнем уровне выполнения src/main.py: {e}", exc_info=True) 