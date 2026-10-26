# Статус реализации по пунктам ТЗ v1.1

Легенда: ✅ реализовано и покрыто тестами · 🟡 частично / демонстрационный контур · ⬜ требует промышленной реализации.

## 3. Функциональные требования

| Пункт | Статус | Реализация |
|---|---|---|
| 3.1 User Flow | ✅ | `POST /requests` → Clarification → черновик → проверка/правки → approve → документ → ревизия → план/факт |
| 3.2.1 Parser, схема, retry ≤3, лог попыток | ✅ | `parser_service.py`, `models.ParsedRequest`, `llm.validate_llm_json`, `pipeline_execution_log` |
| 3.2.2 Clarification ≤5, пропуск | ✅ | `clarification.py`, `timeout()` + уведомление |
| 3.2.3 Search гибридный, ≤500 мс, top-N | ✅ | `search.py` (char-ngram TF-IDF + keyword); 🟡 Qdrant/embeddings в проде |
| 3.2.4 Matching пороги 0.85/0.5 | ✅ | `matching.py`, расширенный поиск, LLM re-rank при включённом vLLM |
| 3.2.5 Calculation без LLM, Decimal, независимый пересчёт | ✅ | `calculation.py` (`Fraction` + целые копейки), checksum версии |
| 3.2.6 Validation: аномалии, дубли, полнота, judge | ✅ | `validation.py`; judge — 🟡 только при локальном vLLM |
| 3.2.7 Document: xlsx, PDF, шаблон, Гранд-Смета | ✅ / 🟡 | `documents.py`: Excel/PDF с кириллицей; экспорт — 🟡 CSV-совместимый, не полный формат АРПС |
| 3.2.8 Revision: дельта, версии, diff | ✅ | `revision.py`, `/estimates/{id}/diff` |
| 3.2.9 Orchestrator: детерминизм, retry, эскалация | ✅ | `orchestrator.py`, circuit breaker, `trace_id` |
| 3.2.10 Vision/OCR | 🟡 | `vision.py`: качество фото, blur/light, confidence, деградация в ручной ввод; ⬜ Qwen2.5-VL/OCR-движок |
| 3.2.11 Notification | ✅ / 🟡 | `notifications.py`: UI + email-журнал, приоритеты, подписки; ⬜ реальный SMTP/мессенджер |
| 3.2.12 Prompt Management | ✅ | `prompts.py`: версии, canary, откат без деплоя, привязка к запуску |
| 3.3 Циклы 1–8 | ✅ | `orchestrator.py`, `clarification.py`, `revision.py`, `loops.py`, `notifications.py` |
| 3.4 API-контракты, trace_id, лог LLM | ✅ | [Приложение Г](appendix-d-api-contracts.md), `openapi/neuro-smetchik.yaml`, `llm_inference_log` |

## 4. Инфраструктура

| Пункт | Статус | Комментарий |
|---|---|---|
| 4.1–4.2 Локальность, железо | ✅ / ⬜ | Локальность обеспечена программно; ⬜ закупка/аренда GPU — решение заказчика (вопрос 4) |
| 4.3 Стек | 🟡 | `docker-compose.yml` — справочный шаблон (postgres/qdrant/minio/redis/vllm/prometheus/grafana); в MVP всё in-process на SQLite |
| 4.4 Изоляция | ✅ / ⬜ | `settings.llm_is_local` + allowlist хостов; ⬜ firewall-правила и VPN — задача DevOps |
| 4.5 Dev/Staging/Prod | 🟡 | Процесс описан в [architecture.md](architecture.md#5-релизный-процесс-dev--staging--prod); ⬜ реальные контуры и CI |

## 5. Модель данных

| Пункт | Статус | Комментарий |
|---|---|---|
| 5.1 Таблицы v1.0 + v1.1 | ✅ | 27 таблиц в `schema.sql` |
| 5.2 Immutable/Decimal/FK/Event Sourcing | ✅ | Триггеры, Decimal-строки, FK на `price_catalog`, `estimate_events` |
| 5.3 Backup RPO/RTO | ⬜ | Требуется pg_basebackup + WAL + снапшоты Qdrant/MinIO; в MVP — SQLite WAL только |

## 6. Безопасность

| Пункт | Статус | Комментарий |
|---|---|---|
| 6.1 Injection, роли, схема, синтетика, анти-галлюцинации | ✅ | `security.py`, `prompts.py`, FK, `validation.hallucinated_catalog_ref` |
| 6.2 RBAC/MFA/аудит | ✅ / 🟡 | Роли + MFA-флаг + append-only hash-chain; ⬜ AES-256/TLS1.3/Vault/OIDC на уровне инфраструктуры |
| 6.3 152-ФЗ, retention, отзыв доступа | 🟡 | Локальность и `users.active` реализованы; ⬜ юридические процедуры заказчика |
| 6.4 NDA и доступ к промптам | 🟡 | Ролевая модель на `/prompts`; ⬜ организационные меры |
| 6.5 Четыре глаза, аномалии | ✅ | `/approve` с порогом, `validation.price_anomaly` |
| 6.6 Rate limit, MIME/magic bytes, EXIF | ✅ | `security.RateLimiter`, `validate_upload`; ⬜ антивирусный сканер |
| 6.7 Лицензии моделей | 🟡 | `model_versions.weights_hash/license`, Qwen License/Apache 2.0 проверяется перед промом; ⬜ юраудит |

## 7. База знаний

| Пункт | Статус | Комментарий |
|---|---|---|
| 7.1 Источники | 🟡 | 66 синтетических расценок + `rate_catalog_sources` (лицензия помечена как internal-demo) |
| 7.2 Нормализация, синонимы, категории | ✅ | Единые `м2/м.п./шт/м3`, синонимы, категории, `qty_rule`, типовые составы |
| 7.3 Контроль качества | ✅ | `catalog.coverage()`, `freshness_check()`, golden-прогон |
| 7.4 Юридическая проверка | ⬜ | Обязательна до загрузки реальных ГЭСН/ФЕР |
| 7.5 Актуальность | ✅ | `POST /admin/freshness`, `knowledge_base_versions`, `data_freshness_log` |

## 8. NFR

| Пункт | Статус | Комментарий |
|---|---|---|
| 8.1 Производительность | ✅ / ⬜ | В MVP p95 ≪1 с; ⬜ нагрузочное тестирование на N пользователей |
| 8.2 Fallback / circuit breaker / retry | ✅ | `llm.py` fallback, `orchestrator.CircuitBreaker`, `with_retry` |
| 8.3 Масштабирование | 🟡 | Stateless API, региональные коэффициенты; ⬜ мультитенантность `tenant_id` |
| 8.4 UX: confidence, diff, WCAG | ✅ / 🟡 | Цветовая маркировка, diff-view, aria/focus/контраст; ⬜ голосовой ввод |
| 8.5 Test Strategy | ✅ | 47 тестов, golden 122 кейса, [test-strategy.md](test-strategy.md) |
| 8.6 Измеримые SLA | ✅ | `loops.metrics()` + дашборд `/metrics` |

## 9–12. Процессы и приёмка

* DoD этапов, RACI, политика, playbook — документы подготовлены ([ТЗ §9](TZ-Neuro-Smetchik-v1.1.md#9-этапы-разработки-и-dod), приложения А, Д, Е).
* Критерии приёмки №1–8, 11 — ✅ в MVP; №9–10 (голос, юзабилити-тест с 5 сметчиками) — 🟡 требуют пилотной группы.
* Экономическое обоснование (§11) и ответы на вопросы заказчика (§15) — ⬜ заполняются заказчиком.

## Известные ограничения MVP, которые нужно закрыть до прома

1. SQLite вместо PostgreSQL/Qdrant/MinIO — заменить при переносе на прод-стек.
2. Rule-based парсер и character n-gram поиск вместо локальной LLM/эмбеддингов — включить vLLM с Qwen2.5 и Qdrant, затем перекалибровать confidence на реальном golden set.
3. Vision — эвристика качества фото, не настоящий OCR/VLM.
4. Аутентификация через заголовки — заменить на OIDC + Vault + mTLS.
5. CSV для Гранд-Смета — упрощённый; требуется сверка формата с версией ПО (вопрос 3 заказчику).
6. Нет реального SMTP/мессенджера, антивируса, backup-процедур и k6-нагрузки.
7. Синтетический прайс не имеет отношения к нормативным базам — юридическая проверка обязательна.
