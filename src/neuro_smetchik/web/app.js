/* Нейро-сметчик UI — vanilla JS, без внешних зависимостей и сетевых вызовов. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const API = '/api/v1';
const state = { estimate: null, meta: null, prompts: [], lastTrace: null };

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = (v) => new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v || 0));
const shortDate = (s) => (s ? String(s).replace('T', ' ').slice(0, 16) : '—');

function toast(msg, type = '') {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => (t.className = 'toast ' + type), 4200);
}

function headers() {
  const role = $('#roleSelect').value;
  const mfa = $('#mfaToggle').checked || role === 'manager' || role === 'admin';
  return { 'X-User': role === 'manager' ? 'petrova' : role === 'admin' ? 'admin' : role === 'client' ? 'client' : 'ivanov',
           'X-Role': role, 'X-MFA': mfa ? '1' : '0' };
}

async function api(path, { method = 'GET', body = null, form = null } = {}) {
  const opts = { method, headers: { ...headers() } };
  if (body !== null) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  if (form) opts.body = form;
  const resp = await fetch(API + path, opts);
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { const j = await resp.json(); detail = j.detail || detail; } catch (e) { /* ignore */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  const ct = resp.headers.get('content-type') || '';
  return ct.includes('json') ? resp.json() : resp.text();
}

function confBadge(c) {
  const v = Number(c || 0);
  const cls = v >= 0.85 ? 'badge-green' : v >= 0.5 ? 'badge-amber' : 'badge-red';
  return `<span class="badge ${cls} conf-cell" title="Confidence score">${v.toFixed(2)}</span>`;
}
function statusBadge(s) {
  const map = {
    auto_accepted: ['badge-green', 'авто'], needs_review: ['badge-amber', 'проверка'],
    escalated: ['badge-red', 'эскалация'], manual: ['badge-blue', 'вручную'],
    draft: ['badge-gray', 'черновик'], needs_clarification: ['badge-amber', 'нужны уточнения'],
    needs_review_color: ['badge-blue', 'на проверке'], pending_second_approval: ['badge-amber', 'ждём 2-ю подпись'],
    approved: ['badge-green', 'утверждена'], archived: ['badge-gray', 'архив'],
  };
  const [cls, label] = map[s] || ['badge-gray', esc(s)];
  return `<span class="badge ${cls}">${label}</span>`;
}
const levelBadge = (l) => `<span class="badge ${l === 'error' ? 'badge-red' : l === 'warning' ? 'badge-amber' : 'badge-blue'}">${esc(l)}</span>`;

/* ------------------------------------------------------------------ NAV */
const VIEW_META = {
  new: ['Новая смета', 'черновик за ≤60 сек'], estimates: ['Сметы', 'реестр и версии'],
  catalog: ['Каталог расценок', 'гибридный поиск'], notifications: ['Уведомления', 'эскалации и события'],
  monitoring: ['Мониторинг и SLA', 'качество, дрейф, error budget'], prompts: ['Промпты', 'version control и canary'],
  trace: ['Трассировка', 'trace_id по шагам пайплайна'], audit: ['Аудит', 'append-only hash-chain'],
};
function setView(view) {
  $$('.nav-item').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
  $$('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + view));
  $('#viewTitle').textContent = VIEW_META[view][0];
  $('#viewSub').textContent = VIEW_META[view][1];
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (view === 'estimates') loadEstimates();
  if (view === 'notifications') loadNotifications();
  if (view === 'monitoring') loadMetrics();
  if (view === 'prompts') loadPrompts();
  if (view === 'catalog') catalogSearch();
  if (view === 'audit') loadAudit();
  if (view === 'trace' && state.lastTrace) { $('#traceInput').value = state.lastTrace; loadTrace(); }
}
$$('.nav-item').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
$('#roleSelect').addEventListener('change', () => {
  const labels = { client: 'Клиент', estimator: 'Иванов И.И.', manager: 'Петрова А.С.', admin: 'Администратор' };
  $('#userChip').textContent = labels[$('#roleSelect').value];
  $('#mfaToggle').checked = ['manager', 'admin'].includes($('#roleSelect').value);
  loadNotificationsCount();
});

/* --------------------------------------------------------------- HELPERS */
async function loadNotificationsCount() {
  try {
    const d = await api('/notifications?unread_only=true');
    $('#unreadBadge').textContent = d.items.length ? d.items.length : '';
  } catch (e) { /* non-critical */ }
}
function jsonBlock(obj) { return esc(JSON.stringify(obj, null, 2)); }

/* ------------------------------------------------------- GENERATE / FLOW */
$('#generateBtn').addEventListener('click', async () => {
  const text = $('#requestText').value.trim();
  if (text.length < 3) return toast('Опишите объект и работы (минимум 3 символа)', 'error');
  const btn = $('#generateBtn');
  btn.disabled = true; btn.textContent = 'Пайплайн работает…';
  try {
    const est = await api('/requests', { method: 'POST', body: {
      text, client: $('#clientName').value.trim(), source_type: 'text', use_llm_judge: $('#judgeBox').checked,
    }});
    state.estimate = est; state.lastTrace = est.trace_id;
    $('#traceInput').value = est.trace_id;
    renderEstimate(est, '#estimateArea');
    renderClarification(est);
    toast(`Черновик готов: версия v${est.version_no}, ${est.positions.length} позиций`, 'success');
    loadNotificationsCount();
  } catch (e) { toast('Ошибка: ' + e.message, 'error'); }
  finally { btn.disabled = false; btn.textContent = 'Сгенерировать черновик →'; }
});
$$('.chip[data-example]').forEach((c) => c.addEventListener('click', () => { $('#requestText').value = c.dataset.example; }));

$('#visionFile').addEventListener('change', async (ev) => {
  const file = ev.target.files[0]; if (!file) return;
  const form = new FormData(); form.append('file', file);
  try {
    const r = await api('/vision', { method: 'POST', form });
    $('#visionResult').innerHTML = `<div class="issue ${r.degraded_to_manual ? 'warning' : 'info'}">
      <div><strong>Vision/OCR:</strong> качество ${r.quality_score}, confidence ${r.confidence}, элементов: ${r.elements.length}.
      ${r.degraded_to_manual ? 'Включён ручной ввод (низкое качество фото).' : ''}</div></div>`;
    toast('Файл проверен и проанализирован', 'success');
  } catch (e) { toast('Файл отклонён: ' + e.message, 'error'); }
});

function renderClarification(est) {
  const area = $('#clarificationArea');
  const qs = est.questions || (est.question ? [est.question] : []);
  if (!qs.length || !est.clarification_session_id) { area.innerHTML = ''; return; }
  const q = qs[0];
  area.innerHTML = `<div class="card clarify-card">
    <h2>Уточняющий вопрос <span class="pill pill-blue">${q.turn_no || 1} / 5</span></h2>
    <p class="muted">Поле <code>${esc(q.field)}</code> критично для расчёта. Можно пропустить — система продолжит с данными по умолчанию и пометкой для проверки.</p>
    <p class="clarify-q"><strong>${esc(q.question)}</strong></p>
    <div class="row-actions"><input id="clarifyAnswer" type="text" placeholder="Ваш ответ…" style="flex:1;min-width:220px" />
      <button class="btn btn-primary" id="clarifySend">Ответить</button>
      <button class="btn btn-ghost" id="clarifySkip">Пропустить</button></div></div>`;
  const send = async (skip) => {
    try {
      const r = await api(`/clarification/${est.clarification_session_id}/answer`, {
        method: 'POST', body: { answer: $('#clarifyAnswer')?.value || '', skip } });
      if (r.estimate) { state.estimate = r.estimate; renderEstimate(r.estimate, '#estimateArea'); }
      if (r.status === 'open' && r.question) {
        renderClarification({ questions: [r.question], clarification_session_id: r.session_id });
      } else { area.innerHTML = ''; toast('Уточнения учтены, смета пересчитана', 'success'); }
    } catch (e) { toast('Ошибка: ' + e.message, 'error'); }
  };
  $('#clarifySend').addEventListener('click', () => send(false));
  $('#clarifySkip').addEventListener('click', () => send(true));
  $('#clarifyAnswer')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(false); });
}

/* ------------------------------------------------------ ESTIMATE RENDER */
function renderEstimate(est, target) {
  const el = $(target); if (!el) return;
  const t = est.totals || {};
  const counts = { auto: 0, review: 0, escalated: 0, manual: 0 };
  est.positions.forEach((p) => { if (p.status === 'auto_accepted') counts.auto++; else if (p.status === 'escalated') counts.escalated++; else if (p.status === 'manual') counts.manual++; else counts.review++; });
  const issues = est.issues || [];
  const suggestions = est.suggestions || [];
  const steps = est.pipeline_steps || [];
  const escCount = (est.escalations || []).length;
  el.innerHTML = `
  <div class="card" id="estCard">
    <div class="card-head">
      <div><h2>${esc(est.title || est.id)} ${statusBadge(est.status)}</h2>
        <div class="meta-line"><span>ID: <code>${esc(est.id)}</code></span><span>Версия: <strong>v${est.version_no}</strong></span>
        <span>Trace: <code>${esc(est.trace_id)}</code></span><span>Создано: ${shortDate(est.created_at)}</span>
        <span>Контрольная сумма: <code>${esc(String(est.checksum || '').slice(0, 14))}…</code></span></div></div>
      <div class="btn-row">
        <button class="btn btn-ghost btn-sm" id="traceJump">Трассировка</button>
        <button class="btn btn-ghost btn-sm" id="approveBtn">Утвердить</button>
      </div>
    </div>
    <div class="kpi-grid">
      <div class="kpi ok"><div class="k-label">Итого, ₽</div><div class="k-value">${num(t.grand_total)}</div><div class="k-note">в т.ч. НДС ${num(t.vat)} ₽</div></div>
      <div class="kpi"><div class="k-label">Позиций</div><div class="k-value">${est.positions.length}</div><div class="k-note">все ссылаются на price_catalog</div></div>
      <div class="kpi ${counts.escalated ? 'warn' : 'ok'}"><div class="k-label">Требуют проверки</div><div class="k-value">${counts.review + counts.escalated}</div><div class="k-note">авто: ${counts.auto} · эскалация: ${counts.escalated} · вручную: ${counts.manual}</div></div>
      <div class="kpi ${t.verification === 'ok' ? 'ok' : 'bad'}"><div class="k-label">Верификация расчёта</div><div class="k-value" style="font-size:18px">${esc(t.verification || '—')}</div><div class="k-note">независимый пересчёт + ${est.latency_ms || 0} мс</div></div>
    </div>
    ${steps.length ? `<div class="steps-strip">${steps.map((s) => `<span class="step-pill ${['error','failed'].includes(s.status) ? 'error' : s.status.includes('escal') ? 'escalation' : ''}" title="${esc(s.detail || '')}">${esc(s.step)}: ${esc(s.status)}</span>`).join('')}</div>` : ''}
    ${escCount ? `<div class="issue warning"><div>${(est.escalations || []).map((e) => esc(e)).join('<br/>')}</div></div>` : ''}
    <div class="section-split">
      <div>
        <h3>Позиции сметы <span class="muted" style="display:inline;font-weight:400">— редактируйте количество/цену, затем примените правки</span></h3>
        <div class="table-wrap"><table><thead><tr><th>№</th><th>Код / Наименование</th><th>Ед.</th><th class="num">Кол-во</th><th class="num">Цена, ₽</th><th class="num">Итого, ₽</th><th>Confidence</th><th>Статус</th></tr></thead>
        <tbody>${est.positions.map((p, i) => `<tr>
          <td>${i + 1}</td><td><strong>${esc(p.catalog_id)}</strong><br/><span class="muted" style="margin:0">${esc(p.name)}</span>${p.notes ? `<br/><span class="badge badge-amber" style="margin-top:3px">${esc(p.notes)}</span>` : ''}</td>
          <td>${esc(p.unit)}</td>
          <td class="num"><input class="cell-input" data-pid="${esc(p.id)}" data-field="quantity" data-original="${esc(p.quantity)}" value="${esc(p.quantity)}" aria-label="Количество для ${esc(p.name)}" /></td>
          <td class="num"><input class="cell-input" data-pid="${esc(p.id)}" data-field="unit_price" data-original="${esc(p.unit_price)}" value="${esc(p.unit_price)}" aria-label="Цена для ${esc(p.name)}" /></td>
          <td class="num">${num(p.total)}</td><td>${confBadge(p.confidence)}</td><td>${statusBadge(p.status)}</td></tr>`).join('')}</tbody></table></div>
        <div class="row-actions" style="margin-top:12px">
          <button class="btn btn-primary btn-sm" id="applyEdits">Применить правки → новая версия</button>
          <button class="btn btn-ghost btn-sm" id="addSuggestion">Добавить типовую позицию</button>
          <a class="btn btn-ghost btn-sm" href="#docRow">Документы ↓</a>
        </div>
      </div>
      <aside>
        <div class="total-box">
          <div class="total-line"><span class="muted-inline">Сумма без НДС</span><strong>${num(t.subtotal)} ₽</strong></div>
          <div class="total-line"><span class="muted-inline">Накладные расходы</span><strong>${num(t.overhead)} ₽</strong></div>
          <div class="total-line"><span class="muted-inline">Сметная прибыль</span><strong>${num(t.profit)} ₽</strong></div>
          <div class="total-line"><span class="muted-inline">НДС</span><strong>${num(t.vat)} ₽</strong></div>
          <div class="total-line grand"><span>ИТОГО</span><span>${num(t.grand_total)} ₽</span></div>
        </div>
        <h3 style="margin-top:18px">Документы</h3>
        <div class="btn-row" id="docRow">
          <button class="btn btn-ghost btn-sm doc-btn" data-fmt="xlsx">Excel .xlsx</button>
          <button class="btn btn-ghost btn-sm doc-btn" data-fmt="pdf">PDF</button>
          <button class="btn btn-ghost btn-sm doc-btn" data-fmt="csv">Гранд-Смета CSV</button>
        </div>
        <h3 style="margin-top:18px">Замечания валидации (${issues.length})</h3>
        ${issues.length ? issues.slice(0, 12).map((i) => `<div class="issue ${esc(i.level)}"><div>${levelBadge(i.level)} <code>${esc(i.code)}</code><br/>${esc(i.message)}${i.suggestion ? `<br/><em>${esc(i.suggestion)}</em>` : ''}</div></div>`).join('') : '<p class="muted">Замечаний нет.</p>'}
        <h3 style="margin-top:18px">Предложения по полноте (${suggestions.length})</h3>
        ${suggestions.length ? suggestions.map((s) => `<div class="suggestion"><div><strong>${esc(s.catalog_id)}</strong> ${esc(s.name)}<br/><span class="muted" style="margin:0">${esc(s.price)} ₽ / ${esc(s.unit)} · ${esc(s.reason)}</span></div><button class="btn btn-ghost btn-sm add-pos" data-cid="${esc(s.catalog_id)}">+</button></div>`).join('') : '<p class="muted">Пропусков по типовому составу не найдено.</p>'}
        <h3 style="margin-top:18px">Diff версий</h3>
        <div class="row-actions tight">
          <select id="diffFrom" style="width:88px"></select><select id="diffTo" style="width:88px"></select>
          <button class="btn btn-ghost btn-sm" id="diffBtn">Сравнить</button>
        </div>
        <div id="diffResult"></div>
      </aside>
    </div>
  </div>`;
  bindEstimateActions(est, target);
  loadVersionSelects(est);
}

function bindEstimateActions(est, target) {
  const root = $(target);
  $$('.cell-input', root).forEach((inp) => inp.addEventListener('input', () => {
    inp.classList.toggle('changed', inp.value !== inp.dataset.original);
  }));
  $('#applyEdits', root)?.addEventListener('click', async () => {
    const ops = $$('.cell-input.changed', root).map((i) => ({ op: 'update', position_id: i.dataset.pid, field: i.dataset.field, value: i.value }));
    if (!ops.length) return toast('Изменений нет', '');
    await applyOps(est.id, ops, 'Правки количества/цены сметчиком', target);
  });
  $$('.add-pos', root).forEach((b) => b.addEventListener('click', async () => {
    await applyOps(est.id, [{ op: 'add', catalog_id: b.dataset.cid, quantity: 1 }], 'Добавлена типовая позиция из предложений', target);
  }));
  $('#addSuggestion', root)?.addEventListener('click', async () => {
    const cid = (est.suggestions && est.suggestions[0] && est.suggestions[0].catalog_id);
    if (!cid) return toast('Предложений нет', '');
    await applyOps(est.id, [{ op: 'add', catalog_id: cid, quantity: 1 }], 'Добавлена типовая позиция', target);
  });
  $$('.doc-btn', root).forEach((b) => b.addEventListener('click', () => downloadDoc(est, b.dataset.fmt)));
  $('#approveBtn', root)?.addEventListener('click', async () => {
    try {
      const r = await api(`/estimates/${est.id}/approve`, { method: 'POST', body: {} });
      toast(r.status === 'approved' ? 'Смета утверждена' : r.message || 'Ожидается вторая подпись', 'success');
      const fresh = await api(`/estimates/${est.id}`);
      state.estimate = fresh; renderEstimate(fresh, target); loadNotificationsCount();
    } catch (e) { toast('Утверждение: ' + e.message, 'error'); }
  });
  $('#traceJump', root)?.addEventListener('click', () => { state.lastTrace = est.trace_id; $('#traceInput').value = est.trace_id; setView('trace'); });
  $('#diffBtn', root)?.addEventListener('click', async () => {
    const from = $('#diffFrom', root).value, to = $('#diffTo', root).value;
    try {
      const d = await api(`/estimates/${est.id}/diff?from_version=${from}&to_version=${to}`);
      $('#diffResult', root).innerHTML = `<div class="diff-box">
        <div class="diff-col"><h4>Добавлено (${d.added.length})</h4>${d.added.map((x) => `<div class="diff-item">+ ${esc(x.name)}</div>`).join('') || '<div class="muted">—</div>'}</div>
        <div class="diff-col"><h4>Удалено (${d.removed.length})</h4>${d.removed.map((x) => `<div class="diff-item">− ${esc(x.name)}</div>`).join('') || '<div class="muted">—</div>'}</div>
        <div class="diff-col"><h4>Изменено (${d.changed.length})</h4>${d.changed.map((x) => `<div class="diff-item">~ ${esc(x.name)}: ${Object.keys(x.changes).join(', ')}</div>`).join('') || '<div class="muted">—</div>'}</div></div>
        <p class="muted" style="margin-top:8px">Итого: ${esc(d.totals.from)} → ${esc(d.totals.to)} ₽ (Δ ${esc(d.totals.delta)})</p>`;
    } catch (e) { toast('Diff: ' + e.message, 'error'); }
  });
}

async function loadVersionSelects(est) {
  try {
    const d = await api(`/estimates/${est.id}/versions`);
    ['#diffFrom', '#diffTo'].forEach((sel) => {
      const e = $(sel); if (!e) return;
      e.innerHTML = d.items.map((v) => `<option value="${v.version_no}">v${v.version_no}</option>`).join('');
    });
    const to = $('#diffTo'), from = $('#diffFrom');
    if (to && d.items.length) to.value = String(d.items[d.items.length - 1].version_no);
    if (from && d.items.length > 1) from.value = String(d.items[d.items.length - 2].version_no);
  } catch (e) { /* ignore */ }
}

async function applyOps(id, ops, reason, target) {
  try {
    const fresh = await api(`/estimates/${id}/revisions`, { method: 'POST', body: { operations: ops, reason } });
    state.estimate = fresh;
    renderEstimate(fresh, target);
    toast(`Создана версия v${fresh.version_no}: применено операций ${fresh.applied_operations?.filter((o) => o.ok).length || 0}`, 'success');
    return fresh;
  } catch (e) { toast('Правка: ' + e.message, 'error'); }
}

async function downloadDoc(est, fmt) {
  try {
    const resp = await fetch(`${API}/estimates/${est.id}/documents/${fmt}`, { headers: headers() });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const cd = resp.headers.get('content-disposition') || '';
    const name = (cd.match(/filename="?([^"]+)"?/) || [])[1] || `${est.id}_v${est.version_no}.${fmt}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    toast(`Документ ${name} сформирован`, 'success');
  } catch (e) { toast('Документ: ' + e.message, 'error'); }
}

/* ------------------------------------------------------------- ESTIMATES */
async function loadEstimates() {
  const box = $('#estimatesList'); box.innerHTML = '<p class="muted">Загрузка…</p>';
  try {
    const d = await api('/estimates');
    if (!d.items.length) { box.innerHTML = '<div class="empty">Смет пока нет. Создайте черновик на вкладке «Новая смета».</div>'; return; }
    box.innerHTML = `<table><thead><tr><th>ID / Объект</th><th>Статус</th><th>Версия</th><th class="num">Итого, ₽</th><th>Обновлена</th></tr></thead>
      <tbody>${d.items.map((e) => `<tr class="link-row" data-id="${esc(e.id)}"><td><strong>${esc(e.title)}</strong><br/><span class="muted" style="margin:0"><code>${esc(e.id)}</code></span></td>
      <td>${statusBadge(e.status)}</td><td>v${e.current_version}</td><td class="num">${num(e.grand_total)}</td><td>${shortDate(e.updated_at)}</td></tr>`).join('')}</tbody></table>`;
    $$('.link-row', box).forEach((tr) => tr.addEventListener('click', async () => {
      try { const est = await api(`/estimates/${tr.dataset.id}`); state.estimate = est; renderEstimate(est, '#estimateArea2'); $('#estimateArea2').scrollIntoView({ behavior: 'smooth' }); }
      catch (e) { toast(e.message, 'error'); }
    }));
  } catch (e) { box.innerHTML = `<div class="empty">Ошибка: ${esc(e.message)}</div>`; }
}
$('#refreshEstimates').addEventListener('click', loadEstimates);

/* --------------------------------------------------------------- CATALOG */
async function catalogSearch() {
  const q = $('#catalogQuery').value.trim(); if (q.length < 2) return;
  try {
    const d = await api(`/catalog/search?q=${encodeURIComponent(q)}&limit=10`);
    $('#catalogResults').innerHTML = `<p class="muted">Найдено ${d.results.length} · ${d.latency_ms} мс · SLA ${d.sla_ms} мс → ${d.within_sla ? '<strong style="color:var(--green)">в норме</strong>' : '<strong style="color:var(--red)">превышение</strong>'}</p>
      <table><thead><tr><th>Код</th><th>Наименование</th><th>Категория</th><th>Ед.</th><th class="num">Цена, ₽</th><th class="num">Score</th><th class="num">Semantic</th><th class="num">Keyword</th></tr></thead>
      <tbody>${d.results.map((r) => `<tr><td><strong>${esc(r.catalog_id)}</strong></td><td>${esc(r.name)}</td><td>${esc(r.category)}</td><td>${esc(r.unit)}</td><td class="num">${num(r.price)}</td><td class="num"><strong>${r.score.toFixed(3)}</strong></td><td class="num">${r.semantic_score.toFixed(3)}</td><td class="num">${r.keyword_score.toFixed(3)}</td></tr>`).join('')}</tbody></table>`;
  } catch (e) { toast('Поиск: ' + e.message, 'error'); }
}
$('#catalogSearchBtn').addEventListener('click', catalogSearch);
$('#catalogQuery').addEventListener('keydown', (e) => { if (e.key === 'Enter') catalogSearch(); });
async function freshness() {
  try { const d = await api('/admin/freshness', { method: 'POST', body: {} }); toast(`Актуальность: проверено ${d.checked_items}, аномалий ${d.anomalies}`, 'success'); return d; }
  catch (e) { toast('Freshness: ' + e.message, 'error'); }
}
$('#freshnessBtn').addEventListener('click', freshness);
$('#freshnessBtn2').addEventListener('click', async () => { const d = await freshness(); if (d) $('#qualityReport').textContent = JSON.stringify(d, null, 2); });

/* --------------------------------------------------------- NOTIFICATIONS */
async function loadNotifications() {
  const box = $('#notificationsList'); box.innerHTML = '<p class="muted">Загрузка…</p>';
  try {
    const d = await api('/notifications');
    if (!d.items.length) { box.innerHTML = '<div class="empty">Уведомлений пока нет.</div>'; return; }
    box.innerHTML = d.items.map((n) => `<div class="notif ${n.priority} ${n.read_at ? '' : 'unread'}" data-id="${esc(n.id)}">
      <div class="n-dot"></div><div style="flex:1"><div class="n-subject">${esc(n.subject)} <span class="badge badge-gray">${esc(n.channel)}</span> ${n.priority === 'high' ? '<span class="badge badge-red">высокий</span>' : ''}</div>
      <div class="n-body">${esc(n.body)}</div><div class="n-meta">${shortDate(n.created_at)} · ${esc(n.recipient)} · trace ${esc(n.trace_id || '—')}</div></div>
      ${n.read_at ? '' : `<button class="btn btn-ghost btn-sm read-btn" data-id="${esc(n.id)}">Прочитано</button>`}</div>`).join('');
    $$('.read-btn', box).forEach((b) => b.addEventListener('click', async () => {
      await api(`/notifications/${b.dataset.id}/read`, { method: 'POST', body: {} }); loadNotifications(); loadNotificationsCount();
    }));
    loadNotificationsCount();
  } catch (e) { box.innerHTML = `<div class="empty">Ошибка: ${esc(e.message)}</div>`; }
}
$('#refreshNotifications').addEventListener('click', loadNotifications);

/* ------------------------------------------------------------ MONITORING */
async function loadMetrics() {
  try {
    const m = await api('/metrics');
    $('#kpiGrid').innerHTML = `
      <div class="kpi"><div class="k-label">Смет / версий</div><div class="k-value">${m.smetas} / ${m.versions}</div><div class="k-note">immutable-история</div></div>
      <div class="kpi"><div class="k-label">Позиций в сметах</div><div class="k-value">${m.positions}</div><div class="k-note">все связаны с каталогом</div></div>
      <div class="kpi ${m.auto_accept_rate >= 0.6 ? 'ok' : 'warn'}"><div class="k-label">Авто-принятие</div><div class="k-value">${(m.auto_accept_rate * 100).toFixed(1)}%</div><div class="k-note">эскалаций: ${(m.escalation_rate * 100).toFixed(1)}%</div></div>
      <div class="kpi ${m.error_rate_pct <= 1 ? 'ok' : 'bad'}"><div class="k-label">Error budget</div><div class="k-value">${m.error_rate_pct}%</div><div class="k-note">лимит: 1% технических ошибок</div></div>
      <div class="kpi ${m.security.audit_chain_valid ? 'ok' : 'bad'}"><div class="k-label">Аудит</div><div class="k-value" style="font-size:18px">${m.security.audit_chain_valid ? 'целостен' : 'НАРУШЕН'}</div><div class="k-note">${m.security.audit_entries} записей · инъекций: ${m.security.prompt_injection_patterns}</div></div>
      <div class="kpi ${m.llm.egress_allowed ? 'bad' : 'ok'}"><div class="k-label">Локальность</div><div class="k-value" style="font-size:18px">${m.llm.egress_allowed ? 'НАРУШЕНА' : 'on-premise'}</div><div class="k-note">${m.llm.enabled ? 'LLM ' + esc(m.llm.model) : 'детерминированный fallback'}</div></div>`;
    const s = m.sla;
    $('#slaTable').innerHTML = `<table><thead><tr><th>Метрика</th><th>Цель</th><th>Факт</th></tr></thead><tbody>
      <tr><td>Генерация черновика, p95</td><td>≤ ${s.draft_p95_ms} мс</td><td>${m.draft_p95_ms} мс</td></tr>
      <tr><td>Search Service, p95</td><td>≤ ${s.search_p95_ms} мс</td><td>${m.search_p95_ms} мс</td></tr>
      <tr><td>Технические ошибки</td><td>≤ ${s.error_budget_pct}%</td><td>${m.error_rate_pct}%</td></tr>
      <tr><td>Доступность (пилот / прод)</td><td>≥ ${s.availability_pilot}% / ${s.availability_prod}%</td><td>мониторинг</td></tr>
      <tr><td>RPO / RTO</td><td>≤ ${s.rpo_h} ч / ${s.rto_h} ч</td><td>политика backup</td></tr>
      <tr><td>Notification Service</td><td>≤ ${s.notification_s} с</td><td>синхронно в журнале</td></tr>
      <tr><td>Позиций каталога</td><td>покрытие категорий</td><td>${m.catalog.items} / ${Object.keys(m.catalog.by_category).length} кат.</td></tr></tbody></table>`;
    $('#loopsList').innerHTML = m.loops.map((l) => `<div class="loop-item"><div><strong>${esc(l.name)}</strong><br/><span class="muted" style="margin:0">${esc(l.period)}</span></div><span class="badge ${l.status === 'active' ? 'badge-green' : 'badge-amber'}">${esc(l.status)}</span></div>`).join('');
  } catch (e) { toast('Метрики: ' + e.message, 'error'); }
}
$('#goldenBtn').addEventListener('click', async () => {
  const box = $('#qualityReport'); box.textContent = 'Выполняется прогон на golden set (122 запроса)…';
  try { const r = await api('/admin/golden', { method: 'POST', body: {} }); box.textContent = JSON.stringify(r, null, 2); toast(r.pass ? 'Регрессия в норме' : 'Обнаружена регрессия качества', r.pass ? 'success' : 'error'); }
  catch (e) { box.textContent = 'Ошибка: ' + e.message; toast(e.message, 'error'); }
});
$('#driftBtn').addEventListener('click', async () => {
  try { const r = await api('/admin/drift', { method: 'POST', body: {} }); $('#qualityReport').textContent = JSON.stringify(r, null, 2); toast('Drift: ' + r.verdict, r.verdict === 'degraded' ? 'error' : 'success'); }
  catch (e) { toast(e.message, 'error'); }
});
$('#planFactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try { const id = $('#pfEstimate').value.trim(); const r = await api(`/estimates/${id}/plan-fact`, { method: 'POST', body: { fact_total: $('#pfFact').value } }); $('#qualityReport').textContent = JSON.stringify(r, null, 2); toast('План/факт записан', 'success'); }
  catch (err) { toast(err.message, 'error'); }
});
$('#feedbackForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try { const id = $('#fbEstimate').value.trim(); const r = await api(`/estimates/${id}/feedback`, { method: 'POST', body: { rating: Number($('#fbRating').value), comment: $('#fbComment')?.value || 'из интерфейса' } }); $('#qualityReport').textContent = JSON.stringify(r, null, 2); toast('Отзыв сохранён', 'success'); }
  catch (err) { toast(err.message, 'error'); }
});

/* --------------------------------------------------------------- PROMPTS */
async function loadPrompts() {
  const box = $('#promptsList');
  try {
    const d = await api('/prompts'); state.prompts = d.items;
    box.innerHTML = `<p class="muted">Активные версии: ${Object.entries(d.active).map(([k, v]) => `<code>${esc(k)}: ${esc(v)}</code>`).join(' · ')}</p>
      <table><thead><tr><th>Сервис</th><th>Версия</th><th>Статус</th><th>Canary</th><th>Автор</th><th>Создана</th><th>Размер</th></tr></thead>
      <tbody>${d.items.map((p) => `<tr><td><strong>${esc(p.service)}</strong></td><td>${esc(p.version)}</td><td>${statusBadge(p.status === 'active' ? 'approved' : p.status === 'canary' ? 'needs_review' : 'draft')}</td><td>${p.canary_percent}%</td><td>${esc(p.author)}</td><td>${shortDate(p.created_at)}</td><td>${p.body_len} симв.</td></tr>`).join('')}</tbody></table>`;
  } catch (e) { box.innerHTML = `<div class="empty">Ошибка: ${esc(e.message)}</div>`; }
}
$('#refreshPrompts').addEventListener('click', loadPrompts);
$('#promptForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = $('#promptBody').value.trim();
  if (body.length < 20) return toast('Введите тело промпта (≥20 символов)', 'error');
  try { await api('/prompts', { method: 'POST', body: { service: $('#promptService').value, body, author: $('#roleSelect').value, canary_percent: Number($('#promptCanary').value), activate: $('#promptActivate').checked } }); toast('Версия промпта создана', 'success'); $('#promptBody').value = ''; loadPrompts(); }
  catch (err) { toast(err.message, 'error'); }
});
$('#activateBtn').addEventListener('click', async () => {
  try { await api('/prompts/activate', { method: 'POST', body: { service: $('#paService').value, version: $('#paVersion').value.trim() } }); toast('Версия активирована (откат без деплоя)', 'success'); loadPrompts(); }
  catch (e) { toast(e.message, 'error'); }
});
$('#canaryBtn').addEventListener('click', async () => {
  try { await api('/prompts/canary', { method: 'POST', body: { service: $('#paService').value, version: $('#paVersion').value.trim(), canary_percent: 25 } }); toast('Canary 25% включён', 'success'); loadPrompts(); }
  catch (e) { toast(e.message, 'error'); }
});

/* ---------------------------------------------------------------- TRACE */
async function loadTrace() {
  const id = $('#traceInput').value.trim(); if (!id) return toast('Введите trace_id', 'error');
  state.lastTrace = id;
  try {
    const d = await api('/admin/trace/' + encodeURIComponent(id));
    $('#traceResult').innerHTML = `<p class="muted">Шагов: ${d.step_count} · LLM-вызовов: ${d.llm_calls}</p>
      <div class="table-wrap"><table><thead><tr><th>Шаг</th><th>Попытка</th><th>Статус</th><th class="num">мс</th><th>Промпт</th><th>Модель</th><th>Ошибка</th></tr></thead>
      <tbody>${d.steps.map((s) => `<tr><td><strong>${esc(s.step)}</strong></td><td>${s.attempt}</td><td>${statusBadge(s.status === 'ok' ? 'approved' : s.status.includes('error') ? 'escalated' : 'draft')}</td><td class="num">${s.duration_ms}</td><td>${esc(s.prompt_version || '—')}</td><td>${esc(s.model_version || '—')}</td><td>${esc(s.error || '—')}</td></tr>`).join('')}</tbody></table></div>
      <h3 style="margin-top:16px">LLM inference log (append-only, ≥12 месяцев)</h3>
      <div class="pre-box">${jsonBlock(d.llm_inference_log.slice(0, 12))}</div>`;
  } catch (e) { $('#traceResult').innerHTML = `<div class="empty">Ошибка: ${esc(e.message)}</div>`; }
}
$('#traceBtn').addEventListener('click', loadTrace);

/* ---------------------------------------------------------------- AUDIT */
async function loadAudit() {
  const box = $('#auditResult');
  try {
    const d = await api('/admin/audit');
    box.innerHTML = `<div class="issue ${d.chain_valid ? 'info' : 'error'}"><div><strong>Хэш-цепочка: ${d.chain_valid ? 'целостна' : 'НАРУШЕНА'}</strong> · записей: ${d.chain_length}</div></div>
      <div class="table-wrap"><table><thead><tr><th>Время</th><th>Актёр</th><th>Роль</th><th>Действие</th><th>Объект</th><th>Важность</th><th>Hash</th></tr></thead>
      <tbody>${d.items.map((r) => `<tr><td>${shortDate(r.ts)}</td><td>${esc(r.actor)}</td><td>${esc(r.role)}</td><td><strong>${esc(r.action)}</strong></td><td>${esc(r.entity)}:${esc(r.entity_id || '')}</td><td>${esc(r.severity)}</td><td><code>${esc(String(r.hash).slice(0, 12))}…</code></td></tr>`).join('')}</tbody></table></div>`;
  } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)} — переключите роль на «Руководитель»/«Администратор» с MFA.</div>`; }
}
$('#refreshAudit').addEventListener('click', loadAudit);

/* ---------------------------------------------------------------- START */
(async function init() {
  try {
    state.meta = await api('/meta');
    $('#catalogCount').textContent = (await api('/health')).catalog_items + ' позиций';
  } catch (e) { toast('Сервис недоступен: ' + e.message, 'error'); }
  $('#mfaToggle').checked = false;
  loadNotificationsCount();
  loadMetrics();
})();
