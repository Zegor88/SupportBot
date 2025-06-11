from agents import Agent, Runner
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
    
    rules_for_prompt_str = "No rules available."
    if rules:
        rules_for_prompt = [rule_to_dict_for_prompt(rule) for rule in rules]
        rules_for_prompt_str = json.dumps(rules_for_prompt, indent=2, ensure_ascii=False)
    

    prompt = f"""
You are a sophisticated Router Agent. Your task is to process a user's message against a set of rules and produce a final action plan as a JSON object. 
Some rules are 'terminal' (they stop the process), while others are 'behavioral' (they add instructions but allow processing to continue).

You MUST return your decision STRICTLY as a JSON string matching the `RouterDecision` schema.
Do NOT add any explanatory text before or after the JSON string.

Here are the rules, sorted by priority:
{rules_for_prompt_str}

Each rule has a `continue_on_match` flag (it defaults to `false` if not present).
- If `continue_on_match: true`, the rule is behavioral.
- If `continue_on_match: false`, the rule is terminal.

Your task:
1.  Initialize an empty list for `behavioral_prompts`.
2.  Iterate through the rules from top to bottom (by priority).
3.  For each rule that semantically matches the user's message:
    a.  If the rule's `action_params` contain `behavioral_prompts`, add all of them to your collected list.
    b.  If the rule is terminal (`continue_on_match: false`), then this is your final action. Stop iterating. Use this rule's `action`, `rule_id`, and `action_params` for your final output.
4.  **Construct the final JSON output.**
5.  The output must be a single `RouterDecision` JSON.
6.  The `action` and `matched_rule_id` should come from the **first terminal rule** that matched.
7.  The `params` object in your output should contain the `params` of that terminal rule, but **you must also add the `behavioral_prompts` key** containing all the prompts you collected from ALL matched rules (both behavioral and terminal).
8.  If no terminal rule matches, you must use the default action: `action: "default_reply"`, `matched_rule_id: null`, and `params: {{ "system_prompt_key": "general_fallback_prompt" }}`. Even in this case, you must include any `behavioral_prompts` you collected from matched behavioral rules.

Example of a final JSON for a message that matches a behavioral greeting rule and a terminal question rule:
```json
{{
  "action": "reply",
  "matched_rule_id": "some_question_rule",
  "params": {{
    "system_prompt_key": "faq_for_that_question",
    "behavioral_prompts": [
      "The user started with a greeting. Greet them back warmly before answering their question."
    ]
  }}
}}
```

Example of a final JSON if ONLY a behavioral rule matches:
```json
{{
  "action": "default_reply",
  "matched_rule_id": null,
  "params": {{
    "system_prompt_key": "general_fallback_prompt",
    "behavioral_prompts": [
      "The user started with a greeting. Greet them back warmly before answering their question."
    ]
  }}
}}
```
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
