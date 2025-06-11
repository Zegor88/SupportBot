from typing import Optional, Dict, List
import logging
import logging.config
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from utils.rag_retriever import DocumentRetriever
from utils.config import (
    LOGGING_CONFIG, CHAT_MODEL, ResponseGenerationError
)

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

class ResponseGenerator:
    def __init__(self, model_name: str = CHAT_MODEL):
        """
        Инициализация генератора ответов
        
        Args:
            model_name: название модели OpenAI для генерации ответов
            
        Raises:
            ResponseGenerationError: при ошибках инициализации
        """
        try:
            self.llm = ChatOpenAI(model_name=model_name)
            self.retriever = DocumentRetriever()
            
            # Обновленный промпт
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """
                 Act as a highly skilled and empathetic Technical Support Specialist for a Telegram channel. 
Your core responsibility is to analyze the user's question and the provided historical support context 
to formulate an answer that not only matches the style, tone, and manner of the existing support team but
also delivers a solution analogous to how previous specialists have addressed similar issues. 

Crucially, observe if the historical answers sometimes advise users to contact an administrator directly instead of providing a full public solution. 
If such a pattern is present for similar questions, or if the question seems to require private assistance, 
instruct the user to contact one of the following administrators: 
David Mulish | I'll never DM first, John Coltrane (I'll Never DM First), Andrew, or Aleksandr | Everscale. 
In this case, do not attempt to answer the question directly. 
Otherwise, 
Focus on extracting the most relevant information from the Context to construct your response. 
If the Context does not provide a direct or inferable solution, clearly state that you don't know the answer, avoiding any fabrication.
All questions must be in English language, otherwise ask user to rephrase the question in English like "This chat is for English language communication."
If you dont know the answer, kindly ask user to rephrase the question.

Your answers should be concise, professional, and helpful.
 
**Input Placeholders (Do not repeat these in your answer, they are for your guidance):**
История диалога (последние сообщения):
{dialog_history}

Контекст из базы знаний (релевантные документы - исторический контекст поддержки):
{rag_context}
                 
Response Formatting:
- Use clear text without formatting and any Markdown formatting
- Don't use quotes and in your response 
"""
                ),
                ("human", "{question}")
            ])
            logger.info("ResponseGenerator успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации ResponseGenerator: {str(e)}")
            raise ResponseGenerationError(f"Ошибка инициализации: {str(e)}")
    
    def _prepare_full_context(self, rag_documents: List[Dict], dialog_history: List[Dict]) -> tuple[str, str]:
        """
        Подготовка контекста из найденных RAG-документов и истории диалога.
        
        Args:
            rag_documents: список найденных RAG-документов.
            dialog_history: список сообщений из истории диалога.
            
        Returns:
            tuple[str, str]: подготовленный RAG-контекст и история диалога в виде строк.
            
        Raises:
            ResponseGenerationError: при ошибках подготовки контекста
        """
        try:
            # Подготовка RAG-контекста
            rag_context_str = "No relevant information found in the knowledge base."
            if rag_documents:
                rag_documents.sort(key=lambda x: x["score"], reverse=True)
                context_parts = []
                for doc in rag_documents:
                    content = doc["content"]
                    if isinstance(content, str):
                        if "Text:" in content:
                            text = content.split("Text:")[1].split("Reply_To_Message_ID:")[0].strip()
                        else:
                            text = content
                        context_parts.append(f"Document (relevance {doc['score']:.2f}): {text}")
                if context_parts:
                    rag_context_str = "\n\n".join(context_parts)

            # Подготовка истории диалога
            dialog_history_str = "No previous dialog history."
            if dialog_history:
                history_parts = []
                for entry in dialog_history:
                    user_msg = entry.get("message", "")
                    bot_response_obj = entry.get("bot_response")
                    bot_msg = ""
                    if isinstance(bot_response_obj, dict):
                        bot_msg = bot_response_obj.get("text", "")
                    elif isinstance(bot_response_obj, str):
                        bot_msg = bot_response_obj

                    if user_msg:
                        history_parts.append(f"User: {user_msg}")
                    if bot_msg:
                        history_parts.append(f"Assistant: {bot_msg}")
                if history_parts:
                    dialog_history_str = "\n".join(history_parts)
                    
            return rag_context_str, dialog_history_str
        except Exception as e:
            logger.error(f"Ошибка при подготовке контекста: {str(e)}")
            raise ResponseGenerationError(f"Ошибка подготовки контекста: {str(e)}")
    
    async def generate_response(self, question: str, dialog_history: List[Dict]) -> str:
        """
        Генерация ответа на вопрос пользователя с учетом RAG и истории диалога.
        
        Args:
            question: вопрос пользователя.
            dialog_history: история диалога с пользователем.
            
        Returns:
            str: сгенерированный ответ.
            
        Raises:
            ResponseGenerationError: при ошибках генерации ответа
        """
        try:
            # Получаем релевантные документы из RAG
            rag_documents = self.retriever.search_similar_documents(question)
            
            # Подготавливаем полный контекст (RAG + история)
            rag_context, dialog_history_str = self._prepare_full_context(rag_documents, dialog_history)
            
            # Генерируем ответ
            response = await self.llm.ainvoke(
                self.prompt.format_messages(
                    dialog_history=dialog_history_str,
                    rag_context=rag_context,
                    question=question
                )
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            raise ResponseGenerationError(f"Ошибка генерации ответа: {str(e)}")