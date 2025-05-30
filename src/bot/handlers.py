from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

from .config import Config, logger

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

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для всех текстовых сообщений (echo)."""
    user_id = update.effective_user.id
    text = update.message.text
    logger.info(f"Получено сообщение от {user_id}: {text}")
    await update.message.reply_text(f"Echo: {text}")

# Добавить другие обработчики по мере необходимости 