# Приложение Г — Схема API между микросервисами (OpenAPI-спецификации)

Машиночитаемая спецификация: **[`openapi/neuro-smetchik.yaml`](../openapi/neuro-smetchik.yaml)** (генерируется `make openapi`). Интерактивная документация: `/docs` (Swagger), `/redoc`, JSON: `/openapi.json`, YAML: `/openapi.yaml`.

## 1. Общие принципы

| Правило | Реализация |
|---|---|
| Формат | REST + JSON, `Content-Type: application/json`; загрузка файлов — `multipart/form-data` |
| Версионирование | Префикс `/api/v1/` у всех бизнес-эндпоинтов |
| Трассировка | `trace_id` (UUID v4) создаётся Orchestrator, передаётся во все шаги, возвращается в ответе, по нему доступен `GET /admin/trace/{trace_id}` |
| Таймауты / retry | Задаются Orchestrator (`retry_base_delay_ms=50`, ×2), не внутри сервисов |
| Ошибки | `{"detail": "...", "code": "..."}` + HTTP 400/403/404/409/429/500 |
| Аутентификация | В MVP — заголовки `X-User`, `X-Role`, `X-MFA`; в проде — OIDC/Vault, mTLS между сервисами |
| Логирование LLM | Каждый вызов → `llm_inference_log` (вход, выход, `prompt_version`, `model_version`, confidence, latency, `trace_id`) |
| Rate limiting | Token bucket, 120 запросов/мин на пользователя (настраивается) |

## 2. Карта эндпоинтов

| Метод | Путь | Назначение | Право |
|---|---|---|---|
| GET | `/api/v1/health` | Доступность, локальность, размер каталога | — |
| GET | `/api/v1/meta` | Пороги, SLA, роли, форматы | — |
| POST | `/api/v1/requests` | Запуск пайплайна, черновик сметы | `request:create` |
| POST | `/api/v1/clarification/{id}/answer` | Ответ / пропуск уточнения | `estimate:write` |
| POST | `/api/v1/clarification/{id}/timeout` | Таймаут → уведомление | `estimate:write` |
| GET | `/api/v1/estimates` | Реестр смет | `estimate:read` |
| GET | `/api/v1/estimates/{id}` | Смета/версия с позициями | `estimate:read` |
| GET | `/api/v1/estimates/{id}/versions` | История версий | `estimate:read` |
| GET | `/api/v1/estimates/{id}/diff` | Diff-view | `estimate:read` |
| POST | `/api/v1/estimates/{id}/revisions` | Дельта-правки | `estimate:write` |
| POST | `/api/v1/estimates/{id}/approve` | Утверждение (four eyes) | `estimate:approve[:second]` |
| GET | `/api/v1/estimates/{id}/documents/{fmt}` | `xlsx` / `pdf` / `csv` | `estimate:read` |
| POST | `/api/v1/estimates/{id}/feedback` | Feedback Loop | `estimate:write` |
| POST | `/api/v1/estimates/{id}/plan-fact` | Plan-Fact Loop | `estimate:write` |
| GET | `/api/v1/catalog`, `/catalog/search` | Каталог и гибридный поиск | `catalog:read` |
| GET | `/api/v1/matching` | Контракт Matching Service | `catalog:read` |
| POST | `/api/v1/vision` | Фото/скан | `request:create` |
| GET/POST | `/api/v1/prompts`, `/prompts/activate`, `/prompts/canary` | Prompt Version Control | `prompt:read` / `prompt:write` + MFA |
| GET | `/api/v1/notifications`, POST `/{id}/read` | Уведомления | роль |
| GET | `/api/v1/metrics` | SLA, дрейф, error budget, циклы | — |
| POST | `/api/v1/admin/golden`, `/admin/drift`, `/admin/freshness` | Циклы качества | роли |
| GET | `/api/v1/admin/trace/{trace_id}` | Сквозная трассировка | `audit:read` для manager/admin |
| GET | `/api/v1/admin/audit`, `/admin/events/{id}`, `/admin/corrections` | Аудит и Event Sourcing | `audit:read` + MFA |

## 3. Контракт: Parser Service (внутренний)

**Запрос** (Orchestrator → Parser, через `llm.complete`):
```json
{
  "trace_id": "9f1d…",
  "service": "parser",
  "prompt_version": "parser:v1",
  "messages": [
    {"role": "system", "content": "<преамбула + JSON-схема>"},
    {"role": "user", "content": "Ванная 8,5 м²: плитка и сантехника"}
  ],
  "response_format": {"type": "json_object"}
}
```

**Ответ** — строго по `ParsedRequest`:
```json
{
  "room_type": "ванная",
  "area_m2": 8.5,
  "work_scope": ["укладка кафеля", "прокладка полипропиленовых труб"],
  "region": "Москва",
  "constraints": [],
  "urgency": "обычная",
  "budget_limit": null,
  "source_type": "text",
  "raw_text": "…",
  "missing_fields": []
}
```
Ошибки схемы → retry (≤3) → детерминированный fallback. Все попытки в `pipeline_execution_log` (`step=parser`, `attempt`, `error`).

## 4. Контракт: Search Service

**Запрос:** `{"trace_id":"…","query_text":"штукатурка стен по маякам","top_n":8,"mode":"hybrid"}`

**Ответ:**
```json
{
  "trace_id": "…",
  "latency_ms": 0.6,
  "sla_ms": 500,
  "within_sla": true,
  "results": [
    {"catalog_id":"CAT-018","code":"НС-…-018","name":"Штукатурка стен по маякам до 20 мм",
     "unit":"м2","price":"720.00","score":0.94,"semantic_score":0.61,"keyword_score":1.0}
  ]
}
```
В проде semantic-часть — Qdrant + embeddings; контракт и метрики неизменны.

## 5. Контракт: Matching Service (базовый из ТЗ v1.1, расширен)

**Запрос:**
```json
{
  "trace_id": "uuid",
  "query_text": "штукатурка стен по маякам",
  "candidates": [{"catalog_id": "CAT-018", "score": 0.94}],
  "prompt_version": "matching_v3"
}
```

**Ответ:**
```json
{
  "trace_id": "uuid",
  "matched_catalog_id": "CAT-018",
  "confidence": 0.892,
  "status": "auto_accepted",
  "model_used": "rules-matcher-v1",
  "latency_ms": 0.7,
  "attempts": 1
}
```
`status ∈ {auto_accepted, needs_review, escalated}`. При `confidence < 0.5` позиция уходит на ручную проверку, при отсутствии кандидата — эскалация без создания позиции.

## 6. Контракт: Calculation Service

**Запрос:** `{"positions":[{"catalog_id":"CAT-018","quantity":"12.5","unit_price":"720.00","coefficients":{"region":"1.00"}}],"vat_rate":"0.20","overhead":"0.12","profit":"0.08"}`

**Ответ:**
```json
{
  "subtotal": "9000.00", "overhead": "1080.00", "profit": "1209.60",
  "vat": "2058.00", "grand_total": "13347.60",
  "checksum": "sha256…", "verification": "ok"
}
```
Все суммы — строки `Decimal`. `verification="mismatch"` блокирует утверждение.

## 7. Контракт: Revision Service

**Запрос:**
```json
{
  "operations": [
    {"op":"update","position_id":"p-…","field":"quantity","value":"3.5"},
    {"op":"add","catalog_id":"CAT-007","quantity":"1"},
    {"op":"remove","position_id":"p-…"}
  ],
  "reason": "Правки после замечаний клиента",
  "revision_text": "убери лишнюю штукатурку"
}
```
**Ответ:** полный объект сметы + `applied_operations` (для каждой операции `ok`/`error`). Неизвестный `catalog_id` отклоняется — защита от галлюцинаций.

## 8. Контракт: Vision/OCR Service

**Запрос:** `multipart/form-data` с полем `file` (JPEG/PNG/WebP/PDF, ≤15 МБ).

**Ответ:**
```json
{
  "accepted": true, "trace_id":"…", "quality_score": 0.72,
  "confidence": 0.72, "degraded_to_manual": false,
  "elements": [{"type":"площадь","value":"42","confidence":0.72,"source":"metadata"}],
  "model_used": "vision-rules-v1",
  "note": "При низком confidence необходим ручной ввод параметров"
}
```
Отклонение: HTTP 400 + причина (MIME/magic bytes/размер/подозрительное имя/инструкции в метаданных).

## 9. Контракт: Orchestrator → клиент (основной ответ `POST /requests`)

```json
{
  "id": "smt-…", "version_no": 1, "status": "needs_review", "title": "…",
  "trace_id": "…", "latency_ms": 34,
  "params": {"room_type":"ванная","area_m2":8.5,"work_scope":["…"],"region":"Москва"},
  "positions": [{"id":"p-…","catalog_id":"CAT-028","name":"…","unit":"м2",
                 "quantity":"19.84","unit_price":"1050.00","total":"24998.40",
                 "confidence":0.82,"status":"needs_review"}],
  "totals": {"subtotal":"…","overhead":"…","profit":"…","vat":"…",
             "grand_total":"…","checksum":"…","verification":"ok"},
  "issues": [{"level":"warning","code":"incomplete_scope","message":"…"}],
  "suggestions": [{"catalog_id":"CAT-048","name":"…","reason":"типовой состав работ по архиву"}],
  "questions": [], "clarification_session_id": null,
  "pipeline_steps": [{"step":"parser","status":"ok","duration_ms":0}],
  "escalations": [], "parser_attempts": [{"attempt":1,"status":"ok","source":"deterministic_fallback"}],
  "llm_degraded": true
}
```

## 10. Таймауты и политики повторов

| Взаимодействие | Таймаут | Retry | Поведение при отказе |
|---|---|---|---|
| API → Orchestrator | 120 с (p99) | 1 | 504 + эскалация |
| Orchestrator → LLM (vLLM) | 20 с | 2, ×2 | `deterministic_fallback` + уведомление |
| Orchestrator → Search | 500 мс (SLA p95) | 2, ×2 | лучшие кандидаты + пометка превышения |
| Matching → расширенный поиск | 500 мс | 1 | статус `needs_review` |
| Calculation / Validation | 2 с | 3, ×2 | circuit breaker, блокировка утверждения |
| Notification Service | ≤30 с на доставку | 2 | запись в журнал, повтор воркером |
