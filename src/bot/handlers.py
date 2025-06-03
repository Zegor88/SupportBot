from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import json # Для парсинга ответа RouterAgent

from .config import Config, logger # Оставим config logger, но будем использовать и стандартный logging
# Импорты для агентов и моделей
from src.bot_agents.language_validator_agent import LanguageValidatorAgentWrapper, LanguageValidationResult
from src.bot_agents.router_agent import RouterAgent # Сам RouterAgent
from src.bot_agents.models import RouterDecision, ReplyHandoffData # Модели
from src.rules_manager.manager import RulesManager, RulesFileError # Менеджер правил
from src.tools.telegram_tools import ForwardTool # Инструмент для пересылки

from agents import Runner # Runner из SDK для запуска RouterAgent

# Настройка стандартного логгера, если еще не настроен глобально
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Инициализация менеджера правил и RouterAgent ---
try:
    rules_manager = RulesManager(rules_file_path="rules.yaml") # Путь к файлу правил
    router_agent_instance = RouterAgent(rules_manager=rules_manager)
    logger.info(f"RulesManager and RouterAgent initialized successfully with {len(rules_manager.get_rules())} rules.")
except RulesFileError as e:
    logger.error(f"CRITICAL: Failed to initialize RulesManager or RouterAgent: {e}", exc_info=True)
    # В случае ошибки инициализации, бот может работать некорректно или не сможет обрабатывать правила.
    # Можно либо остановить бота, либо работать в ограниченном режиме.
    rules_manager = None
    router_agent_instance = None
    # Добавим обработку ниже, чтобы бот сообщал об этой проблеме, если агенты не загружены
except Exception as e:
    logger.error(f"CRITICAL: Unexpected error during RulesManager/RouterAgent initialization: {e}", exc_info=True)
    rules_manager = None
    router_agent_instance = None

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
        await update.message.reply_text(
            "Sorry, I encountered an issue while processing the language of your message. "
            "Please try again, or contact support if the problem persists."
        )
        return

    # 2. Если язык английский, передаем сообщение в RouterAgent
    logger.info(f"Сообщение от {user_id} прошло валидацию языка. Вызов RouterAgent...")

    if not router_agent_instance or not rules_manager:
        logger.error(f"RouterAgent или RulesManager не инициализирован. Отправка сообщения об ошибке пользователю {user_id}.")
        await update.message.reply_text(
            "Sorry, the message routing system is currently unavailable. Please try again later."
        )
        return

    try:
        # Запуск RouterAgent
        # Входные данные для RouterAgent - это просто текст сообщения пользователя.
        # Runner.run ожидает именованный аргумент 'input' или просто позиционный аргумент.
        # router_agent_instance.run(text) - если бы мы вызывали метод напрямую, но мы используем Runner
        run_result = await Runner.run(router_agent_instance, text) 
        
        # RouterAgent должен вернуть JSON строку, которую мы парсим в RouterDecision
        # (Это поведение из текущей реализации RouterAgent)
        raw_decision_str = run_result.final_output
        logger.info(f"RouterAgent raw output for user {user_id}: {raw_decision_str}")

        if not isinstance(raw_decision_str, str):
            logger.error(f"RouterAgent for user {user_id} returned non-string output: {type(raw_decision_str)}. Expected JSON string.")
            await update.message.reply_text("Sorry, I received an unexpected response from the routing system.")
            return
        
        # Очистка и парсинг JSON
        parsed_json_str = raw_decision_str.strip()
        if parsed_json_str.startswith("```json"):
            parsed_json_str = parsed_json_str[7:]
        if parsed_json_str.endswith("```"):
            parsed_json_str = parsed_json_str[:-3]
        parsed_json_str = parsed_json_str.strip()

        router_decision = RouterDecision.model_validate_json(parsed_json_str)
        logger.info(f"RouterAgent decision for user {user_id}: {router_decision}")

        # 3. Обработка решения RouterAgent
        action = router_decision.action
        params = router_decision.params
        matched_rule_id = router_decision.matched_rule_id

        if action == "drop":
            logger.info(f"Действие 'drop' для user {user_id} (сообщение: '{text[:50]}...'). Matched rule: {matched_rule_id}. Обработка прекращена.")
            # Ничего не делаем, просто логируем
            return

        elif action == "forward":
            destination_chat_id = params.get("destination_chat_id")
            if not destination_chat_id:
                logger.error(f"Действие 'forward' для user {user_id}, но 'destination_chat_id' отсутствует в параметрах. Matched rule: {matched_rule_id}")
                await update.message.reply_text("Sorry, I was asked to forward your message, but the destination is unclear.")
                return

            forward_tool = ForwardTool(bot=context.bot)
            original_message_id = update.message.message_id
            from_chat_id = update.message.chat_id
            
            logger.info(f"Действие 'forward' для user {user_id}: пересылка сообщения {original_message_id} из чата {from_chat_id} в {destination_chat_id}. Matched rule: {matched_rule_id}")
            success = await forward_tool.forward_message(
                original_message_id=original_message_id,
                from_chat_id=from_chat_id,
                target_chat_id=destination_chat_id
            )
            if success:
                # Можно добавить ответ пользователю, что его сообщение переслано, если это требуется
                # await update.message.reply_text("Your message has been forwarded.") 
                logger.info(f"Сообщение {original_message_id} успешно переслано в {destination_chat_id} для user {user_id}.")
            else:
                logger.warning(f"Не удалось переслать сообщение {original_message_id} в {destination_chat_id} для user {user_id}.")
                await update.message.reply_text("Sorry, I could not forward your message at this time.")
            return

        elif action == "reply" or action == "default_reply":
            response_text = params.get("response_text")
            system_prompt_key = params.get("system_prompt_key")

            if response_text:
                logger.info(f"Действие 'reply' (прямой ответ) для user {user_id}. Matched rule: {matched_rule_id}. Ответ: '{response_text[:100]}...'" )
                await update.message.reply_text(response_text)
                return
            
            elif system_prompt_key:
                # Подготовка к Handoff для AnswerAgent (Эпик 5)
                # Пока просто логируем и сообщаем пользователю, что запрос обрабатывается
                # В будущем здесь будет реальный handoff
                history = [] # Заглушка для истории, нужно будет реализовать сбор истории
                handoff_data = ReplyHandoffData(
                    user_message=text,
                    history=history, # TODO: Заполнить реальной историей диалога
                    system_prompt_key=system_prompt_key
                )
                logger.info(f"Действие 'reply' (через AnswerAgent) для user {user_id}. Matched rule: {matched_rule_id}. Handoff data prepared: {handoff_data}")
                await update.message.reply_text(
                    "Your request requires a detailed answer. I am processing it... (AnswerAgent handoff placeholder)"
                )
                # ЗАГЛУШКА: Здесь будет вызов handoff(agent=answer_agent, input_data=handoff_data)
                # Например:
                # answer_agent_placeholder = ... # Экземпляр AnswerAgent
                # await context.handoff(answer_agent_placeholder, handoff_data)
                return
            
            else:
                logger.error(f"Действие 'reply'/'default_reply' для user {user_id}, но нет 'response_text' или 'system_prompt_key'. Matched rule: {matched_rule_id}. Params: {params}")
                await update.message.reply_text("Sorry, I was asked to reply, but I don't have the required information.")
                return
        else:
            logger.warning(f"Неизвестное действие '{action}' от RouterAgent для user {user_id}. Decision: {router_decision}")
            await update.message.reply_text("Sorry, I received an unknown instruction from the routing system.")
            return

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON от RouterAgent для user {user_id}: {e}. Строка: '{raw_decision_str}'", exc_info=True)
        await update.message.reply_text("Sorry, I couldn't understand the response from the routing system.")
        return
    except Exception as e:
        logger.error(f"Общая ошибка при обработке решения RouterAgent для user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an unexpected error occurred while processing your message.")
        return

async def reload_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /reload_rules для перезагрузки правил из rules.yaml."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /reload_rules от пользователя {user_id}.")

    if not Config.ADMIN_USER_IDS:
        logger.warning(f"Попытка вызова /reload_rules пользователем {user_id}, но список ADMIN_USER_IDS пуст.")
        await update.message.reply_text(
            "Команда не настроена: список администраторов не определен."
        )
        return

    if user_id not in Config.ADMIN_USER_IDS:
        logger.warning(f"Неавторизованный пользователь {user_id} попытался выполнить /reload_rules.")
        await update.message.reply_text(
            "У вас нет прав для выполнения этой команды."
        )
        return

    if not rules_manager:
        logger.error(f"RulesManager не инициализирован. Пользователь {user_id} не может перезагрузить правила.")
        await update.message.reply_text(
            "Ошибка: Сервис управления правилами недоступен. Невозможно перезагрузить правила."
        )
        return
    
    logger.info(f"Администратор {user_id} инициировал перезагрузку правил.")
    try:
        # Метод reload_rules() в RulesManager теперь возвращает bool и не кидает исключения наружу,
        # а обрабатывает их внутри и логирует.
        success = rules_manager.reload_rules()
        
        if success:
            logger.info(f"Правила успешно перезагружены администратором {user_id}. Количество правил: {len(rules_manager.get_rules())}")
            await update.message.reply_text(
                f"Правила успешно перезагружены. Загружено правил: {len(rules_manager.get_rules())}."
            )
        else:
            # RulesManager уже залогировал детали ошибки
            logger.warning(f"Администратор {user_id} столкнулся с ошибкой при перезагрузке правил. Предыдущие правила восстановлены.")
            await update.message.reply_text(
                "Ошибка при перезагрузке правил. Детали ошибки залогированы. Были восстановлены предыдущие правила."
            )
            
    except Exception as e: # Дополнительный общий перехват на всякий случай
        logger.error(f"Непредвиденная ошибка при выполнении /reload_rules для {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла непредвиденная ошибка при попытке перезагрузить правила. Пожалуйста, проверьте логи."
        )

# Старый echo обработчик будет заменен на handle_text_message
# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Обработчик для всех текстовых сообщений (echo)."""
#     user_id = update.effective_user.id
#     text = update.message.text
#     logger.info(f"Получено сообщение от {user_id}: {text}")
#     await update.message.reply_text(f"Echo: {text}")

# Добавить другие обработчики по мере необходимости 