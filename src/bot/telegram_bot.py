from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging

from .config import Config, logger
from .handlers import start, help_command, echo # Пока только echo для Task E1

class TelegramBot:
    def __init__(self, token: str):
        if not token:
            logger.critical("Токен Telegram бота не предоставлен!")
            raise ValueError("Токен не может быть пустым")
        self.token = token
        self.application = Application.builder().token(self.token).build()
        self._register_handlers()
        logger.info("Telegram бот инициализирован.")

    def _register_handlers(self):
        """Регистрирует обработчики команд и сообщений."""
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_command))
        
        # Для Task E1 (echo) регистрируем echo handler
        # В будущих задачах здесь будет более сложная логика MessageHandler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        logger.info("Обработчики команд зарегистрированы.")

    def run(self):
        """Запускает бота."""
        if not self.application:
            logger.error("Приложение не инициализировано.")
            return
            
        logger.info("Запуск бота...")
        self.application.run_polling()

def main():
    """Основная функция для запуска бота."""
    try:
        # Config.validate_token() уже был вызван в config.py при импорте
        bot_token = Config.TELEGRAM_BOT_TOKEN
        
        bot = TelegramBot(token=bot_token)
        bot.run()
    except ValueError as e:
        logger.critical(f"Ошибка запуска бота: {e}")
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка при запуске бота: {e}", exc_info=True)

if __name__ == '__main__':
    # Этот блок не будет выполняться при импорте, 
    # но полезен для прямого запуска этого файла для отладки (если потребуется).
    # Однако, рекомендуется создать отдельный main.py в корне src/ для запуска.
    logger.warning("telegram_bot.py запущен напрямую. Рекомендуется использовать src/main.py для запуска.")
    main() 