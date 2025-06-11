# src/bot/handlers.py
# This file contains the handlers for the bot.
# It is used to handle the commands and messages from the users.

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import json # Для парсинга ответа RouterAgent
from telegram.constants import ParseMode
from datetime import datetime

from .config import Config, logger # Оставим config logger, но будем использовать и стандартный logging

# Импорты для агентов и моделей
from src.bot_agents import (
    LanguageValidatorAgentWrapper,
    RouterAgent,
    RetrieverAgent,
    answer_agent,
    Logger as BotLogger,
    InteractionLog,
    RouterDecision,
    ReplyHandoffData,
    RouterDecisionParams
)
from src.rules_manager.manager import RulesManager, RulesFileError # Менеджер правил
from src.tools.telegram_tools import ForwardTool # Инструмент для пересылки

from agents import Runner # Runner из SDK для запуска RouterAgent

# ========= 1. Инициализация =========
# 1.1. Инициализация менеджера правил и RouterAgent
try:
    rules_manager = RulesManager(rules_file_path="rules.yaml") # Путь к файлу правил
    router_agent_instance = RouterAgent(rules_manager=rules_manager) # Инициализация RouterAgent
    logger.info(f"RulesManager and RouterAgent initialized successfully with {len(rules_manager.get_rules())} rules.") # Логирование успешного инициализации
except (RulesFileError, Exception) as e:
    logger.error(f"CRITICAL: Failed to initialize RulesManager or RouterAgent: {e}", exc_info=True)
    rules_manager = None
    router_agent_instance = None

# 1.2. Инициализация валидатора языка
language_validator = LanguageValidatorAgentWrapper()

# 1.3. Инициализация агента логгирования
logger_agent = BotLogger()

# 1.4. Инициализация RetrieverAgent
try:
    retriever_agent = RetrieverAgent()
    logger.info("RetrieverAgent initialized successfully.")
except Exception as e:
    retriever_agent = None
    logger.error(f"CRITICAL: Failed to initialize RetrieverAgent: {e}", exc_info=True)

# ========= 2. Обработчики =========
# 2.1. Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    logger.info(f"Received /start command from user {user_id}.")
    
    response = "Hello! I am a support bot. How can I help you?"

    # Добавляем сообщение в память
    if memory_manager:
        memory_manager.add_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)

# 2.2. Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик команды /help."""
    user_id = update.effective_user.id
    logger.info(f"Received /help command from user {user_id}.")
    
    response = "You can ask me any questions, and I will do my best to help you."

    # Добавляем сообщение в память
    if memory_manager:
        memory_manager.add_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)

# ========= 3. Обработчик всех текстовых сообщений =========
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик для всех текстовых сообщений, включает валидацию языка."""
    user_id = update.effective_user.id
    text = update.message.text
    chat_type = update.message.chat.type

    logger.info(f"Received text message from {user_id}: '{text[:100]}...'")

    # Добавляем сообщение в память
    if memory_manager:
        memory_manager.add_message(user_id, "user", text)

    # 1. Валидация языка
    try:
        validation_result = await language_validator.validate_language(text)
        if not validation_result.is_english:
            detected_lang = validation_result.detected_language or "an unknown language"
            reply_message = f"This chat is for English language communication. You texted me in {detected_lang}. Please rephrase your question in English."
            await update.message.reply_text(reply_message)
            return
    except Exception as e:
        logger.error(f"Language validation error for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I had trouble processing the language of your message.")
        return

    logger.info(f"Message from {user_id} passed language validation. Calling RouterAgent...")

    # Проверяем, что RouterAgent и RulesManager инициализированы
    if not router_agent_instance or not rules_manager:
        logger.error(f"RouterAgent или RulesManager не инициализирован. Отправка сообщения об ошибке пользователю {user_id}.")
        await update.message.reply_text(
            "Sorry, the message routing system is currently unavailable. Please try again later."
        )
        return

    # 2. Запуск RouterAgent
    try:
        run_result = await Runner.run(router_agent_instance, text) 
        
        # RouterAgent должен вернуть JSON строку, которую мы парсим в RouterDecision
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
        # Старый лог решения, можно будет удалить или изменить после рефакторинга
        # logger.info(f"RouterAgent decision for user {user_id}: {router_decision}")

        # --- Новое расширенное логирование решения RouterAgent ---
        # В соответствии с FR-LOG-2 из TR-E3.6.md
        log_data = {
            "uid": user_id,
            "message_id": update.message.message_id,
            "q": text, # Полный текст сообщения
            "action": router_decision.action,
            "matched_rule_id": router_decision.matched_rule_id,
            "params": router_decision.params.model_dump_json(exclude_none=True)
        }
        logger.info(f"RouterAgent decision details: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
        # --- Конец нового расширенного логирования ---

        # 3. Обработка решения RouterAgent
        action = router_decision.action
        params = router_decision.params
        matched_rule_id = router_decision.matched_rule_id

        if action == "drop":
            logger.info(f"Действие 'drop' для user {user_id} (сообщение: '{text[:50]}...'). Matched rule: {matched_rule_id}. Обработка прекращена.")
            # Ничего не делаем, просто логируем
            return

        elif action == "forward":
            destination_chat_id = params.destination_chat_id
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
                logger.info(f"Сообщение {original_message_id} успешно переслано в {destination_chat_id} для user {user_id}.")
            else:
                logger.warning(f"Не удалось переслать сообщение {original_message_id} в {destination_chat_id} для user {user_id}.")
                await update.message.reply_text("Sorry, I could not forward your message at this time.")
            return

        elif action == "reply" or action == "default_reply":
            response_text = params.response_text
            system_prompt_key = params.system_prompt_key

            if response_text:
                logger.info(f"Действие 'reply' (прямой ответ) для user {user_id}. Matched rule: {matched_rule_id}. Ответ: '{response_text[:100]}...'" )
                await update.message.reply_text(response_text)
                return
            
            elif system_prompt_key:
                # --- Запуск RAG и AnswerAgent пайплайна ---
                await handle_answer_agent_handoff(
                    update, text, user_id, memory_manager, matched_rule_id, params
                )
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

async def handle_answer_agent_handoff(update: Update, text: str, user_id: int, memory_manager, matched_rule_id: str, params: RouterDecisionParams) -> None:
    """Handles the pipeline for getting a response from the AnswerAgent."""
    
    # 1. Получение контекста из RetrieverAgent
    retrieved_context = None
    if retriever_agent:
        try:
            retrieved_context = await retriever_agent.retrieve_context(text)
            logger.info(f"RetrieverAgent returned context for user {user_id}.")
        except Exception as e:
            logger.error(f"Error calling RetrieverAgent for user {user_id}: {e}", exc_info=True)
    
    # 2. Получение истории диалога и инструкций
    history = memory_manager.get_history_as_text(user_id) if memory_manager else ""
    
    # 3. Сборка инструкций: основные + поведенческие
    final_instructions = []
    matched_rule = rules_manager.get_rule_by_id(matched_rule_id) if matched_rule_id else None
    
    # Основная инструкция из правила (если есть)
    if matched_rule and hasattr(matched_rule, 'instruction') and matched_rule.instruction:
        final_instructions.append(matched_rule.instruction)
        
    # Поведенческие инструкции
    if params.behavioral_prompts:
        final_instructions.extend(params.behavioral_prompts)
        
    instruction_text = "\n".join(f"- {inst}" for inst in final_instructions) if final_instructions else ""

    # 4. Создание объекта с данными для AnswerAgent
    handoff_data = ReplyHandoffData(
        user_message=text,
        system_prompt_key=params.system_prompt_key,
        context=retrieved_context,
        history=history,
        instruction=instruction_text,
        behavioral_prompts=params.behavioral_prompts # на всякий случай, если понадобится в будущем
    )

    await update.message.reply_chat_action('typing')

    # 5. Запуск AnswerAgent
    try:
        answer_result = await Runner.run(answer_agent, text, context=handoff_data)
        final_response = str(answer_result.final_output)
        logger.info(f"AnswerAgent returned response for user {user_id}: '{final_response[:150]}...'")

        if memory_manager:
            memory_manager.add_message(user_id, "assistant", final_response)
        
        # Логирование взаимодействия
        log_entry = InteractionLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            matched_rule_id=matched_rule_id,
            action="reply_with_answer_agent",
            question=text,
            answer=final_response,
            context=retrieved_context
        )
        await logger_agent.log_interaction(log_entry)
        
        await update.message.reply_text(final_response)

    except Exception as e:
        error_message = "Sorry, I encountered an error while generating a detailed response."
        if memory_manager:
            memory_manager.add_message(user_id, "assistant", error_message)
        logger.error(f"Error executing AnswerAgent for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(error_message)

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
    success = rules_manager.reload_rules()
    
    if success:
        num_rules = len(rules_manager.get_rules())
        logger.info(f"Правила успешно перезагружены администратором {user_id}. Всего правил: {num_rules}")
        await update.message.reply_text(
            f"Правила успешно перезагружены. Теперь управляется {num_rules} правилами."
        )
    else:
        logger.warning(f"Администратор {user_id} столкнулся с ошибкой при перезагрузке правил. Предыдущие правила восстановлены.")
        await update.message.reply_text(
            "Ошибка при перезагрузке правил. Детали ошибки залогированы. Были восстановлены предыдущие правила."
        )