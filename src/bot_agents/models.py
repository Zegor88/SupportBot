from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel

RouterActionType = Literal["reply", "forward", "drop", "default_reply"]

class RouterDecision(BaseModel):
    action: RouterActionType
    matched_rule_id: Optional[str] = None
    params: Dict[str, Any] = {} 