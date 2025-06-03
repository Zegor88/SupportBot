from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel

RouterActionType = Literal["reply", "forward", "drop", "default_reply"]

class RouterDecision(BaseModel):
    action: RouterActionType
    matched_rule_id: Optional[str] = None
    params: Dict[str, Any] = {} 

class ReplyHandoffData(BaseModel):
    user_message: str
    history: list # В ТЗ указано list, но лучше конкретизировать List[Dict[str, str]] или создать отдельную модель для сообщения в истории
    system_prompt_key: Optional[str] = None
    response_text: Optional[str] = None 