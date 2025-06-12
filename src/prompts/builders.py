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
    system_prompt_key = handoff_data.system_prompt_key or "default_prompt"
    system_prompt = prompt_manager.get_prompt(system_prompt_key)

    # 3. Получаем остальные данные из handoff_data
    history_str = handoff_data.history or "No conversation history provided."
    
    instruction_str = handoff_data.instruction
    if not instruction_str:
        instruction_str = "No special instructions provided. Follow the standard procedure."

    # 4. Собираем итоговый промпт, подставляя переменные
    # Используем .format() для замены плейсхолдеров типа {history}, {instruction}
    # Плейсхолдер {context} больше не используется, т.к. агент сам получает его через Tool.
    final_prompt = system_prompt.format(
        history=history_str,
        instruction=instruction_str
    )

    logger.debug(f"Assembled prompt for AnswerAgent with key '{handoff_data.system_prompt_key}'.")
    return final_prompt 