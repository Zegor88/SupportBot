# src/bot/handlers.py
# Этот файл содержит обработчики для команд Telegram.
# Основная логика обработки текстовых сообщений вынесена в message_handler.py

from telegram import Update
from telegram.ext import ContextTypes
import base64
import io

from .config import Config, logger
from .services import bot_services # Импортируем централизованные сервисы
from .message_handler import handle_text_message # Импортируем основной обработчик
from openai import AsyncOpenAI

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

# ========= Обработчик изображений =========

async def describe_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщения с фотографиями, генерирует описание с помощью Vision LLM
    и отправляет его пользователю.
    """
    if not update.message or not update.message.photo:
        return

    chat_id = update.message.chat_id
    message_id = update.message.message_id
    logger.info(f"Получено изображение от пользователя в чате {chat_id}.")

    try:
        # 1. Получаем клиент OpenAI из контекста бота
        openai_client: AsyncOpenAI = context.bot_data.get('openai_client')
        if not openai_client:
            logger.error(f"Клиент OpenAI не найден в контексте для чата {chat_id}.")
            raise ValueError("OpenAI client not configured.")

        # 2. Получаем и скачиваем файл изображения в память
        photo = update.message.photo[-1]  # Берем фото самого высокого разрешения
        photo_file = await photo.get_file()
        
        image_stream = io.BytesIO()
        await photo_file.download_to_memory(image_stream)
        image_stream.seek(0)
        
        # 3. Кодируем изображение в base64
        base64_image = base64.b64encode(image_stream.read()).decode('utf-8')

        # 4. Отправляем запрос в LLM для получения описания
        logger.info(f"Отправка изображения из чата {chat_id} в Vision LLM ({Config.OPENAI_VISION_MODEL}).")
        
        response = await openai_client.chat.completions.create(
            model=Config.OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": Config.OPENAI_VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                    ],
                }
            ],
            max_tokens=300,
        )

        description = response.choices[0].message.content

        # 5. Отправляем ответ пользователю
        if description:
            logger.info(f"Успешно получено описание для изображения из чата {chat_id}.")
            await context.bot.send_message(
                chat_id=chat_id,
                text=description,
                reply_to_message_id=message_id
            )
        else:
            logger.warning(f"Vision LLM вернул пустое описание для изображения из чата {chat_id}.")
            raise ValueError("LLM returned an empty description.")

    except Exception as e:
        logger.error(f"Не удалось обработать изображение для чата {chat_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="К сожалению, не удалось проанализировать изображение. Пожалуйста, попробуйте позже.",
            reply_to_message_id=message_id
        )

__all__ = ["start", "help_command", "reload_rules_command", "handle_text_message", "describe_image_handler"]