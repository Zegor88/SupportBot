# src/bot/handlers.py
# Этот файл содержит обработчики для команд Telegram.
# Основная логика обработки текстовых сообщений вынесена в message_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from .config import Config, logger
from .services import bot_services # Импортируем централизованные сервисы
from .message_handler import handle_text_message # Импортируем основной обработчик

# ========= Обработчики команд =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    logger.info(f"Received /start command from user {user_id}.")
    
    response = "Hello! I am a support bot. How can I help you?"

    if memory_manager:
        memory_manager.add_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик команды /help."""
    user_id = update.effective_user.id
    logger.info(f"Received /help command from user {user_id}.")
    
    response = "You can ask me any questions, and I will do my best to help you."

    if memory_manager:
        memory_manager.add_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)

async def reload_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /reload_rules для перезагрузки правил из rules.yaml."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /reload_rules от пользователя {user_id}.")

    if not Config.ADMIN_USER_IDS:
        logger.warning(f"Попытка вызова /reload_rules пользователем {user_id}, но список ADMIN_USER_IDS пуст.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Команда не настроена: список администраторов не определен."
        )
        return

    if user_id not in Config.ADMIN_USER_IDS:
        logger.warning(f"Неавторизованный пользователь {user_id} попытался выполнить /reload_rules.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="У вас нет прав для выполнения этой команды."
        )
        return

    if not bot_services.rules_manager:
        logger.error(f"RulesManager не инициализирован. Пользователь {user_id} не может перезагрузить правила.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ошибка: Сервис управления правилами недоступен."
        )
        return
    
    logger.info(f"Администратор {user_id} инициировал перезагрузку правил.")
    success = bot_services.rules_manager.reload_rules()
    
    if success:
        num_rules = len(bot_services.rules_manager.get_rules())
        logger.info(f"Правила успешно перезагружены администратором {user_id}. Всего правил: {num_rules}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Правила успешно перезагружены. Теперь управляется {num_rules} правилами."
        )
    else:
        logger.warning(f"Администратор {user_id} столкнулся с ошибкой при перезагрузке правил.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ошибка при перезагрузке правил. Детали ошибки залогированы."
        )

__all__ = ["start", "help_command", "reload_rules_command", "handle_text_message"]