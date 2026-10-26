# Архитектура «Нейро-сметчик» (MVP →prod)

## 1. Контекст (C4 Level 1)

```mermaid
flowchart LR
  U[Сметчик / руководитель / клиент] -->|HTTPS, VPN| GW[API Gateway + RBAC + rate limit]
  subgraph OnPrem[Внутренний периметр — без исходящих AI-API]
    GW --> ORCH[Orchestrator / FastAPI]
    ORCH --> SRV[Parser · Clarification · Search · Matching · Calculation · Validation · Document · Revision · Vision · Notification · Prompt Mgmt]
    ORCH --> Q[Redis + Celery/RQ — очередь]
    SRV --> PG[(PostgreSQL 15+ / SQLite в MVP)]
    SRV --> VDB[(Qdrant — vector)]
    SRV --> FS[(MinIO — файлы/документы)]
    ORCH --> LLM[vLLM / TGI — Qwen2.5 7B/32B/72B]
    MON[Prometheus + Grafana] -.-> ORCH
    AUD[(Append-only аудит)] --- ORCH
  end
  ADMIN[ML/DevOps инженер] -->|VPN + MFA| GW
```

**Ключевое ограничение:** стрелки наружу отсутствуют. `LLM_BASE_URL` проверяется на принадлежность списку `LLM_ALLOWED_HOSTS`; любой внешний хост отклоняется, а пайплайн деградирует до детерминированного/ручного режима.

## 2. Пайплайн (детерминированный, без свободных LLM-агентов)

```mermaid
sequenceDiagram
  actor Сметчик
  participant API as API /v1
  participant O as Orchestrator
  participant P as Parser
  participant C as Clarification
  participant S as Search
  participant M as Matching
  participant Calc as Calculation
  participant V as Validation
  participant D as Document

  Сметчик->>API: POST /requests {text, client}
  API->>O: trace_id, actor, rate limit, injection guard
  O->>P: parse (≤3 попытки, строгая схема)
  P-->>O: ParsedRequest + missing_fields
  alt есть критичные пропуски
    O->>C: start_session (≤5 вопросов)
    C-->>Сметчик: вопрос по полю
    Сметчик->>C: ответ / пропуск
    C-->>O: уточнённые params + дефолты
  end
  O->>S: hybrid search по каждому work_scope
  S-->>O: top-N кандидатов (semantic + keyword)
  O->>M: match (confidence, extended re-search, LLM re-rank)
  M-->>O: catalog_id + confidence + status
  Note over O: позиция без реального catalog_id отбрасывается
  O->>Calc: Decimal qty × price × coeff + VAT, checksum
  Calc-->>O: totals + независимая верификация
  O->>V: аномалии / дубли / полнота / judge
  V-->>O: issues + suggestions
  O->>PG: НОВАЯ immutable-версия
  O->>D: xlsx / pdf / csv по запросу
  O-->>Сметчик: черновик + confidence + trace_id
```

**Circuit breaker:** на шагах `matching`, `calculation`, `validation`, `search`. После 3 сбоев подряд шаг временно отключается, создаётся эскалация и уведомление, пайплайн продолжается в ручном режиме. **Retry:** экспоненциальная задержка 50/100 мс, все попытки пишутся в `pipeline_execution_log`.

## 3. Слои и ответственность

| Слой | Компоненты | Правило |
|---|---|---|
| Presentation | Web UI (vanilla JS), Swagger UI | Confidence-маркировка, diff-view, aria-live, focus-visible |
| API | FastAPI `/api/v1`, Pydantic-схемы | trace_id, RBAC/MFA, rate limit, общий формат ошибок |
| Orchestration | `orchestrator.py` | Фиксированный порядок шагов, retry, эскалация |
| Domain services | 12 сервисов | Чистые функции; деньги только в Calculation |
| Data | PostgreSQL/SQLite, Qdrant, MinIO | DECIMAL, immutable-версии, append-only логи |

## 4. Циклы обратной связи

```mermaid
flowchart TB
  A[Запрос] --> B[Валидация в пайплайне]
  B --> C{Clarification Loop}
  C --> D[Revision Loop]
  D --> E[Feedback Loop → llm_corrections]
  E --> F[Fine-tuning / prompt tuning]
  G[Golden set] --> H[Model Drift Loop — ежедневно]
  I[Прайс-листы] --> J[Data Freshness Loop — еженедельно]
  K[Закрытый проект] --> L[Plan-Fact Loop → historical_correction_factors]
  M[Сбой сервиса] --> N[Инфраструктурный retry + circuit breaker]
```

## 5. Релизный процесс (Dev → Staging → Prod)

Артефакты версионируются **независимо**:

| Артефакт | Источник истины | Проверка перед Staging | Откат |
|---|---|---|---|
| Код | Git, semver | unit + contract + E2E + security | `git revert`, пересборка образа |
| Промпты | `prompt_versions` (БД) | golden set ≥ baseline −2 %, canary 5→25→100 % | `POST /prompts/activate` (без деплоя) |
| Веса модели | `model_versions` + хэш | golden set, лицензия, дрейф-тест | переключение активной версии |
| База знаний | `knowledge_base_versions` + хэш каталога | freshness, покрытие категорий, тестовый поиск | активация предыдущей версии KB |

Error budget ≤1 % технических ошибок: при превышении — заморозка релизов до устранения причин.

## 6. Инфраструктура и изоляция

`docker-compose.yml` в корне — справочный шаблон on-prem-стека (профили `core` и `gpu`): postgres, qdrant, minio, redis, vllm, api, worker, prometheus, grafana. Рекомендации:

* отдельные сети `dmz`, `app`, `data`; только `app` видит `vllm`;
* egress-правило firewall: `DENY` для известных внешних AI-API, `ALLOW` только внутренние репозитории артефактов;
* секреты — Vault / Docker secrets (в репозитории только `.env.example`);
* TLS 1.3 на шлюзе, AES-256 at rest для PostgreSQL/MinIO;
* VPN + MFA для администраторов; append-only аудит выносится в отдельную БД/схему.

## 7. Деградация и отказоустойчивость

| Сбой | Поведение |
|---|---|
| Недоступен vLLM/GPU | `deterministic_fallback` парсера, rule-based matching; уведомление в UI; расчёты и документы продолжают работать |
| Search > SLA | Логируется превышение, возвращаются лучшие кандидаты, позиции уходят на проверку |
| Нет кандидатов в каталоге | Позиция **не создаётся** (защита от галлюцинаций), создаётся эскалация сметчику |
| Несовпадение контрольной суммы | Утверждение заблокировано, ошибка валидации уровня `error` |
| 3 сбоя сервиса | Circuit breaker, эскалация, ручной режим |
| Плохое фото | `degraded_to_manual=true`, ручной ввод параметров |

## 8. Масштабирование

Stateless API масштабируется горизонтально; состояние — в PostgreSQL/Redis; воркеры Celery разбирают очередь; Qdrant шардируется по категориям/филиалам; региональные коэффициенты хранятся в `price_catalog.region_coeffs`; мультитенантность — через `tenant_id` во всех таблицах (точка расширения на этапе 4–5).
