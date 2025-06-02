import pytest
import yaml
import os
from typing import List, Dict, Any

from src.rules_manager.manager import RulesManager, RulesFileError
from src.rules_manager.models import Rule, KeywordMatchCondition, RegexMatchCondition, ReplyActionParams, ForwardActionParams, DropActionParams

# Фикстура для создания временного файла rules.yaml
@pytest.fixture
def create_rules_file(tmp_path):
    def _create_rules_file(content: Dict[str, Any], filename: str = "rules.yaml"):
        file_path = tmp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(content, f)
        return str(file_path)
    return _create_rules_file

# Пример валидного контента для rules.yaml
VALID_RULES_CONTENT = {
    "rules": [
        {
            "rule_id": "test_rule_1",
            "priority": 10,
            "conditions": [{"type": "keyword_match", "keywords": ["hello"], "match_type": "any"}],
            "action": "reply",
            "action_params": {"response_text": "Hello there!"}
        },
        {
            "rule_id": "test_rule_2",
            "priority": 1,
            "conditions": [{"type": "regex_match", "pattern": ".*help.*"}],
            "action": "forward",
            "action_params": {"destination_chat_id": "@support_channel"}
        },
    ]
}

class TestRulesManager:
    def test_successful_initialization_and_loading(self, create_rules_file):
        rules_file_path = create_rules_file(VALID_RULES_CONTENT)
        manager = RulesManager(rules_file_path)
        
        assert len(manager.get_rules()) == 2
        assert manager.get_rules()[0].rule_id == "test_rule_2" # Проверка сортировки по priority
        assert manager.get_rules()[1].rule_id == "test_rule_1"
        
        rule1 = manager.get_rules()[1]
        assert isinstance(rule1.conditions[0], KeywordMatchCondition)
        assert rule1.conditions[0].keywords == ["hello"]
        assert isinstance(rule1.action_params, ReplyActionParams)
        assert rule1.action_params.response_text == "Hello there!"

        rule2 = manager.get_rules()[0]
        assert isinstance(rule2.conditions[0], RegexMatchCondition)
        assert rule2.conditions[0].pattern == ".*help.*"
        assert isinstance(rule2.action_params, ForwardActionParams)
        assert rule2.action_params.destination_chat_id == "@support_channel"

    def test_initialization_file_not_found(self):
        with pytest.raises(RulesFileError, match="Rules file not found: non_existent_rules.yaml"):
            RulesManager("non_existent_rules.yaml") # Менеджер должен выбросить ошибку, если не может загрузить

    def test_initialization_with_empty_rules_list(self, create_rules_file):
        empty_rules = {"rules": []}
        rules_file_path = create_rules_file(empty_rules)
        manager = RulesManager(rules_file_path)
        assert len(manager.get_rules()) == 0
    
    def test_initialization_with_empty_file(self, create_rules_file):
        # Файл существует, но он пустой
        rules_file_path = create_rules_file({}) # Пустой словарь означает пустой YAML
        manager = RulesManager(rules_file_path)
        assert len(manager.get_rules()) == 0
        # Логгер должен был выдать warning, здесь мы это не проверяем напрямую, но поведение корректно

    def test_initialization_with_no_rules_key(self, create_rules_file):
        # Файл существует, но нет ключа 'rules'
        content_no_rules_key = {"not_rules": []}
        rules_file_path = create_rules_file(content_no_rules_key)
        manager = RulesManager(rules_file_path)
        assert len(manager.get_rules()) == 0
        # Логгер должен был выдать warning

    def test_invalid_yaml_syntax(self, tmp_path):
        invalid_yaml_content = "rules: - rule_id: test\n  priority: 10\n conditions: [{type: keyword_match, keywords: [test]}]" # Нарушен отступ
        rules_file_path = tmp_path / "invalid_syntax.yaml"
        with open(rules_file_path, 'w', encoding='utf-8') as f:
            f.write(invalid_yaml_content)
        
        with pytest.raises(RulesFileError, match="Error parsing YAML"):
            RulesManager(str(rules_file_path))

    def test_validation_error_missing_rule_id(self, create_rules_file):
        invalid_content = {
            "rules": [{
                # "rule_id": "missing", 
                "priority": 1, 
                "conditions": [{"type": "keyword_match", "keywords": ["test"]}] , 
                "action": "drop", 
                "action_params": {}
            }]
        }
        rules_file_path = create_rules_file(invalid_content)
        with pytest.raises(RulesFileError, match="Validation error for rules"):
            RulesManager(rules_file_path)

    def test_validation_error_invalid_action_type(self, create_rules_file):
        invalid_content = {
            "rules": [{
                "rule_id": "invalid_action", "priority": 1, 
                "conditions": [{"type": "keyword_match", "keywords": ["test"]}] , 
                "action": "invalid_action_type", # Неверный тип действия
                "action_params": {}
            }]
        }
        rules_file_path = create_rules_file(invalid_content)
        with pytest.raises(RulesFileError, match="Validation error for rules"):
            RulesManager(rules_file_path)
            
    def test_validation_error_reply_missing_params(self, create_rules_file):
        invalid_content = {
            "rules": [{
                "rule_id": "reply_no_params", "priority": 1,
                "conditions": [{"type": "keyword_match", "keywords": ["test"]}] ,
                "action": "reply",
                "action_params": {} # Нет ни response_text, ни system_prompt_key
            }]
        }
        rules_file_path = create_rules_file(invalid_content)
        with pytest.raises(RulesFileError, match="Validation error for rules"):
             RulesManager(rules_file_path) # Ошибка должна быть поймана Pydantic валидатором в ReplyActionParams


    def test_reload_rules_success(self, create_rules_file):
        initial_rules_content = {
            "rules": [{"rule_id": "initial", "priority": 1, "conditions": [{"type": "keyword_match", "keywords": ["initial"]}], "action": "drop", "action_params": {}}]
        }
        rules_file_path = create_rules_file(initial_rules_content, "reload_test.yaml")
        manager = RulesManager(rules_file_path)
        assert len(manager.get_rules()) == 1
        assert manager.get_rules()[0].rule_id == "initial"

        new_rules_content = {
            "rules": [
                {"rule_id": "reloaded_1", "priority": 5, "conditions": [{"type": "keyword_match", "keywords": ["new1"]}], "action": "drop", "action_params": {}},
                {"rule_id": "reloaded_2", "priority": 2, "conditions": [{"type": "keyword_match", "keywords": ["new2"]}], "action": "drop", "action_params": {}}
            ]
        }
        # Перезаписываем тот же файл
        create_rules_file(new_rules_content, "reload_test.yaml") 
        
        assert manager.reload_rules() is True
        assert len(manager.get_rules()) == 2
        assert manager.get_rules()[0].rule_id == "reloaded_2" # Проверка сортировки
        assert manager.get_rules()[1].rule_id == "reloaded_1"

    def test_reload_rules_file_not_found(self, create_rules_file):
        rules_file_path = create_rules_file(VALID_RULES_CONTENT, "original.yaml")
        manager = RulesManager(rules_file_path)
        original_rules = list(manager.get_rules()) # Копируем для сравнения

        os.remove(rules_file_path) # Удаляем файл
        
        assert manager.reload_rules() is False # Перезагрузка должна провалиться
        assert manager.get_rules() == original_rules # Правила не должны были измениться

    def test_reload_rules_invalid_yaml_syntax(self, create_rules_file, tmp_path):
        rules_file_path = create_rules_file(VALID_RULES_CONTENT, "reload_invalid.yaml")
        manager = RulesManager(rules_file_path)
        original_rules = list(manager.get_rules())

        # Создаем файл с невалидным синтаксисом на том же пути
        invalid_yaml_content = "rules: - rule_id: test\n  priority: 10\n conditions: [{type: keyword_match, keywords: [test]}]"
        with open(rules_file_path, 'w', encoding='utf-8') as f:
            f.write(invalid_yaml_content)
            
        assert manager.reload_rules() is False
        assert manager.get_rules() == original_rules
        
    # Можно добавить больше тестов на разные Pydantic ошибки, специфичные условия и т.д. 