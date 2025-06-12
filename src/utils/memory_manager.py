from typing import Dict, List, Optional
from datetime import datetime
from .config import NUM_STORED_MESSAGES

class MemoryManager:
    def __init__(self):
        self._memory: Dict[int, List[dict]] = {}
        self.max_history_length = NUM_STORED_MESSAGES  # Хранить последние 10 сообщений для каждого пользователя

    def add_message(self, user_id: int, role: str, text: str) -> None:
        """Добавляет новое сообщение в историю диалога."""
        if user_id not in self._memory:
            self._memory[user_id] = []
        
        message = {
            'role': role,
            'text': text,
            'timestamp': datetime.now().isoformat()
        }
        
        self._memory[user_id].append(message)
        
        # Ограничиваем историю последними N сообщениями
        if len(self._memory[user_id]) > self.max_history_length:
            self._memory[user_id] = self._memory[user_id][-self.max_history_length:]

    def get_history(self, user_id: int) -> List[dict]:
        """Возвращает историю диалога для пользователя."""
        return self._memory.get(user_id, [])

    def get_history_as_text(self, user_id: int) -> str:
        """Возвращает историю диалога в текстовом формате."""
        history = self.get_history(user_id)
        if not history:
            return ""
        
        formatted_messages = []
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            formatted_messages.append(f"{role}: {msg['text']}")
        
        return "\n".join(formatted_messages)

    def clear_history(self, user_id: int) -> None:
        """Очищает историю диалога для пользователя."""
        if user_id in self._memory:
            del self._memory[user_id] 