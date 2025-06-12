from telegram.ext import Application, CommandHandler, MessageHandler, filters
from .config import Config, logger
from .handlers import start, help_command, handle_text_message, reload_rules_command
from ..utils.memory_manager import MemoryManager  # Добавляем импорт MemoryManager

class TelegramBot:
    def __init__(self, token: str):
        """Инициализирует бота."""
        if not token:
            logger.critical("Токен Telegram бота не предоставлен!")
            raise ValueError("Токен не может быть пустым")
        self.token = token
        self.application = Application.builder().token(self.token).build()
        self.memory_manager = MemoryManager()  # Инициализируем менеджер памяти
        self._register_handlers()
        logger.info("Telegram бот инициализирован.")

    def _register_handlers(self):
        """Регистрирует обработчики команд и сообщений."""
        # Создаем замыкания для передачи memory_manager в обработчики
        def handle_text_with_memory(update, context):
            return handle_text_message(update, context, self.memory_manager)

        def start_with_memory(update, context):
            return start(update, context, self.memory_manager)

        def help_with_memory(update, context):
            return help_command(update, context, self.memory_manager)

        self.application.add_handler(CommandHandler("start", start_with_memory))
        self.application.add_handler(CommandHandler("help", help_with_memory))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_with_memory))
        self.application.add_handler(CommandHandler("reload_rules", reload_rules_command))
        
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
    logger.warning("telegram_bot.py запущен напрямую. Рекомендуется использовать src/main.py для запуска.")
    main() 