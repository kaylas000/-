# Приложение А — Матрица RACI

**R** — Responsible (исполнитель), **A** — Accountable (отвечает за результат, один на строку), **C** — Consulted (консультирует), **I** — Informed (информируется).

| № | Процесс / артефакт | Product Owner | Domain Expert (сметчик) | Backend/ML | MLOps/DevOps | Data Engineer | QA | Руководитель | Администратор |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Инвентаризация источников и прав на ГЭСН/ФЕР | A | C | I | I | R | I | I | I |
| 2 | Нормализация и наполнение `price_catalog` | C | C | C | I | **R/A** | I | I | I |
| 3 | Формирование golden test set | C | **R** | C | I | C | A | I | I |
| 4 | Выбор/тест локальной LLM, хэш весов | C | I | **R/A** | C | I | C | I | C |
| 5 | Разработка Parser / Search / Matching | C | C | **R/A** | I | C | C | I | I |
| 6 | Calculation Service (Decimal, контрольная сумма) | I | C | **R/A** | I | I | R | I | I |
| 7 | Системные промпты и Prompt Version Control | C | C | **R/A** | C | I | C | I | C |
| 8 | Политика ИБ, RBAC, MFA, аудит | C | I | R | R | I | C | C | **A** |
| 9 | CI/CD, Dev/Staging/Prod, backup (RPO/RTO) | I | I | C | **R/A** | I | C | I | C |
| 10 | Тестирование (unit/E2E/red teaming/нагрузка) | C | C | C | C | I | **R/A** | I | I |
| 11 | Shadow Mode: сбор расхождений | A | R | C | I | C | C | I | I |
| 12 | Pilot Group: обратная связь сметчиков | A | R | C | I | I | C | I | I |
| 13 | Data Freshness Loop (еженедельно) | I | C | I | C | **R/A** | I | I | I |
| 14 | Model Drift Loop (ежедневно) | I | I | **R/A** | C | I | C | I | I |
| 15 | Plan-Fact Loop и коэффициенты | C | R | C | I | C | I | **A** | I |
| 16 | Утверждение сметы до порога | I | **R/A** | I | I | I | I | I | I |
| 17 | Утверждение сметы выше порога («четыре глаза») | I | R | I | I | I | I | **A** | I |
| 18 | Реагирование на инциденты ИБ | I | I | C | R | I | C | I | **A** |
| 19 | Обучение персонала, политика использования AI | **A** | R | C | I | I | C | C | I |
| 20 | Решение о полном внедрении / rollback | R | C | C | C | I | C | **A** | I |

## Эскалация

1. Сметчик → куратор качества (Domain Expert) — вопросы по расценкам и confidence.
2. Куратор качества → Product Owner — системные расхождения, массовые эскалации.
3. Product Owner + Администратор — инциденты ИБ, дрейф модели, заморозка релизов.
