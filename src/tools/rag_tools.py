from agents import function_tool
from src.utils.rag_retriever import DocumentRetriever, RetrievalError
import logging

logger = logging.getLogger(__name__)

# Инициализируем DocumentRetriever один раз при загрузке модуля.
# Это более эффективно, чем создавать новый экземпляр при каждом вызове.
try:
    document_retriever = DocumentRetriever()
    logger.info("DocumentRetriever initialized successfully for RAG tool.")
except RetrievalError as e:
    logger.error(f"Failed to initialize DocumentRetriever for RAG tool: {e}", exc_info=True)
    document_retriever = None

@function_tool
def retrieve_rag_context(query: str) -> str:
    """
    Retrieves relevant context from the knowledge base (RAG) to answer a user's query.
    Use this tool when you need additional information to provide a comprehensive and accurate answer.
    
    Args:
        query: The user's query or a question that requires information from the knowledge base.
        
    Returns:
        A string containing the relevant context found, or a message indicating that no information was found or an error occurred.
    """
    logger.info(f"RAG Tool triggered with query: '{query}'")
    
    if document_retriever is None:
        logger.error("DocumentRetriever is not available, cannot retrieve context.")
        return "Error: The knowledge base is currently unavailable."
        
    try:
        context = document_retriever.get_relevant_context(query)
        if not context:
            logger.warning(f"No context found for query: '{query}'")
            return "No specific information found for this query in the knowledge base."
        
        logger.info(f"Successfully retrieved context for query: '{query}'")
        # Добавляем подробное логирование извлеченного контекста
        logger.info(f"--- RETRIEVED CONTEXT START ---\n{context}\n--- RETRIEVED CONTEXT END ---")
        
        return context
    except Exception as e:
        logger.error(f"An error occurred during context retrieval for query '{query}': {e}", exc_info=True)
        return "An error occurred while trying to access the knowledge base."

__all__ = ["retrieve_rag_context"] 