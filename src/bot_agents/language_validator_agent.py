from typing import Optional
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelBehaviorError # Используем SDK, добавляем ModelBehaviorError
import os # Для OPENAI_API_KEY, если он не установлен глобально для SDK

class LanguageValidationResult(BaseModel):
    is_english: bool = Field(description="True if the text is predominantly in English, False otherwise.")
    detected_language: Optional[str] = Field(default=None, description="The name of the detected language if not English (e.g., 'Spanish', 'French').")
    #reply_needed: bool = Field(..., description="True if a standardized reply should be sent to the user.") # Решено на уровне интеграции

# Обновленный промпт, который будет использоваться в Agent.instructions
# Он описывает задачу и ожидаемый формат JSON, предполагая, что сообщение пользователя будет основным вводом.
REVISED_LANGUAGE_VALIDATOR_PROMPT = """
Your primary task is to analyze the user's input text and determine its main language.

If the primary language of the text is English, you MUST respond with the following JSON structure:
{
    "is_english": true,
    "detected_language": null
}

If the primary language of the text is NOT English, you MUST identify the name of the language (e.g., Spanish, French, German, Russian, Chinese, Japanese, etc.) and respond with the following JSON structure, replacing "<LanguageName>" with the actual detected language name:
{
    "is_english": false,
    "detected_language": "<LanguageName>"
}

IMPORTANT: Your entire response MUST be ONLY the JSON object described above. Do not include any other text, explanations, dialogue, or markdown formatting around the JSON. Ensure the JSON keys and value types (boolean for is_english, string or null for detected_language) are exactly as specified.

Example for a non-English message (e.g., user input is "Hola, ¿cómo estás?"):
{
    "is_english": false,
    "detected_language": "Spanish"
}

Example for an English message (e.g., user input is "Hello, how are you?"):
{
    "is_english": true,
    "detected_language": null
}
"""

class LanguageValidatorAgentWrapper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LanguageValidatorAgentWrapper, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "gpt-4o-mini"):
        if self._initialized:
            return
        
        # SDK обычно ожидает, что OPENAI_API_KEY установлен как переменная окружения.
        # Дополнительная проверка или установка здесь может быть излишней, если .env загружается глобально.
        # if not os.getenv("OPENAI_API_KEY"):
        #     raise ValueError("OPENAI_API_KEY environment variable not set.")

        self.agent = Agent(
            name="LanguageValidatorAgent",
            instructions=REVISED_LANGUAGE_VALIDATOR_PROMPT,
            output_type=LanguageValidationResult,
            model=model_name 
        )
        self._initialized = True
        print(f"LanguageValidatorAgentWrapper initialized with model: {model_name}") # Для отладки

    async def validate_language(self, user_message: str) -> LanguageValidationResult:
        """
        Validates the language of the user_message using the LLM agent.
        The user_message is passed as the primary input to the agent.
        """
        if not user_message or not user_message.strip():
            # Возвращаем как английский, чтобы не блокировать пустые сообщения, 
            # или можно определить специальное поведение
            return LanguageValidationResult(is_english=True, detected_language=None)
            
        print(f"Validator: Sending to Agent SDK: '{user_message[:50]}...' ") # Для отладки
        try:
            # Runner.run() ожидает 'input' как именованный аргумент для основного содержания.
            # Однако, стандартная практика SDK - передавать его как позиционный аргумент после агента.
            result = await Runner.run(self.agent, user_message) 
            # result = await Runner.run(agent=self.agent, input=user_message)
            
            validated_output = result.final_output_as(LanguageValidationResult)
            print(f"Validator: Received from Agent SDK: {validated_output}") # Для отладки
            return validated_output
        except ModelBehaviorError as mbe:
            print(f"ModelBehaviorError (LLM likely returned invalid format for Pydantic model or other model misbehavior): {mbe}")
            # Если LLM не смогла вернуть ожидаемый JSON, считаем, что язык не определен (или потенциально не английский).
            # Отправка заглушки об ошибке может быть лучшим вариантом, чем тихий пропуск.
            return LanguageValidationResult(is_english=False, detected_language="Language check failed: LLM output format issue")
        except Exception as e:
            print(f"Generic error during LanguageValidatorAgent execution: {type(e).__name__} - {e}")
            # В случае общей непредвиденной ошибки, безопаснее пропустить как английский, 
            # чтобы не блокировать пользователя безвозвратно, но с логированием ошибки.
            # Альтернативно, можно также вернуть is_english=False и специфичное сообщение об ошибке.
            return LanguageValidationResult(is_english=True, detected_language=f"Validation Error: An unexpected error occurred ({type(e).__name__})")

# Здесь будет реализация самого агента с использованием OpenAI Agents SDK
# from agents import Agent, Runner # и т.д.

# class LanguageValidatorAgent:
#     def __init__(self, api_key: str):
#         self.agent = Agent(
#             name="LanguageValidatorAgent",
#             instructions=LANGUAGE_VALIDATOR_PROMPT, # Этот промпт нужно будет адаптировать под {{user_message}} 
#             output_type=LanguageValidationResult, 
#             # model="o3-mini" # или другой подходящий, например gpt-4o-mini
#         )
#         # self.runner = Runner() # Runner может быть общим

#     async def validate_language(self, user_message: str) -> LanguageValidationResult:
#         # Промпт нужно будет отформатировать с user_message перед передачей в агент.
#         # OpenAI Agents SDK может иметь свой способ передачи входных данных, который заполнит {{user_message}}.
#         # Нужно будет изучить, как Runner.run() или аналогичный метод SDK обрабатывает входные данные для промпта.
         
#         # formatted_prompt = LANGUAGE_VALIDATOR_PROMPT.replace("{{user_message}}", user_message)
#         # Вместо прямого форматирования, SDK ожидает, что переменные в промпте будут разрешены из входных данных.
#         # Мы передадим user_message как входные данные в Runner.run.

#         # result = await Runner.run(self.agent, user_message) # Передаем просто сообщение
#         # return result.final_output_as(LanguageValidationResult)
#         pass # Заглушка

# TODO:
# 1. Определиться с моделью (o3-mini, gpt-4o-mini)
# 2. Изучить, как правильно передавать user_message в промпт через OpenAI Agents SDK Runner.
#    Вероятно, {{user_message}} в `instructions` не будет работать напрямую так, как здесь написано.
#    SDK может ожидать, что `instructions` - это общий системный промпт, а пользовательское сообщение передается как `input_data` в `Runner.run()`,
#    и LLM сама поймет, что `input_data` - это то, что нужно анализировать.
#    Или же `instructions` могут быть динамическими. См. https://openai.github.io/openai-agents-python/agents/#dynamic-instructions
# 3. Реализовать класс LanguageValidatorAgent и метод validate_language.
# 4. Настроить OPENAI_API_KEY для SDK. 