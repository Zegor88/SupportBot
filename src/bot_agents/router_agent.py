from agents import Agent
from agents.run_context import RunContextWrapper
from .models import RouterDecision, RouterActionType # Наши модели для RouterAgent
import os
from dotenv import load_dotenv
from typing import List, Any, Dict, Callable
import json
import logging
from src.rules_manager.manager import RulesManager
from src.rules_manager.models import (
    Rule as RulesManagerRule, 
    AnyCondition as RulesManagerAnyCondition
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set.")

# Тип контекста для RouterAgent
CtxType = object 

def rule_to_dict_for_prompt(rule: RulesManagerRule) -> Dict[str, Any]:
    """
    Конвертирует объект RulesManagerRule в словарь, подходящий для JSON-представления в промпте.
    Использует model_dump() для корректной сериализации, включая вложенные Pydantic модели.
    """
    return rule.model_dump(exclude_none=True) 

def dynamic_router_instructions(
    context_wrapper: RunContextWrapper[CtxType], 
    agent: Agent[CtxType]
) -> str:
    rules_manager: RulesManager = agent.rules_manager 
    rules = rules_manager.get_rules() # Получаем список объектов RulesManagerRule

    # Извлекаем историю из контекста
    history = "No history available."
    if context_wrapper.context and isinstance(context_wrapper.context, dict):
        history = context_wrapper.context.get("history", "No history available.")
    if not history:
        history = "No history available."
    
    rules_for_prompt_str = "No rules available."
    if rules:
        rules_for_prompt = [rule_to_dict_for_prompt(rule) for rule in rules]
        rules_for_prompt_str = json.dumps(rules_for_prompt, indent=2, ensure_ascii=False)
    

    prompt = f"""
You are a sophisticated Router Agent. Your task is to process a user's message against a set of rules and produce a final action plan as a JSON object. 
You MUST return your decision STRICTLY as a JSON string matching the `RouterDecision` schema.
Do NOT add any explanatory text before or after the JSON string.

Here is the conversation history with the user. Use it for context to better understand the user's intent.
<history>
{history}
</history>

Here are the rules, sorted by priority:
{rules_for_prompt_str}

IMPORTANT: There are two types of rules in the system:
1. Behavioral Rules (`is_behavioral: true`): These rules add context and instructions but don't stop processing.
2. Terminal Rules (`is_behavioral: false`): These rules determine the final action and stop processing.

Your task is to:
1. Collect all matching behavioral rules (their IDs and prompts)
2. Find the first matching terminal rule (if any)
3. Generate a response that includes:
   - The action from the terminal rule (or default if none found)
   - The ID of the terminal rule (or null if none found)
   - The IDs of all matching behavioral rules
   - All collected behavioral prompts

Process:

1.  **Initialization**:
    *   Start with `final_decision` as `null`.
    *   Start with an empty list called `collected_behavioral_prompts`.
    *   Start with an empty list called `collected_behavioral_rule_ids`.

2.  **Rule Iteration**:
    *   Go through the rules one by one, in the provided order (by priority).
    *   For each rule that semantically matches the user's latest message (considering the history):
        a.  **Check for Behavioral Rule**: If `is_behavioral: true`:
            *   Add the rule's `rule_id` to `collected_behavioral_rule_ids`.
            *   If the rule has `behavioral_prompts`, add them to `collected_behavioral_prompts`.
            *   **Continue** to the next rule.
        b.  **Check for Terminal Rule**: If `is_behavioral: false`:
            *   If your `final_decision` is still `null`, this rule becomes your `final_decision`. Store its `action`, `rule_id`, and `action_params`.
            *   If the rule has `behavioral_prompts`, add them to `collected_behavioral_prompts`.
            *   **You must stop iterating now.**

3.  **Final Decision Assembly**:
    *   **If you found a terminal rule** (your `final_decision` is not `null`):
        *   Your final JSON will use the `action` and `matched_rule_id` from your `final_decision`.
        *   The `params` object will be from the `final_decision`.
    *   **If you did NOT find any terminal rule** (`final_decision` is still `null`):
        *   You must use the default action. Your JSON will have `action: "default_reply"`, `matched_rule_id: null`, and `params`: {{{{ "system_prompt_key": "default_prompt" }}}}.
    *   **In all cases**:
        *   The final `params` object in the JSON must include a `behavioral_prompts` key with all `collected_behavioral_prompts`.
        *   The top-level JSON must include a `behavioral_rule_ids` key with all `collected_behavioral_rule_ids`.

Example of a final JSON if ONLY a behavioral rule matches:
```json
{{
  "action": "default_reply",
  "matched_rule_id": null,
  "behavioral_rule_ids": ["GREETING"],
  "params": {{
    "system_prompt_key": "default_prompt",
    "behavioral_prompts": [
      "The user started with a greeting. Greet them back warmly before answering their question."
    ]
  }}
}}
```

Example of a final JSON if both behavioral and terminal rules match:
```json
{{
  "action": "reply",
  "matched_rule_id": "FAREWELL",
  "behavioral_rule_ids": ["GREETING"],
  "params": {{
    "response_text": "Goodbye! Have a great day!",
    "behavioral_prompts": [
      "The user started with a greeting. Greet them back warmly before saying goodbye."
    ]
  }}
}}
"""
    return prompt

class RouterAgent(Agent[CtxType]):
    rules_manager: RulesManager

    def __init__(self, 
                 rules_manager: RulesManager,
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