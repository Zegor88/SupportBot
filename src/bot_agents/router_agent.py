from agents import Agent, Runner
from agents.run_context import RunContextWrapper
from .models import RouterDecision, RouterActionType # Наши модели для RouterAgent
import os
from dotenv import load_dotenv
from typing import List, Any, Dict, Callable
import json
import logging # Добавим для инициализации RulesManager

# Импортируем реальный RulesManager и его модели
from src.rules_manager.manager import RulesManager
# Используем псевдонимы для моделей из rules_manager, чтобы избежать конфликтов и для ясности
from src.rules_manager.models import (
    Rule as RulesManagerRule, 
    AnyCondition as RulesManagerAnyCondition
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set.")

CtxType = object 

def rule_to_dict_for_prompt(rule: RulesManagerRule) -> Dict[str, Any]:
    """
    Конвертирует объект RulesManagerRule в словарь, подходящий для JSON-представления в промпте.
    Использует model_dump() для корректной сериализации, включая вложенные Pydantic модели.
    """
    # Pydantic модели отлично сами себя дампят в словари, включая Union типы для action_params и AnyCondition
    return rule.model_dump(exclude_none=True) 

def dynamic_router_instructions(
    context_wrapper: RunContextWrapper[CtxType], 
    agent: Agent[CtxType] # У agent теперь будет атрибут rules_manager типа RulesManager
) -> str:
    rules_manager: RulesManager = agent.rules_manager 
    rules = rules_manager.get_rules() # Получаем список объектов RulesManagerRule
    
    rules_for_prompt_str = "No rules available."
    if rules:
        rules_for_prompt = [rule_to_dict_for_prompt(rule) for rule in rules]
        rules_for_prompt_str = json.dumps(rules_for_prompt, indent=2)
    
    # hamster_combat_rule_id = "HAMSTER_COMBAT_SUPPORT_REDIRECT" # Больше не нужен здесь

    prompt = f"""
You are a Router Agent. Your primary goal is to analyze the user's message and decide the next action based on a predefined set of rules.
You MUST return your decision STRICTLY as a JSON string matching the RouterDecision schema (fields: `action`, `matched_rule_id`, `params`). Do NOT add any explanatory text before or after the JSON string.

The user's message will be provided as the last message in the input history.

Here are the available rules, sorted by priority. Each rule has `rule_id`, `conditions`, `action`, and `action_params`.

Details on `conditions` (list of condition objects, field `type` inside each object):
- `keyword_match`:
  - `keywords`: list of strings.
  - `match_type` (optional, defaults to "any" if not present): "any" or "all".
  - `case_sensitive` (optional, defaults to false if not present): boolean.
- `regex_match`:
  - `pattern`: regex string.
  - `case_sensitive` (optional, usually handled by regex pattern flags): boolean.

Available Rules:
{rules_for_prompt_str}

Your task:
1.  Carefully analyze the user's most recent message to understand its **primary intent and context**.
2.  Evaluate the rules in the order of their appearance (which is by priority).
3.  For each rule:
    a.  Check if ALL its literal `conditions` (keywords, regex) are met by the user's message.
    b.  If the literal conditions are met, then **critically assess if the primary intent of the user's message aligns with the implied purpose of this rule.** For example, if a rule is designed to redirect specific support questions (e.g., for 'Product X' or a topic like 'Hamster Combat'), but the user only mentions 'Product X' or 'Hamster Combat' in a passing, comparative, or general informational context (e.g., "Is Hamster Combat similar to Product Y?"), then the rule should NOT be considered a match, even if keywords are present. The rule should only apply if the user is *actually seeking what the rule is designed to handle based on its conditions and action*.
    c.  A rule is considered a true match only if **both step 3a AND step 3b are true.**
4.  Select the FIRST rule that is a true match according to the criteria above.
5.  If a rule matches, use its `rule_id`, `action`, and `action_params` for your JSON response.
6.  If NO rule truly matches (either literal conditions are not met, or the primary intent does not align with the rule's purpose), return a default decision JSON: `{{\"action\": \"default_reply\", \"matched_rule_id\": null, \"params\": {{\"system_prompt_key\": \"general_fallback_prompt\"}}}}`.

Output ONLY the RouterDecision JSON string.

Example (GREETING rule):
```json
{{
  "action": "reply",
  "matched_rule_id": "GREETING",
  "params": {{
    "response_text": "Hello there! This is your Router Agent. How can I assist you?"
  }}
}}
```
Example (Rule for specific support like HAMSTER_COMBAT_SUPPORT_REDIRECT, if user asks for direct support for Hamster Combat):
```json
{{
  "action": "reply",
  "matched_rule_id": "HAMSTER_COMBAT_SUPPORT_REDIRECT",
  "params": {{
    "response_text": "This chat doesn't provide support for Hamster Boost. Please contact @Hamster_Boost_Support_bot for assistance with your query."
  }}
}}
"""
    # print(f"\n[dynamic_router_instructions] Generated prompt:\n{prompt}\n") # Закомментировано, т.к. очень длинный
    return prompt

class RouterAgent(Agent[CtxType]):
    rules_manager: RulesManager # Используем реальный RulesManager

    def __init__(self, 
                 rules_manager: RulesManager, # Принимаем реальный RulesManager
                 name: str = "RouterAgent",
                 model: str = "gpt-4o-mini", 
                 **kwargs):
        
        self.rules_manager = rules_manager 

        super().__init__(
            name=name, 
            instructions=dynamic_router_instructions, 
            model=model,
            **kwargs
        )
        print(f"[RouterAgent] Initialized with REAL RulesManager. Expecting JSON string output.")

async def main_test_real_rules_manager_and_hamster():
    print("\n--- RouterAgent: Test with REAL RulesManager and Hamster Combat Logic ---")
    
    rules_file_path = "rules.yaml" 
    try:
        # Инициализируем реальный RulesManager с logging
        # Настраиваем базовый уровень логирования для вывода INFO от RulesManager
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # Можно установить logging.DEBUG для более детального вывода от RulesManager, если необходимо
        # logging.getLogger("src.rules_manager.manager").setLevel(logging.DEBUG)
        
        rules_manager = RulesManager(rules_file_path=rules_file_path)
        print(f"Successfully initialized RulesManager with {len(rules_manager.get_rules())} rules.")
    except Exception as e:
        print(f"ERROR: Could not initialize RulesManager with '{rules_file_path}': {e}")
        return

    router_agent = RouterAgent(rules_manager=rules_manager)

    test_messages = {
        "greeting": "Hey there",
        # Hamster Combat tests
        "hamster_direct_support_card": "How do I upgrade my card in Hamster Combat?",
        "hamster_direct_support_tokens": "My HMSTR tokens are not showing, help!",
        "hamster_direct_support_kombat": "hamster kombat not working",
        "hamster_general_comparison": "Is Hamster Combat similar to the Everscale project?",
        "hamster_general_opinion": "What do you think about the latest Hamster Combat update, is it good for its tokenomics?",
        "hamster_mention_unrelated_support": "I need help with my account, and by the way, Hamster Combat is a fun game.",
        # Other tests
        "balance_inquiry": "check my balance",
        "farewell": "ok thanks bye",
        "unknown_query": "What's the weather like today?"
    }

    for test_name, user_message in test_messages.items():
        print(f"\n--- Testing: {test_name} ---")
        print(f"User message: '{user_message}'")

        run_result = await Runner.run(router_agent, user_message)
        final_output_str = run_result.final_output
        
        print(f"RouterAgent Raw Output (string):\n{final_output_str}")

        if isinstance(final_output_str, str):
            try:
                parsed_json_str = final_output_str.strip()
                if parsed_json_str.startswith("```json"):
                    parsed_json_str = parsed_json_str[7:]
                if parsed_json_str.endswith("```"):
                    parsed_json_str = parsed_json_str[:-3]
                parsed_json_str = parsed_json_str.strip()

                final_decision = RouterDecision.model_validate_json(parsed_json_str)
                print(f"Parsed RouterAgent Decision:")
                print(f"  Action: {final_decision.action}")
                print(f"  Matched Rule ID: {final_decision.matched_rule_id}")
                print(f"  Params: {final_decision.params}")
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON: {e}")
                print(f"Problematic string: >>>{final_output_str}<<<")
            except Exception as e: 
                print(f"ERROR: Failed to validate RouterDecision: {e}")
                print(f"Problematic string: >>>{final_output_str}<<<")
        else:
            print(f"ERROR: Expected string output from agent, but got {type(final_output_str)}")
        print("------------------------")

    print("\n--- End of RouterAgent: REAL RulesManager Test ---")

if __name__ == "__main__":
    import asyncio
    # Убедитесь, что poetry установила зависимости из src.rules_manager (если они еще не установлены)
    # и что rules.yaml находится в правильном месте (корень проекта по умолчанию для теста)
    asyncio.run(main_test_real_rules_manager_and_hamster()) 