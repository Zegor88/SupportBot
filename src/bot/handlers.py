from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

from .config import Config, logger
from bot_agents.language_validator_agent import LanguageValidatorAgentWrapper, LanguageValidationResult

# Инициализируем валидатор языка (Singleton)
# Это создаст экземпляр при первом импорте модуля handlers
language_validator = LanguageValidatorAgentWrapper()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я Support Bot. Готов помочь."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    logger.info(f"Получена команда /help от пользователя {update.effective_user.id}")
    await update.message.reply_text(
        "Я пока в разработке. Вот что я смогу делать (когда-нибудь):\n"
        "- Отвечать на ваши вопросы\n"
        "- Перенаправлять сложные запросы специалистам\n"
        "Просто напишите мне ваш вопрос."
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для всех текстовых сообщений, включает валидацию языка."""
    user_id = update.effective_user.id
    text = update.message.text
    chat_type = update.message.chat.type

    logger.info(f"Получено текстовое сообщение от {user_id} в чате типа '{chat_type}': '{text[:100]}...'")

    # 1. Валидация языка
    try:
        validation_result: LanguageValidationResult = await language_validator.validate_language(text)
        logger.info(f"Результат валидации языка для user {user_id}: {validation_result}")

        if not validation_result.is_english:
            detected_lang = validation_result.detected_language or "an unknown language"
            reply_message = (
                f"This chat is for English language communication. "
                f"You texted me in {detected_lang}. Please rephrase your question in English."
            )
            logger.info(f"Отправка заглушки о языке пользователю {user_id}: {reply_message}")
            await update.message.reply_text(reply_message)
            return # Прекращаем дальнейшую обработку

    except Exception as e:
        logger.error(f"Ошибка во время валидации языка для user {user_id}: {e}", exc_info=True)
        # В случае ошибки валидации, пока просто пропускаем к echo, чтобы не блокировать пользователя.
        # В будущем можно добавить отправку сообщения об ошибке.
        pass # Продолжаем к основной логике (echo)

    # 2. Если язык английский (или валидация не удалась и мы решили продолжить), выполняем основную логику
    # Пока это просто echo
    logger.info(f"Сообщение от {user_id} прошло валидацию языка (или ошибка валидации проигнорирована), выполняем echo.")
    await update.message.reply_text(f"Echo: {text}")

# Старый echo обработчик будет заменен на handle_text_message
# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Обработчик для всех текстовых сообщений (echo)."""
#     user_id = update.effective_user.id
#     text = update.message.text
#     logger.info(f"Получено сообщение от {user_id}: {text}")
#     await update.message.reply_text(f"Echo: {text}")

# Добавить другие обработчики по мере необходимости 