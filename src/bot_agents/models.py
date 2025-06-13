from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

# Тип действия, которое должен вернуть RouterAgent
RouterActionType = Literal["reply", "forward", "drop", "default_reply"]

# Модель для параметров, возвращаемых RouterAgent
class RouterDecisionParams(BaseModel):
    system_prompt_key: Optional[str] = None
    response_text: Optional[str] = None
    destination_chat_id: Optional[str] = None
    behavioral_prompts: Optional[List[str]] = None

# Основная модель решения, которую должен вернуть RouterAgent в виде JSON
class RouterDecision(BaseModel):
    action: RouterActionType
    matched_rule_id: Optional[str] # ID терминального правила, которое было выбрано
    behavioral_rule_ids: Optional[List[str]] = None # IDs сработавших поведенческих правил
    params: RouterDecisionParams

# Модель для данных, передаваемых в AnswerAgent
class ReplyHandoffData(BaseModel):
    """
    Data model for handoff to the AnswerAgent.
    """
    user_message: str
    system_prompt_key: str
    history: Optional[str] = None
    instruction: Optional[str] = None
    behavioral_prompts: Optional[List[str]] = None

class InteractionLog(BaseModel):
    """
    Data model for logging interactions.
    Follows FR-13.
    """
    timestamp: datetime
    user_id: int
    matched_rule_id: Optional[str]
    action: str
    question: str
    answer: str
    final_prompt: str
    rag_contexts: Optional[List[str]] = None