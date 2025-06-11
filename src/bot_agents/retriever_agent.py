import asyncio
import logging
from typing import Optional

from src.utils.rag_retriever import DocumentRetriever, RetrievalError

logger = logging.getLogger(__name__)

class RetrieverAgent:
    """
    An asynchronous agent that wraps the synchronous DocumentRetriever utility.
    """
    def __init__(self):
        """
        Initializes the RetrieverAgent.
        
        This constructor initializes the underlying DocumentRetriever.
        It raises a RetrievalError if the retriever fails to initialize,
        for example, if the vector store is not found or is corrupted.
        """
        try:
            self.document_retriever = DocumentRetriever()
            logger.info("DocumentRetriever initialized successfully within RetrieverAgent.")
        except RetrievalError as e:
            logger.error(f"Failed to initialize DocumentRetriever in RetrieverAgent: {e}", exc_info=True)
            # Re-raise the exception to be handled by the application's startup logic.
            raise

    async def retrieve_context(self, query: str) -> Optional[str]:
        """
        Asynchronously retrieves relevant context for a given query.

        This method runs the synchronous `get_relevant_context` method from
        DocumentRetriever in a separate thread to avoid blocking the asyncio event loop.

        Args:
            query: The user's query string.

        Returns:
            A string containing the relevant context, or None if no context
            is found or an error occurs.
        """
        try:
            # Run the synchronous, I/O-bound function in a separate thread
            context = await asyncio.to_thread(
                self.document_retriever.get_relevant_context, query
            )
            return context
        except Exception as e:
            # Catch any exception during the retrieval process
            logger.error(f"An error occurred during context retrieval for query '{query}': {e}", exc_info=True)
            return None 