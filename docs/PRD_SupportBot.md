1. Executive Summary

Предлагаемый продукт — интеллектуальный Telegram-бот для поддержки пользователей блокчейн-сервисов (кошельки, мосты и т. д.). Бот сочетает валидатор входящих сообщений, динамический маршрутизатор по YAML-правилам и RAG-генерацию ответов (FAISS + GPT-4o-mini). Это позволяет:
	•	отвечать на типовые вопросы ≤ 15 с;
	•	автоматически перенаправлять «неподходящие» запросы в специализированные каналы;
	•	снизить нагрузку live-агентов ≥ 65 % без потери качества.

2. Goals & Success Metrics

Цель	KPI	Целевое значение (MVP)
Сократить время первой реакции	Median First Response Time	≤ 15 с
Уменьшить нагрузку на live-агентов	% запросов, решённых ботом	≥ 65 %
Поддерживать качество ответов	CSAT (1-5)	≥ 4.0

3. Personas

Persona	Pain	Gain
Конечный пользователь	Долгий ответ, непонятные инструкции	Мгновенный, релевантный ответ
Служба поддержки	Рутина, выгорание	Фокус на сложных кейсах

4. Scope

In-Scope
	•	Приём сообщений в группах и DM
	•	Валидатор языка/токсичности
	•	Router & Dynamic Instructions (YAML-правила: reply / forward / drop)
	•	RAG-поиск по answers_table (FAISS)
	•	Генерация ответа GPT-4o-mini
	•	Логирование диалогов в SQLite

Out-of-Scope v1
	•	Многоязычная поддержка
	•	Интеграция с CRM/Help-desk
	•	Облачный хостинг и масштабирование
	•	Продвинутая аналитика (dashboard)

5. Functional Requirements

5.1 Message Intake
	•	FR-1 Бот получает Message из Telegram API.
	•	FR-2 Извлекает последние N реплик диалога по user_id.

5.2 Validator
	•	FR-3 Проверяет язык (только EN).
	•	FR-4 Детектирует токсичность/спам; при нарушении отвечает заглушкой.

5.3 Router & Dynamic Instructions
	•	FR-5 Загружает YAML-правила при старте и по /reload_rules.
	•	FR-6 Для каждого сообщения определяет action ∈ {reply, forward, drop}.
	•	FR-7 При forward пересылает сообщение в dst_chat_id.
	•	FR-8 При reply добавляет system_prompt из правила к LLM-промпту.

5.4 Retrieval (RAG)
	•	FR-9 Извлекает top-k (≤ 3) Q&A из FAISS < 200 мс.
	•	FR-10 Формирует контекст ≤ 2 000 токенов.

5.5 Answer Generation
	•	FR-11 Собирает промпт: system_prompt + history + context + user_message.
	•	FR-12 Генерирует ответ ≤ 500 токенов и отправляет в чат.

5.6 Logging
	•	FR-13 Записывает {ts, uid, rule_id, action, q, a, ctx} в SQLite.
	•	FR-14 Экспорт логов в CSV по запросу.

6. Non-Functional Requirements
	•	Performance – ответ ≤ 2 с при 1 k RPS локально.
	•	Security – ключи в .env; шифрование логов; GDPR-удаление PII.
	•	Accessibility – чистый текст, минимум emoji.
	•	Compliance – OpenAI policy, GDPR, локальное хранение данных.

7. Tech Stack

Компонент	Выбор	Причина
Язык	Python 3.12	зрелая экосистема
Telegram	python-telegram-bot	async-поддержка
LLM	OpenAI GPT-4o-mini	цена/качество
Agent Orchestration	OpenAI Agent SDK	memory, tools
Vector Store	FAISS (pkl)	офлайн, быстро
Rules Store	YAML + pyyaml	читабельно, «горячая» перезагрузка
DB	SQLite	file-based, MVP
Env Mgmt	python-dotenv	безопасность

8. Agents

Агент	Роль	Техники / Методики
ValidatorAgent	Фильтр языка/токсичности	FastText, OpenAI moderation
RouterAgent	Маршрутизация по YAML-правилам	Regex/keyword match
RetrieverAgent	Поиск контекста	FAISS + OpenAIEmbeddings
AnswerAgent	Генерация ответа	Prompt-engineering, RAG-fusion
LoggerAgent	Журналирование	Async SQLite writes

9. Risks & Mitigations

Риск	V/I	План
Неверная маршрутизация	M/H	unit-тесты Router, тест-матрица правил
Галлюцинации LLM	H/M	human-review, уточнение промптов
OpenAI rate-limit	M/H	кеш, back-off
Утечка данных	H/H	шифрование, PII-masking

10. Epics

Эпик	Цель	Done-критерий	Ключевые задачи
E0. Git Repo & Среда	Централизованный код и reproducible-среда	Репо с README, .gitignore, pyproject.toml	Инициализировать repo; настроить pre-commit (black, ruff); Makefile/poetry для venv
E1. Telegram Handler	Принимать сообщения и отвечать «echo»	Бот онлайн, echo ≤ 2 с	Создать Bot Token; async-хендлер MessageHandler; поддержать группы и DM
E2. Validator	Фильтровать не-EN; заглушка-ответ
E3. Router & Dynamic Instructions	Выбрать инструкцию и действие (reply/forward/drop)	100 % сообщений получают верный action	YAML-rules store; RouterAgent; команда /reload_rules; пересылка в dst_chat_id
E4. Retrieval (RAG)	Достать релевантный контекст	top-3 Q&A < 200 мс	Загрузить answers_table.pkl; FAISS + OpenAIEmbeddings; get_context()
E5. Answer Generation	Сформировать связный ответ	≥ 50 % кейсов закрыты ботом	Промпт: system_prompt+history+context; GPT-4o-mini; ответ ≤ 500 токенов
E6. Logging	Хранить данные для улучшений	100 % диалогов в SQLite	Таблица dialogs; async-write; CSV-экспорт скрипт


11. Strong Opinion on Priorities
	1.	Router → Validator → Retrieval → Answer: без Router некорректные вопросы уйдут в LLM и ухудшат метрики.
	2.	Логирование обязательно в MVP — без данных невозможно улучшать правила и RAG.
	3.	Сложный UI и аналитика откладываются до подтверждения ценности автоответов.