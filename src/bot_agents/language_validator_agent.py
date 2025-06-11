from typing import Optional
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelBehaviorError

class LanguageValidationResult(BaseModel):
    is_english: bool = Field(description="True if the text is predominantly in English, False otherwise.")
    detected_language: Optional[str] = Field(default=None, description="The name of the detected language if not English (e.g., 'Spanish', 'French').")

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

        self.agent = Agent(
            name="LanguageValidatorAgent",
            instructions=REVISED_LANGUAGE_VALIDATOR_PROMPT,
            output_type=LanguageValidationResult,
            model=model_name 
        )
        self._initialized = True

    async def validate_language(self, user_message: str) -> LanguageValidationResult:
        """
        Validates the language of the user_message using the LLM agent.
        The user_message is passed as the primary input to the agent.
        """
        if not user_message or not user_message.strip():
            return LanguageValidationResult(is_english=True, detected_language=None)
            
        try:
            result = await Runner.run(self.agent, user_message) 
            
            validated_output = result.final_output_as(LanguageValidationResult)
            return validated_output
        except ModelBehaviorError as mbe:
            return LanguageValidationResult(is_english=False, detected_language="Language check failed: LLM output format issue")
        except Exception as e:
            print(f"Generic error during LanguageValidatorAgent execution: {type(e).__name__} - {e}")
            return LanguageValidationResult(is_english=True, detected_language=f"Validation Error: An unexpected error occurred ({type(e).__name__})")