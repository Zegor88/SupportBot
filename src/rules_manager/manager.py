# src/rules_manager/manager.py
# This file contains the RulesManager class, which is responsible for loading and managing the rules.

import yaml
import logging
from typing import List, Optional
from pydantic import ValidationError

from .models import Rule, RulesConfig # Используем относительный импорт

logger = logging.getLogger(__name__)

class RulesFileError(Exception):
    """Custom exception for errors related to rules file processing."""
    pass

class RulesManager:
    def __init__(self, rules_file_path: str):
        self.rules_file_path = rules_file_path
        self._rules: List[Rule] = []
        self.load_rules()
        logger.info(f"RulesManager initialized successfully. Loaded {len(self._rules)} rules from {self.rules_file_path}")

    def load_rules(self) -> List[Rule]:
        logger.debug(f"Attempting to load rules from {self.rules_file_path}")
        try:
            with open(self.rules_file_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            if not raw_config or 'rules' not in raw_config:
                 logger.warning(f"Rules file {self.rules_file_path} is empty or does not contain a 'rules' key. Loading empty rule set.")
                 self._rules = []
                 return self._rules

            config = RulesConfig(**raw_config)
            
            self._rules = sorted(config.rules, key=lambda rule: rule.priority)
            
            logger.info(f"Successfully loaded and validated {len(self._rules)} rules from {self.rules_file_path}.")
            return self._rules

        except FileNotFoundError:
            logger.error(f"Rules file not found: {self.rules_file_path}")
            raise RulesFileError(f"Rules file not found: {self.rules_file_path}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML from {self.rules_file_path}: {e}")
            raise RulesFileError(f"Error parsing YAML from {self.rules_file_path}: {e}")
        except ValidationError as e:
            logger.error(f"Validation error for rules in {self.rules_file_path}: {e}")
            raise RulesFileError(f"Validation error for rules in {self.rules_file_path}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading rules from {self.rules_file_path}: {e}")
            raise RulesFileError(f"An unexpected error occurred: {e}")

    def get_rules(self) -> List[Rule]:
        return self._rules

    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """Находит правило по его ID."""
        if not rule_id:
            return None
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def reload_rules(self) -> bool:
        logger.info(f"Attempting to reload rules from {self.rules_file_path}")
        current_rules_backup = list(self._rules)
        try:
            self.load_rules()
            logger.info(f"Rules reloaded successfully. {len(self._rules)} rules are now active.")
            return True
        except RulesFileError as e:
            logger.error(f"Failed to reload rules: {e}. Restoring previous rule set ({len(current_rules_backup)} rules).")
            self._rules = current_rules_backup
            return False
        except Exception as e:
            logger.error(f"An unexpected critical error occurred during rule reload: {e}. Restoring previous rule set ({len(current_rules_backup)} rules).")
            self._rules = current_rules_backup
            return False 