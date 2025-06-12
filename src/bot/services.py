# src/bot/services.py
# Этот файл отвечает за инициализацию и управление всеми внешними сервисами и агентами,
# которые использует бот.

import logging
from .config import logger

from src.bot_agents import (
    LanguageValidatorAgentWrapper,
    RouterAgent,
    answer_agent,
    Logger as BotLogger,
)
from src.rules_manager.manager import RulesManager, RulesFileError
from agents import Runner

class BotServices:
    """
    Класс-контейнер для всех сервисов и агентов бота.
    Инициализирует все компоненты при создании экземпляра.
    """
    def __init__(self, rules_file_path="rules.yaml"):
        self.rules_manager = self._initialize_rules_manager(rules_file_path)
        self.router_agent = self._initialize_router_agent(self.rules_manager)
        self.language_validator = LanguageValidatorAgentWrapper()
        self.logger_agent = BotLogger()
        self.runner = Runner  # Класс Runner для запуска агентов

    def _initialize_rules_manager(self, file_path: str) -> RulesManager | None:
        try:
            manager = RulesManager(rules_file_path=file_path)
            logger.info(f"RulesManager initialized successfully with {len(manager.get_rules())} rules.")
            return manager
        except (RulesFileError, Exception) as e:
            logger.error(f"CRITICAL: Failed to initialize RulesManager: {e}", exc_info=True)
            return None

    def _initialize_router_agent(self, manager: RulesManager | None) -> RouterAgent | None:
        if not manager:
            logger.error("Cannot initialize RouterAgent because RulesManager failed to initialize.")
            return None
        try:
            agent = RouterAgent(rules_manager=manager)
            logger.info("RouterAgent initialized successfully.")
            return agent
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize RouterAgent: {e}", exc_info=True)
            return None

# Создаем единый экземпляр-синглтон, который будет использоваться во всем приложении
bot_services = BotServices() 