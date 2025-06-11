import yaml
import os
from typing import Dict
import logging

# Получаем тот же логгер, что и в основном приложении, для консистентности
logger = logging.getLogger("src.bot.config")

class PromptManager:
    _instance = None
    _prompts: Dict[str, str] = {}
    _default_prompt_key = "default_prompt"
    _prompts_file_path = "prompts.yaml"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _load_prompts(self):
        try:
            if not os.path.exists(self._prompts_file_path):
                logger.error(f"Prompts file not found at '{self._prompts_file_path}'. Cannot load prompts.")
                self._prompts = {}
                return

            with open(self._prompts_file_path, 'r', encoding='utf-8') as f:
                loaded_prompts = yaml.safe_load(f)
                if not isinstance(loaded_prompts, dict):
                    logger.error(f"'{self._prompts_file_path}' is not a valid dictionary. No prompts loaded.")
                    return
                self._prompts = loaded_prompts
                if self._default_prompt_key not in self._prompts:
                    logger.error(f"'{self._default_prompt_key}' is missing from '{self._prompts_file_path}'. Fallback mechanism will be impaired.")
                logger.info(f"Successfully loaded {len(self._prompts)} prompts from '{self._prompts_file_path}'.")

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file '{self._prompts_file_path}': {e}")
            self._prompts = {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading prompts: {e}", exc_info=True)
            self._prompts = {}

    def get_prompt(self, key: str) -> str:
        """
        Retrieves a prompt template by its key.
        Returns a default prompt if the key is not found.
        """
        prompt = self._prompts.get(key)
        if prompt is None:
            logger.warning(f"Prompt key '{key}' not found. Falling back to default prompt.")
            return self._prompts.get(self._default_prompt_key, "You are a helpful assistant.")
        
        return prompt

# Экспортируем синглтон-экземпляр для удобного использования во всем приложении
prompt_manager = PromptManager() 