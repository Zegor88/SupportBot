from agents import Agent, RunContextWrapper
from typing import Any
import logging

from src.bot_agents.models import ReplyHandoffData
from .manager import prompt_manager

logger = logging.getLogger("src.bot.config")

async def build_answer_prompt(context_wrapper: RunContextWrapper[Any], agent: Agent[Any]) -> str:
    """
    Dynamically builds the instruction prompt for the AnswerAgent based on the context.
    """
    # 1. Извлекаем ReplyHandoffData из контекста
    if not isinstance(context_wrapper.context, ReplyHandoffData):
        logger.error("Incorrect context type passed to build_answer_prompt. Expected ReplyHandoffData.")
        return prompt_manager.get_prompt("default_prompt")

    handoff_data: ReplyHandoffData = context_wrapper.context

    # 2. Получаем системный промпт из PromptManager
    system_prompt = prompt_manager.get_prompt(handoff_data.system_prompt_key)

    # 3. Добавляем заглушки для будущих данных (Эпик E5)
    # TODO: [E5] Заменить эту заглушку на реальное получение и форматирование истории диалога.
    history_str = "Conversation history is not yet implemented."
    
    # TODO: [E5] Заменить эту заглушку на реальный контекст, полученный от RetrieverAgent.
    rag_context_str = handoff_data.context or "No additional context provided."

    # 4. Собираем итоговый промпт
    final_prompt = f"""{system_prompt}

### Conversation History:
{history_str}

### Provided Context from Knowledge Base:
{rag_context_str}

### User's Question:
{handoff_data.user_message}
"""
    logger.debug(f"Assembled prompt for AnswerAgent with key '{handoff_data.system_prompt_key}'.")
    return final_prompt 