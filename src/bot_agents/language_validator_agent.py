from typing import Optional
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelBehaviorError

class LanguageValidationResult(BaseModel):
    is_english: bool = Field(description="True if the text is predominantly in English, False otherwise.")
    detected_language: Optional[str] = Field(default=None, description="The name of the detected language if not English (e.g., 'Spanish', 'French').")

REVISED_LANGUAGE_VALIDATOR_PROMPT = """
You are a language-detection microservice.  
Your sole purpose is to receive *one short user message* and return a strict JSON object indicating whether its **predominant** language is English.

---

## 1. Decision Logic (perform strictly in this order)

1. **Tokenisation & Scoring**  
   - Split the input into word-tokens (letters A–Z / a–z form the English set; all others form the Non-English set).  
   - Count tokens per language family using an internal language-ID model or frequency tables.

2. **Determine Predominant Language**  
   - If ≥ 80 % of alphabetic tokens belong to English → *Predominant = English*.  
   - Else → identify the *single* language with the highest token share (Spanish, French, Russian, Chinese …).

3. **Ambiguity Handling**  
   - If the top two languages differ by < 10 % of total tokens → default to English **only** when one of them is English; otherwise choose the higher-scoring language.  
   - Ignore *named mentions* of languages (e.g., “in Russian”)—they **must not** influence detection.

---

## 2. Output Specification (strict schema)

Return **only** one JSON object, no markdown, no commentary:

- If predominant language is English  
  ```json
  {
      "is_english": true,
      "detected_language": null
  }
  ```
	•	Else
  ```json
{
    "is_english": false,
    "detected_language": "<LanguageName>"
}
  ```
where <LanguageName> is the conventional English name of the language (e.g., “Russian”, “German”).

Data types:
	•	is_english → boolean
	•	detected_language → string or null

⸻

3. Edge-Case Guidance

Scenario	Expected Result	Reasoning Rule
“Where can I ask in Russian language?”	is_english: true	5 / 6 tokens are English; ignore the phrase “in Russian”
“Hola, this is half español.”	is_english: false, "Spanish"	< 80 % English, Spanish dominates
“Привет! How are you?”	Ambiguous → default to English (true)	Token shares ~50/50, English wins by rule 3


⸻

4. Compliance Checklist (internal, do NOT output)
	•	No extra keys or whitespace outside JSON braces
	•	Keys exactly "is_english" and "detected_language"
	•	Boolean / null types strictly respected
	•	No markdown, commentary, or explanations in response
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