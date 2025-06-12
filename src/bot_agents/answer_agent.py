from agents import Agent, ModelSettings
from src.tools.rag_tools import retrieve_rag_context

# Импортируем нашу новую динамическую функцию-сборщик промптов
from src.prompts import build_answer_prompt

# Создание и экспорт экземпляра агента
answer_agent = Agent(
    name="AnswerAgent",
    model="gpt-4o-mini",
    instructions=build_answer_prompt,
    tools=[retrieve_rag_context],
    model_settings=ModelSettings(
        temperature=0.7,
        max_tokens=500,
    ),
)

__all__ = ["answer_agent"] 