import logging
from src.bot_agents.models import InteractionLog

logger = logging.getLogger(__name__)

class Logger:
    """
    Utility class for logging user interactions.
    Currently logs to console, but will be extended to write to a database.
    """
    async def log_interaction(self, log_data: InteractionLog):
        """
        Logs the details of a user interaction.

        Args:
            log_data: A Pydantic model containing the structured log data.
        
        TODO: E6 - Replace this with logic to write to a persistent database.
        """
        try:
            # Pydantic's model_dump_json is a good way to get a serializable representation
            log_str = log_data.model_dump_json(indent=2)
            logger.info(f"Interaction logged:\n{log_str}")
        except Exception as e:
            logger.error(f"Failed to serialize or log interaction data: {e}", exc_info=True)

__all__ = ["Logger"] 