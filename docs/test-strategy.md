# Стратегия тестирования (ТЗ v1.1 §8.5) и Definition of Done

## 1. Уровни тестирования

| Уровень | Что проверяется | Инструменты / подход | Где в репозитории |
|---|---|---|---|
| Unit | Расчёт (Decimal, округление, коэффициенты, НДС), независимый пересчёт, схемы, санитизация | `pytest` | `tests/test_calculation.py`, `test_parser.py` |
| Integration | Взаимодействие сервисов через API-контракты, immutable-версии, diff, four eyes, документы, промпты | `TestClient` + контрактные проверки | `tests/test_versioning.py`, `test_documents.py` |
| E2E | Полный сценарий 3.1: запрос → уточнение → правки → утверждение → документы → обратные связи → аудит | `TestClient`, golden scenarios | `tests/test_e2e.py` |
| Регрессия качества LLM | Golden test set (122 запроса) при смене промпта/модели/KB; порог ≥ baseline −2 % | `scripts/evaluate_golden.py`, `loops.evaluate_golden()` | `tests/test_e2e.py::test_golden_acceptance_criteria` |
| Нагрузочное | p95/p99 времени, SLA Search ≤500 мс | k6/Locust (в проде), встроенные замеры latency | `loops.metrics()`, `tests/test_search_matching.py` |
| Red teaming / Security | Prompt injection, извлечение системного промпта, jailbreak, подмена MIME, EXIF-injection, RBAC/MFA | чек-лист OWASP LLM Top-10, параметрайзд-тесты | `tests/test_security.py` |
| Отказоустойчивость | Отключение GPU/сервисов, circuit breaker, fallback | Chaos engineering в Staging; в MVP — unit-тесты порогов и fallback | `orchestrator.with_retry`, `tests/test_parser.py` |

**Критерий готовности к релизу:** все уровни пройдены, регрессия на golden set не хуже −2 %, error budget ≤1 %, hash-chain аудита целостен.

## 2. Golden test set

* Объём: **122 запроса** (120 сгенерированных по 25 фразам × 6 типов помещений + 2 робастных кейса).
* Для каждого запроса фиксируются: ожидаемые `room_type`/`area_m2`, эталонная формулировка `probe` и ожидаемые `catalog_id`.
* Метрики:
  * `parser_accuracy` — корректность извлечения параметров (критерий №1, ≥90 %);
  * `matching_top1_accuracy` — top-1 попадание по `probe` (критерий №2);
  * `auto_precision` — доля корректных среди **авто-принятых** совпадений (≥85 %);
  * `matching_recall` — покрытие ожидаемых позиций всеми подсказками пайплайна;
  * `search_latency_p95_ms` — SLA Search (≤500 мс).

**Текущий baseline (MVP, детерминированный режим):**
```
total                    122
parser_accuracy          1.000
matching_top1_accuracy   1.000
matching_recall          1.000
auto_accepted            122
auto_precision           1.000
search_latency_p95_ms    0.68
pass                     true
```
Baseline хранится в `model_versions.golden_accuracy` и `drift_checks.verdict=baseline_set`. Важно: это **синтетический** набор; на реальном архиве смет метрики будут ниже — калибровку проводит Domain Expert на этапе 0.

## 3. Запуск

```bash
make test                                   # все 47 тестов
.venv/bin/python scripts/evaluate_golden.py --report   # отчёт по golden set
.venv/bin/python scripts/evaluate_golden.py --write    # зафиксировать новый baseline
make openapi                                # экспорт спецификации
```

## 4. Definition of Done по этапам (ТЗ §9)

| Этап | DoD | Проверка |
|---|---|---|
| 0 | golden ≥100 запросов, покрытие ≥70 % частых позиций, точность ≥85 % | `golden_set.json` (122), `catalog.coverage()`, отчёт |
| 1 | E2E в Dev, unit/integration зелёные, API-документация | `make test`, `/openapi.yaml` |
| 2 | расхождения с ручными сметами зафиксированы, точность Matching измерена | Shadow Mode отчёт, `loops.metrics()` |
| 3 | ≥50 кейсов обратной связи, критические баги устранены | `llm_corrections`, `/feedback` |
| 4 | частота эскалаций снижается, NPS/CSAT измерен | `metrics.escalation_rate`, опрос |
| 5 | SLA 8.6 соблюдены, политика использования подписана | Grafana дашборды, приказ |
| 6 | fine-tuning, drift-мониторинг, ежеквартальная ревизия полноты | `drift_checks`, `data_freshness_log` |

## 5. Что тестируется отдельно в проде

* Нагрузка: ≥N одновременных пользователей, p95 ≤60 с, p99 ≤120 с (k6/Locust).
* Chaos: отключение GPU, разрыв Qdrant/MinIO, переполнение очереди Redis.
* Восстановление: ежедневный full backup + WAL, RPO ≤1 ч, RTO ≤4 ч, тестовый restore.
* Пентест: сетевой аудит исходящего трафика, prompt injection, попытка правки append-only таблиц.
* Юзабилити: ≥5 сметчиков, понятность confidence-индикации, базовые WCAG.
* Юридический аудит: лицензии ГЭСН/ФЕР и весов Qwen2.5.
