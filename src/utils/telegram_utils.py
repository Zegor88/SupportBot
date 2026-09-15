from telegram import Bot
from telegram.error import TelegramError
import logging

logger = logging.getLogger(__name__)

class MessageForwarder:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def forward_message(
        self,
        original_message_id: int,
        from_chat_id: int, # ID чата, из которого нужно переслать
        target_chat_id: str  # ID чата, в который нужно переслать (может быть строкой для @username или числом)
    ) -> bool:
        """
        Пересылает сообщение в указанный чат.

        Args:
            original_message_id: ID оригинального сообщения для пересылки.
            from_chat_id: ID чата, из которого сообщение будет переслано.
            target_chat_id: ID чата назначения (числовой ID или @username).

        Returns:
            bool: True, если пересылка успешна, False в противном случае.
        """
        logger.info(f"Attempting to forward message_id {original_message_id} from chat_id {from_chat_id} to target_chat_id {target_chat_id}")
        try:
            # target_chat_id может быть как числом, так и строкой (например, @channelname)
            # from_chat_id должен быть числом
            # message_id должен быть числом
            
            # Убедимся, что target_chat_id может быть как int так и str
            # А from_chat_id и message_id являются int
            
            _target_chat_id = target_chat_id 
            if isinstance(target_chat_id, str) and target_chat_id.isdigit():
                _target_chat_id = int(target_chat_id)

            await self.bot.forward_message(
                chat_id=_target_chat_id,
                from_chat_id=int(from_chat_id),
                message_id=int(original_message_id)
            )
            logger.info(f"Successfully forwarded message_id {original_message_id} to {target_chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to forward message_id {original_message_id} to {target_chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while forwarding message_id {original_message_id} to {target_chat_id}: {type(e).__name__} - {e}")
            return False 