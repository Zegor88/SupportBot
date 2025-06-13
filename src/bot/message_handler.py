# src/bot/message_handler.py
# Этот файл содержит основную логику обработки текстовых сообщений от пользователя.

import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .config import Config, logger
from .services import bot_services
from src.bot_agents import RouterDecision, InteractionLog, ReplyHandoffData, RouterDecisionParams
from src.utils.telegram_utils import MessageForwarder
from src.bot_agents import answer_agent

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_manager=None) -> None:
    """Обработчик для всех текстовых сообщений, включает валидацию языка."""
    user_id = update.effective_user.id
    text = update.message.text
    message_id = update.message.message_id

    logger.info(f"Received text message from {user_id}: '{text[:100]}...'")

    if memory_manager:
        memory_manager.add_message(user_id, "user", text)

    # 1. Валидация языка
    try:
        validation_result = await bot_services.language_validator.validate_language(text)
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

    # Проверяем, что ключевые сервисы инициализированы
    if not bot_services.router_agent or not bot_services.rules_manager:
        logger.error(f"RouterAgent или RulesManager не инициализирован. Отправка сообщения об ошибке пользователю {user_id}.")
        await update.message.reply_text(
            "Sorry, the message routing system is currently unavailable. Please try again later."
        )
        return

    # 2. Запуск RouterAgent
    try:
        history = memory_manager.get_history_as_text(user_id) if memory_manager else ""
        run_result = await bot_services.runner.run(
            bot_services.router_agent,
            text,
            context={"history": history}
        )
        
        raw_decision_str = run_result.final_output
        logger.info(f"RouterAgent raw output for user {user_id}: {raw_decision_str}")

        if not isinstance(raw_decision_str, str):
            logger.error(f"RouterAgent for user {user_id} returned non-string output: {type(raw_decision_str)}. Expected JSON string.")
            await update.message.reply_text("Sorry, I received an unexpected response from the routing system.")
            return
        
        parsed_json_str = raw_decision_str.strip().removeprefix("```json").removesuffix("```").strip()
        router_decision = RouterDecision.model_validate_json(parsed_json_str)

        log_data = {
            "uid": user_id,
            "message_id": update.message.message_id,
            "q": text,
            "action": router_decision.action,
            "matched_rule_id": router_decision.matched_rule_id,
            "behavioral_rule_ids": router_decision.behavioral_rule_ids,
            "params": router_decision.params.model_dump_json(exclude_none=True)
        }
        logger.info(f"RouterAgent decision details: {json.dumps(log_data, ensure_ascii=False, indent=2)}")

        # 3. Обработка решения RouterAgent
        await execute_router_decision(update, context, router_decision, text, user_id, memory_manager)

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON от RouterAgent для user {user_id}: {e}. Строка: '{raw_decision_str}'", exc_info=True)
        await update.message.reply_text("Sorry, I couldn't understand the response from the routing system.")
    except Exception as e:
        logger.error(f"Общая ошибка при обработке решения RouterAgent для user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an unexpected error occurred while processing your message.")

async def execute_router_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, decision: RouterDecision, text: str, user_id: int, memory_manager) -> None:
    """Выполняет действие, определенное RouterAgent."""
    action = decision.action
    params = decision.params
    matched_rule_id = decision.matched_rule_id

    if matched_rule_id is None:
        if not Config.REPLY_ON_NO_MATCH:
            logger.info(f"No terminal rule matched for user {user_id} and REPLY_ON_NO_MATCH is False. Processing stopped.")
            return
        else:
            logger.warning(f"No terminal rule matched for user {user_id}, but REPLY_ON_NO_MATCH is True. Proceeding with a default reply.")
            action = "default_reply"
            if not params.system_prompt_key:
                params.system_prompt_key = "default_prompt"

    if action == "drop":
        logger.info(f"Action 'drop' for user {user_id}. Matched rule: {matched_rule_id}. Processing stopped.")
        return

    elif action == "forward":
        await handle_forward_action(update, context, params, user_id, matched_rule_id)

    elif action in ["reply", "default_reply"]:
        await handle_reply_action(update, context, text, user_id, memory_manager, matched_rule_id, params)

    else:
        logger.warning(f"Unknown action '{action}' from RouterAgent for user {user_id}. Decision: {decision}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, I received an unknown instruction from the routing system.",
            reply_to_message_id=update.message.message_id
        )

async def handle_forward_action(update: Update, context: ContextTypes.DEFAULT_TYPE, params: RouterDecisionParams, user_id: int, matched_rule_id: str | None) -> None:
    """Обрабатывает действие 'forward'."""
    destination_chat_id = params.destination_chat_id
    if not destination_chat_id:
        logger.error(f"Action 'forward' for user {user_id}, but 'destination_chat_id' is missing. Matched rule: {matched_rule_id}")
        await update.message.reply_text("Sorry, I was asked to forward your message, but the destination is unclear.")
        return

    forwarder = MessageForwarder(bot=context.bot)
    success = await forwarder.forward_message(
        original_message_id=update.message.message_id,
        from_chat_id=update.message.chat_id,
        target_chat_id=destination_chat_id
    )
    if success:
        logger.info(f"Message successfully forwarded to {destination_chat_id} for user {user_id}. Matched rule: {matched_rule_id}")
    else:
        logger.warning(f"Failed to forward message for user {user_id}. Matched rule: {matched_rule_id}")
        await update.message.reply_text("Sorry, I could not forward your message at this time.")

async def handle_reply_action(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int, memory_manager, matched_rule_id: str | None, params: RouterDecisionParams) -> None:
    """Обрабатывает действие 'reply' или 'default_reply'."""
    # Если есть response_text, то отправляем его пользователю
    if params.response_text:
        logger.info(f"Action 'reply' (direct response) for user {user_id}. Matched rule: {matched_rule_id}.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=params.response_text,
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Если есть system_prompt_key, то отправляем его пользователю
    if params.system_prompt_key:
        await handle_answer_agent_handoff(update, context, text, user_id, memory_manager, matched_rule_id, params)
        return
    
    logger.error(f"Action 'reply' for user {user_id}, but no 'response_text' or 'system_prompt_key'. Matched rule: {matched_rule_id}.")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I was asked to reply, but I don't have the required information.",
        reply_to_message_id=update.message.message_id
    )

async def handle_answer_agent_handoff(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int, memory_manager, matched_rule_id: str | None, params: RouterDecisionParams) -> None:
    """Handles the RAG and AnswerAgent pipeline."""
    history = memory_manager.get_history_as_text(user_id) if memory_manager else ""
    
    final_instructions = []
    if matched_rule_id and (rule := bot_services.rules_manager.get_rule_by_id(matched_rule_id)) and hasattr(rule, 'instruction') and rule.instruction:
        final_instructions.append(rule.instruction)
    if params.behavioral_prompts:
        final_instructions.extend(params.behavioral_prompts)
    instruction_text = "\n".join(final_instructions)

    handoff_data = ReplyHandoffData(
        user_message=text,
        system_prompt_key=params.system_prompt_key,
        history=history,
        instruction=instruction_text,
        behavioral_prompts=params.behavioral_prompts
    )

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        from src.prompts import build_answer_prompt
        from agents import RunContextWrapper
        run_context_wrapper = RunContextWrapper(context=handoff_data)
        final_prompt_for_agent = await build_answer_prompt(run_context_wrapper, answer_agent)
        
        logger.info(f"Final prompt for AnswerAgent (user: {user_id}):\n--- PROMPT START ---\n{final_prompt_for_agent}\n--- PROMPT END ---")
        
        answer_result = await bot_services.runner.run(answer_agent, text, context=handoff_data)
        final_response = str(answer_result.final_output)
        
        if memory_manager:
            memory_manager.add_message(user_id, "assistant", final_response)

        log_entry = InteractionLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            matched_rule_id=matched_rule_id,
            action="reply_with_answer_agent",
            question=text,
            answer=final_response,
            final_prompt=final_prompt_for_agent
        )
        await bot_services.logger_agent.log_interaction(log_entry)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=final_response,
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        error_message = "Sorry, I encountered an error while generating a detailed response."
        if memory_manager:
            memory_manager.add_message(user_id, "assistant", error_message)
        logger.error(f"Error executing AnswerAgent for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_message,
            reply_to_message_id=update.message.message_id
        ) 