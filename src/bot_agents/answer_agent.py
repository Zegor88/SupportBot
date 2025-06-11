from agents import Agent, RunContextWrapper, ModelSettings
from typing import Any

# Импортируем нашу новую динамическую функцию-сборщик промптов
from src.prompts import build_answer_prompt

# Временная функция-заглушка для `instructions`. 
# В задаче E4.2 она будет заменена на реальную логику построения промпта.
def build_answer_prompt(context_wrapper: RunContextWrapper[Any], agent: Agent[Any]) -> str:
    """
    (Mock) Builds the prompt for the AnswerAgent.
    Returns a static prompt for now.
    """
    # В будущем здесь будет логика извлечения данных из context_wrapper.context,
    # который будет содержать UserContext с ReplyHandoffData.
    return "You are a helpful assistant. Please answer the user's question based on the provided context."

# Создание и экспорт экземпляра агента в соответствии с TR-E4.1 и TR-E4.2
answer_agent = Agent(
    name="AnswerAgent",
    model="gpt-4o-mini",
    instructions=build_answer_prompt,
    # В соответствии с ТЗ добавляем model_settings (из Epic4.md)
    model_settings=ModelSettings(
        temperature=0.7,
        max_tokens=500,
    ),
    # output_type не указываем, так как по умолчанию ожидается текстовый ответ (str).
)

__all__ = ["answer_agent"] 