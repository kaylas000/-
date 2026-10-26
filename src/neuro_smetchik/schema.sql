-- ============================================================================
-- Нейро-сметчик: реляционная схема (ТЗ 5.1, 5.2 + дополнения v1.1 разд. 5)
-- SQLite-диалект для MVP; для прома — PostgreSQL 15+ (DECIMAL/NUMERIC, append-only
-- обеспечивается правами роли + отдельной схемой). См. docs/appendix-b-er-diagram.md
-- ВАЖНО: все деньги хранятся как TEXT (строка Decimal), НЕ FLOAT.
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    role            TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    permissions     TEXT NOT NULL DEFAULT '[]'      -- JSON-массив
);

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    role            TEXT NOT NULL REFERENCES roles(role),
    mfa_enabled     INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_catalog_sources (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    license         TEXT NOT NULL,                  -- лицензия/правовой статус (ТЗ 7.4)
    legal_status    TEXT NOT NULL DEFAULT 'checked',
    url             TEXT,
    checked_at      TEXT NOT NULL,
    responsible     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_catalog (
    id              TEXT PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    unit            TEXT NOT NULL,
    category        TEXT NOT NULL,
    base_price      TEXT NOT NULL,                  -- DECIMAL как строка
    synonyms        TEXT NOT NULL DEFAULT '[]',
    tags            TEXT NOT NULL DEFAULT '[]',
    qty_rule        TEXT NOT NULL DEFAULT '{}',
    rooms           TEXT NOT NULL DEFAULT '[]',
    hist_min        TEXT NOT NULL DEFAULT '0',
    hist_avg        TEXT NOT NULL DEFAULT '0',
    hist_max        TEXT NOT NULL DEFAULT '0',
    region_coeffs   TEXT NOT NULL DEFAULT '{}',
    source_id       TEXT REFERENCES rate_catalog_sources(id),
    valid_from      TEXT NOT NULL,
    valid_to        TEXT,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_catalog_category ON price_catalog(category);
CREATE INDEX IF NOT EXISTS idx_catalog_code ON price_catalog(code);

CREATE TABLE IF NOT EXISTS knowledge_base_versions (
    id              TEXT PRIMARY KEY,
    version         TEXT UNIQUE NOT NULL,
    created_at      TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    catalog_hash    TEXT NOT NULL,
    prompt_service_versions TEXT NOT NULL DEFAULT '{}',
    model_version   TEXT,
    status          TEXT NOT NULL DEFAULT 'active'  -- active | draft | rolled_back
);

CREATE TABLE IF NOT EXISTS smetas (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    client          TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft|needs_review|approved|archived
    region          TEXT NOT NULL DEFAULT 'Москва',
    source_request  TEXT NOT NULL DEFAULT '',
    source_type     TEXT NOT NULL DEFAULT 'text',   -- text|voice|photo|scan
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 0,
    approved_by     TEXT,
    approved_at     TEXT,
    second_approver TEXT,
    trace_id        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_smetas_status ON smetas(status);

-- Версии сметы НЕИЗМЕНЯЕМЫ (immutable history, ТЗ 5.2 / Revision Service 3.2.8)
CREATE TABLE IF NOT EXISTS smeta_versions (
    id              TEXT PRIMARY KEY,
    smeta_id        TEXT NOT NULL REFERENCES smetas(id),
    version_no      INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    created_by      TEXT NOT NULL,
    change_reason   TEXT NOT NULL DEFAULT '',
    parent_version  INTEGER,
    totals          TEXT NOT NULL DEFAULT '{}',    -- JSON
    checksum        TEXT NOT NULL,
    UNIQUE(smeta_id, version_no)
);

CREATE TABLE IF NOT EXISTS smeta_positions (
    id              TEXT PRIMARY KEY,
    version_id      TEXT NOT NULL REFERENCES smeta_versions(id),
    catalog_id      TEXT NOT NULL REFERENCES price_catalog(id),  -- защита от галлюцинаций
    name            TEXT NOT NULL,
    unit            TEXT NOT NULL,
    quantity        TEXT NOT NULL,                 -- DECIMAL
    unit_price      TEXT NOT NULL,                 -- DECIMAL
    coefficients    TEXT NOT NULL DEFAULT '{}',
    subtotal        TEXT NOT NULL,
    vat_rate        TEXT NOT NULL,
    vat_amount      TEXT NOT NULL,
    total           TEXT NOT NULL,
    confidence      REAL NOT NULL,
    status          TEXT NOT NULL,                 -- auto_accepted|needs_review|escalated|manual
    source_query    TEXT NOT NULL DEFAULT '',
    notes           TEXT NOT NULL DEFAULT '',
    sort_order      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_positions_version ON smeta_positions(version_id);

CREATE TABLE IF NOT EXISTS clarification_sessions (
    id              TEXT PRIMARY KEY,
    smeta_id        TEXT REFERENCES smetas(id),
    trace_id        TEXT,
    max_turns       INTEGER NOT NULL DEFAULT 5,
    asked_count     INTEGER NOT NULL DEFAULT 0,
    parsed_json     TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'open',  -- open|completed|skipped|expired
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clarification_turns (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES clarification_sessions(id),
    turn_no         INTEGER NOT NULL,
    field           TEXT NOT NULL,
    question        TEXT NOT NULL,
    asked_at        TEXT NOT NULL,
    answer          TEXT,
    answered_at     TEXT,
    skipped         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS llm_corrections (
    id              TEXT PRIMARY KEY,
    version_id      TEXT NOT NULL,
    position_id     TEXT,
    field           TEXT NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    corrected_by    TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    used_for_training INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS golden_examples (
    id              TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    probe           TEXT NOT NULL DEFAULT '',
    expected_params TEXT NOT NULL DEFAULT '{}',
    expected_catalog_ids TEXT NOT NULL DEFAULT '[]',
    category        TEXT NOT NULL DEFAULT 'generic',
    added_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_fact_comparison (
    id              TEXT PRIMARY KEY,
    smeta_id        TEXT NOT NULL,
    version_no      INTEGER NOT NULL,
    planned_total   TEXT NOT NULL,
    fact_total      TEXT NOT NULL,
    deviation_pct   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS historical_correction_factors (
    id              TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    region          TEXT NOT NULL,
    factor          TEXT NOT NULL,
    period          TEXT NOT NULL,
    sample_size     INTEGER NOT NULL,
    computed_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_execution_log (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    smeta_id        TEXT,
    step            TEXT NOT NULL,
    attempt         INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    duration_ms     INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    input_json      TEXT,
    output_json     TEXT,
    prompt_version  TEXT,
    model_version   TEXT
);
CREATE INDEX IF NOT EXISTS idx_pipeline_trace ON pipeline_execution_log(trace_id, id);

CREATE TABLE IF NOT EXISTS security_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    actor           TEXT NOT NULL,
    role            TEXT NOT NULL,
    action          TEXT NOT NULL,
    entity          TEXT NOT NULL,
    entity_id       TEXT,
    ip              TEXT,
    details         TEXT,
    severity        TEXT NOT NULL DEFAULT 'info',
    prev_hash       TEXT NOT NULL,
    hash            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id              TEXT PRIMARY KEY,
    service         TEXT NOT NULL,
    version         TEXT NOT NULL,
    body            TEXT NOT NULL,
    author          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft', -- draft|canary|active|rolled_back
    canary_percent  INTEGER NOT NULL DEFAULT 0,
    metrics         TEXT NOT NULL DEFAULT '{}',
    UNIQUE(service, version)
);

CREATE TABLE IF NOT EXISTS model_versions (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    weights_hash    TEXT NOT NULL,
    license         TEXT NOT NULL,
    loaded_at       TEXT NOT NULL,
    golden_accuracy REAL,
    status          TEXT NOT NULL DEFAULT 'active'
);

-- append-only: содержит вход/выход каждого вызова LLM (ТЗ 3.4 v1.1)
CREATE TABLE IF NOT EXISTS llm_inference_log (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    service         TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    input_json      TEXT NOT NULL,
    output_json     TEXT NOT NULL,
    confidence      REAL,
    latency_ms      INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    retention_until TEXT NOT NULL              -- >= 12 месяцев, затем холодный архив
);
CREATE INDEX IF NOT EXISTS idx_llm_log_trace ON llm_inference_log(trace_id);

CREATE TABLE IF NOT EXISTS vision_extraction_results (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    mime            TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    quality_score   REAL NOT NULL,
    elements_json   TEXT NOT NULL,
    confidence      REAL NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id              TEXT PRIMARY KEY,
    recipient       TEXT NOT NULL,
    channel         TEXT NOT NULL,                 -- ui|email|messenger
    priority        TEXT NOT NULL,                 -- low|normal|high
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    trace_id        TEXT,
    created_at      TEXT NOT NULL,
    read_at         TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    smeta_id        TEXT NOT NULL,
    version_no      INTEGER NOT NULL,
    fmt             TEXT NOT NULL,                 -- xlsx|pdf|grand_smeta_csv
    path            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    created_by      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_checks (
    id              TEXT PRIMARY KEY,
    checked_at      TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    golden_accuracy REAL NOT NULL,
    baseline        REAL NOT NULL,
    delta_pct       REAL NOT NULL,
    verdict         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_freshness_log (
    id              TEXT PRIMARY KEY,
    run_at          TEXT NOT NULL,
    checked_items   INTEGER NOT NULL,
    updated_items   INTEGER NOT NULL,
    anomalies       INTEGER NOT NULL,
    kb_version      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estimate_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    smeta_id        TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         TEXT NOT NULL,
    actor           TEXT NOT NULL,
    ts              TEXT NOT NULL
);

-- ------------------------- append-only триггеры (ТЗ 5.2, 6.2) ----------------
CREATE TRIGGER IF NOT EXISTS trg_versions_no_update BEFORE UPDATE ON smeta_versions
BEGIN SELECT RAISE(ABORT, 'smeta_versions is immutable: create a new version'); END;
CREATE TRIGGER IF NOT EXISTS trg_versions_no_delete BEFORE DELETE ON smeta_versions
BEGIN SELECT RAISE(ABORT, 'smeta_versions is immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_positions_no_update BEFORE UPDATE ON smeta_positions
BEGIN SELECT RAISE(ABORT, 'positions are immutable: create a new version'); END;
CREATE TRIGGER IF NOT EXISTS trg_positions_no_delete BEFORE DELETE ON smeta_positions
BEGIN SELECT RAISE(ABORT, 'positions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_llm_log_no_update BEFORE UPDATE ON llm_inference_log
BEGIN SELECT RAISE(ABORT, 'llm_inference_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_llm_log_no_delete BEFORE DELETE ON llm_inference_log
BEGIN SELECT RAISE(ABORT, 'llm_inference_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_audit_no_update BEFORE UPDATE ON security_audit_log
BEGIN SELECT RAISE(ABORT, 'security_audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete BEFORE DELETE ON security_audit_log
BEGIN SELECT RAISE(ABORT, 'security_audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_pipeline_no_update BEFORE UPDATE ON pipeline_execution_log
BEGIN SELECT RAISE(ABORT, 'pipeline_execution_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_pipeline_no_delete BEFORE DELETE ON pipeline_execution_log
BEGIN SELECT RAISE(ABORT, 'pipeline_execution_log is append-only'); END;
