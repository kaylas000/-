# Нейро-сметчик — рабочий MVP по ТЗ v1.1

Локальный (on-premise) AI-ассистент сметчика: **человек принимает финальное решение**, система готовит черновик сметы, помечает сомнительные позиции, считает деньги детерминированным кодом и выпускает Excel/PDF/CSV.

Репозиторий содержит не только описание, но и **работающую реализацию** пайплайна ТЗ v1.0 + доработок v1.1, веб-интерфейс сметчика, базу знаний, golden test set на 122 запроса, 47 автотестов и OpenAPI-спецификацию.

> ⚠️ Демо-данные (`data/price_catalog.json`) — **синтетические**. Это не ГЭСН/ФЕР. Перед промышленной эксплуатацией замените прайс на лицензионно чистый источник компании (ТЗ §7.4).

---

## Быстрый старт

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make init          # генерация каталога, схемы БД, golden set, baseline дрейфа
make test          # 47 тестов: unit / integration / E2E / red teaming / golden
make run           # http://localhost:8000  (Swagger: /docs, OpenAPI: /openapi.yaml)
```

Альтернатива без venv: `.venv/bin/uvicorn neuro_smetchik.api:app --host 0.0.0.0 --port 8000` (с `PYTHONPATH=src`).

**GPU не требуется.** По умолчанию `LLM_ENABLED=false`: включён детерминированный rule-based экстрактор и локальный гибридный поиск. Чтобы подключить vLLM/TGI с Qwen2.5, выставьте `LLM_ENABLED=true`, `LLM_BASE_URL=http://vllm:8000/v1` (разрешены только хосты внутреннего периметра — см. `.env.example`).

---

## Что попробовать в интерфейсе

| Сценарий | Действие | Что увидеть |
|---|---|---|
| Обычный черновик | «Сгенерировать черновик» с примером «Ванная…» | 8–10 позиций, confidence-маркировка, итоги с НДС, замечания валидации, предложения по полноте |
| Человек-в-контуре | Пример «Размытый запрос (эскалация)» | красная позиция с confidence 0.18, предупреждение, уведомление об эскалации |
| Clarification Loop | запрос без площади, например «отремонтировать кухню, плитка на пол» | вопрос (≤5 итераций), ответ/пропуск → пересчёт в новую версию |
| Revision Loop | измените «Кол-во» в таблице → «Применить правки» | новая immutable-версия, diff-view, запись в `llm_corrections` |
| Документы | Excel / PDF / Гранд-Смета CSV | фирменный шаблон, цветовая индикация уверенности |
| Четыре глаза | смета от 500 000 ₽ → «Утвердить» сметчиком, затем руководителем с MFA | `pending_second_approval` → `approved` |
| Prompt Version Control | «Промпты» → создать версию → активировать → откат на v1 | откат без деплоя кода, canary 25% |
| Мониторинг | «Golden-прогон», «Drift check», «Freshness» | точность на 122 кейсах, error budget, SLA, состояние 8 циклов |
| Трассировка | «Трассировка» по `trace_id` из черновика | все шаги, попытки, версии промптов/моделей, LLM inference log |
| Аудит | роль «Руководитель» + MFA → «Аудит» | append-only hash-chain, попытки prompt injection |
| Анти-галлюцинации | «Ванная…» → каждая строка имеет `catalog_id` | позиция не может появиться без записи в `price_catalog` |

---

## Архитектура (кратко)

```
Parser → Clarification → Search → Matching → Calculation → Validation → Document
                 ↑                                              ↓
           Orchestrator (trace_id, retry, circuit breaker, escalation)
                 + Vision/OCR, Notification, Prompt Management
                 + Feedback / Drift / Freshness / Plan-Fact Loops
```

* **Деньги — только `Decimal`**, независимый пересчёт через `Fraction` + целые копейки, контрольная сумма версии (ТЗ §3.2.5).
* **Цены — только из `price_catalog`**; LLM не придумывает расценки и не вычисляет (ТЗ §5.2, §6.1).
* **Версии неизменяемы**: триггеры `BEFORE UPDATE/DELETE` на `smeta_versions`, `smeta_positions`, логах.
* **Логи LLM** (`llm_inference_log`) append-only, отдельная таблица, retention ≥12 мес.
* **Аудит** — hash-chain; prompt injection детектируется до передачи в модель.
* **Всё локально**: исходящие вызовы разрешены только на `127.0.0.1/localhost/vllm/llm/host.docker.internal`.

Подробнее: [docs/architecture.md](docs/architecture.md), [docs/TZ-Neuro-Smetchik-v1.1.md](docs/TZ-Neuro-Smetchik-v1.1.md).

---

## Структура

```
src/neuro_smetchik/
  api.py            FastAPI + контракты + RBAC + rate limiting + раздача UI
  orchestrator.py   детерминированный пайплайн, retry, circuit breaker
  parser_service.py строгая схема, retry ≤3, rule-based/LLM-экстракция
  clarification.py  ≤5 итераций, пропуск, таймаут
  search.py         semantic (char-ngram TF-IDF) + keyword, p95 ≤500 мс
  matching.py       confidence, расширенный поиск, эскалация
  calculation.py    Decimal + независимый пересчёт
  validation.py     аномалии, дубли, полнота, LLM-judge
  documents.py      xlsx / PDF (DejaVu, кириллица) / CSV для Гранд-Смета
  revision.py       дельта-правки, версии, diff-view
  vision.py         качество фото, confidence, деградация в ручной ввод
  prompts.py        Prompt Version Control, canary, откат
  loops.py          golden / drift / freshness / plan-fact / feedback / метрики
  security.py       RBAC, MFA, injection, аудит hash-chain, загрузки
  schema.sql        27 таблиц + append-only триггеры
  web/              рабочее место сметчика (vanilla JS, WCAG-база)
scripts/            init_db, build_catalog, evaluate_golden, export_openapi
tests/              47 тестов (pytest), включая E2E и red teaming
docs/               ТЗ v1.1, архитектура, приложения А–Е, статус реализации
openapi/            neuro-smetchik.yaml (Приложение Г)
```

---

## Команды

| Команда | Назначение |
|---|---|
| `make init` | создать БД, загрузить 66 расценок, 122 golden-примера, 6 промптов |
| `make test` | полный набор тестов |
| `make golden` | отчёт по golden test set (baseline −2% — критерий релиза) |
| `make openapi` | перегенерировать `openapi/neuro-smetchik.yaml` |
| `make run` | запуск API + UI на `0.0.0.0:8000` |

---

## Границы MVP (что сознательно упрощено)

См. [docs/implementation-status.md](docs/implementation-status.md). Ключевое: SQLite вместо PostgreSQL, in-process сервисы вместо отдельных контейнеров, локальный TF-IDF вместо Qdrant, rule-based парсер при отключённом vLLM, эвристический анализ фото вместо Qwen2.5-VL, CSV-экспорт вместо полной интеграции с Гранд-Смета/АРПС, заголовочная аутентификация вместо Vault/OIDC. Контракты и точки расширения сохранены.

## Документация

* [ТЗ v1.1 (консолидированное)](docs/TZ-Neuro-Smetchik-v1.1.md)
* [Архитектура и циклы](docs/architecture.md)
* [Приложение А — RACI](docs/appendix-a-raci.md)
* [Приложение Б — ER-диаграмма](docs/appendix-b-er-diagram.md)
* [Приложение В — промпты](docs/appendix-c-prompts.md)
* [Приложение Г — API-контракты / OpenAPI](docs/appendix-d-api-contracts.md)
* [Приложение Д — Playbook ИБ](docs/appendix-e-security-playbook.md)
* [Приложение Е — Политика использования AI](docs/appendix-f-ai-usage-policy.md)
* [Стратегия тестирования и DoD](docs/test-strategy.md)
* [Статус реализации по пунктам ТЗ](docs/implementation-status.md)
