# src/rules_manager/models.py
# This file contains the models for the rules.

from typing import List, Literal, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator, model_validator, ValidationError
from pydantic import ConfigDict

# Enums
ActionType = Literal["reply", "forward", "drop"]
ConditionType = Literal["keyword_match", "regex_match", "description_match"]
KeywordMatchType = Literal["any", "all"]

# --- Condition Models ---
class BaseCondition(BaseModel):
    type: ConditionType

class KeywordMatchCondition(BaseCondition):
    type: Literal["keyword_match"] = "keyword_match"
    keywords: List[str] = Field(..., min_length=1)
    match_type: KeywordMatchType = "any"
    case_sensitive: bool = False

class RegexMatchCondition(BaseCondition):
    type: Literal["regex_match"] = "regex_match"
    pattern: str

class DescriptionMatchCondition(BaseCondition):
    type: Literal["description_match"] = "description_match"
    description: str = Field(..., min_length=1)

# Union of all condition types using discriminated union
AnyCondition = Union[KeywordMatchCondition, RegexMatchCondition, DescriptionMatchCondition]

# --- Action Parameter Models ---
class BaseActionParams(BaseModel):
    pass

class ReplyActionParams(BaseActionParams):
    response_text: Optional[str] = None
    system_prompt_key: Optional[str] = None
    behavioral_prompts: Optional[List[str]] = None

    @model_validator(mode='after')
    def check_reply_params(self) -> 'ReplyActionParams':
        # For a 'reply' action, at least one of the possible parameters must be provided.
        if not self.response_text and not self.system_prompt_key and not self.behavioral_prompts:
            raise ValueError(
                'For a reply action, at least one of response_text, system_prompt_key, or behavioral_prompts must be provided.'
            )
        return self

class ForwardActionParams(BaseActionParams):
    destination_chat_id: str

class DropActionParams(BaseActionParams):
    # No specific params, can be an empty dict in YAML
    pass

# --- Rule Model ---
class Rule(BaseModel):
    """
    Represents a single rule in the rules.yaml file.
    """
    rule_id: str = Field(..., min_length=1)
    priority: int
    is_behavioral: bool = Field(default=False, alias='is_behavioral')
    conditions: List[AnyCondition] = Field(..., min_length=1)
    action: ActionType
    action_params: Union[ReplyActionParams, ForwardActionParams, DropActionParams]
    instruction: Optional[str] = None # For system prompts

    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True,
    )

    @model_validator(mode='before')
    @classmethod
    def _init_action_params(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        action_type = data.get('action')
        params_data = data.get('action_params')

        if action_type is None:
            return data

        if params_data is None:
            params_data = {}
            data['action_params'] = params_data

        if not isinstance(params_data, dict):
            raise ValueError(
                f"action_params must be a dictionary for action '{action_type}', "
                f"got {type(params_data).__name__}."
            )

        try:
            if action_type == 'reply':
                data['action_params'] = ReplyActionParams(**params_data)
            elif action_type == 'forward':
                data['action_params'] = ForwardActionParams(**params_data)
            elif action_type == 'drop':
                data['action_params'] = DropActionParams(**params_data)
        except ValidationError:
            raise # Валидационная ошибка из Pydantic при создании *ActionParams, даем ей всплыть
        except ValueError as e:
            # Оборачиваем другие ValueError (например, из нашего кастомного валидатора) в ValidationError
            # чтобы они были консистентно обработаны Pydantic и нашим RulesManager
            # Это должно помочь тесту поймать RulesFileError
            raise ValidationError.from_exception_data(
                title=cls.__name__ + ".action_params", 
                line_errors=[{'type': 'value_error', 'loc': ('action_params', action_type), 'msg': str(e), 'input': params_data}]
            )

        return data

# --- Config Model (for the entire rules.yaml file) ---
class RulesConfig(BaseModel):
    rules: List[Rule]

class RulesFile(BaseModel):
    # This class is not provided in the original file or the code block
    # It's assumed to exist as it's called in the original file
    pass 