// ============================================================
// REPORTS
// ============================================================

let _activeSessionId   = null;
let _activeSessionData = null;   // full response from get_session_details
let _emailModalReports = null;   // [{lap_id, name, email, html}] built when modal opens

// ── View navigation ──────────────────────────────────────────

function reportsBack() {
  const detailVisible = document.getElementById('reports-detail-view').style.display !== 'none';
  if (detailVisible) {
    _showListView();
  } else {
    goTo('home-screen');
  }
}

function _showListView() {
  document.getElementById('reports-list-view').style.display   = '';
  document.getElementById('reports-detail-view').style.display = 'none';
  document.getElementById('reports-back-label').textContent    = 'Home';
  document.getElementById('reports-refresh-btn').style.display = '';
}

function _showDetailView() {
  document.getElementById('reports-list-view').style.display   = 'none';
  document.getElementById('reports-detail-view').style.display = '';
  document.getElementById('reports-back-label').textContent    = 'All Sessions';
  document.getElementById('reports-refresh-btn').style.display = 'none';
}

// ── Session list ─────────────────────────────────────────────

async function loadSessions() {
  _showListView();
  const listEl = document.getElementById('sessions-list');
  listEl.innerHTML = '<div style="color:var(--muted);font-size:15px;padding:6px 0">Loading…</div>';

  const r = await pywebview.api.list_completed_sessions();
  if (!r.ok) {
    listEl.innerHTML =
      `<div style="color:var(--danger);font-size:15px;padding:6px 0">${r.msg || 'Failed to load sessions.'}</div>`;
    return;
  }
  if (!r.sessions || !r.sessions.length) {
    listEl.innerHTML =
      '<div style="color:var(--muted);font-size:15px;padding:6px 0">'
      + 'No completed workout sessions found. Finish a workout to generate reports.'
      + '</div>';
    return;
  }

  listEl.innerHTML = r.sessions.map(s => {
    const date  = _fmtDate(s.started_at);
    const wk    = s.workout;
    const wkStr = wk
      ? `${wk.interval_distance} m&nbsp;&nbsp;·&nbsp;&nbsp;${wk.rest_time} s rest`
      : 'Unknown workout';
    const n = s.athletes_with_data;
    return `
      <div class="session-item">
        <div class="session-item-main">
          <div class="session-dot"></div>
          <div class="session-info">
            <div class="session-date">${date}</div>
            <div class="session-meta">${wkStr}&nbsp;&nbsp;·&nbsp;&nbsp;${n} athlete${n !== 1 ? 's' : ''}</div>
          </div>
        </div>
        <div class="session-actions">
          <button class="session-open-btn"
                  type="button"
                  onclick="openSession('${_esc(s.session_id)}')">
            View Details <span class="session-open-btn-arrow">›</span>
          </button>
          <button class="session-delete-btn"
                type="button"
                title="Delete session"
                aria-label="Delete session"
                data-session-id="${_esc(s.session_id)}"
                data-session-date="${_esc(date)}"
                data-workout-label="${_esc(wkStr.replace(/&nbsp;/g, ' '))}"
                onclick="deleteSessionFromButton(event, this)">
            <span class="session-delete-icon" aria-hidden="true">✖</span>
          </button>
        </div>
      </div>`;
  }).join('');
}

async function deleteSessionFromButton(event, btn) {
  const { sessionId, sessionDate, workoutLabel } = btn.dataset;
  await deleteSession(event, sessionId, sessionDate, workoutLabel);
}

async function deleteSession(event, sessionId, sessionDate, workoutLabel) {
  if (event) event.stopPropagation();

  if (!await showConfirm(
    `${workoutLabel}\n\nThis cannot be undone.`,
    { title: `Delete session from ${sessionDate}?`, confirmText: 'Delete' }
  )) return;

  try {
    const result = await pywebview.api.delete_completed_session(sessionId);
    log(result.msg || (result.ok ? 'Workout session deleted.' : 'Failed to delete session.'), result.ok ? 'ok' : 'err');
    if (result.ok) {
      if (_activeSessionId === sessionId) {
        _activeSessionId = null;
        _activeSessionData = null;
      }
      await loadSessions();
    }
  } catch (e) {
    log(`Error deleting session: ${e.message}`, 'err');
  }
}

// ── Session detail ────────────────────────────────────────────

async function openSession(sessionId) {
  _activeSessionId = sessionId;
  _showDetailView();

  document.getElementById('detail-session-date').textContent     = 'Loading…';
  document.getElementById('detail-session-subtitle').textContent = '';
  document.getElementById('detail-workout-info').innerHTML       = '';
  document.getElementById('detail-athletes-accordion').innerHTML = '';
  document.getElementById('report-files').innerHTML              = '';
  document.getElementById('report-select-all').checked           = false;
  _activeSessionData = null;
  _updateGenerateBtn();

  const r = await pywebview.api.get_session_details(sessionId);
  if (!r.ok) {
    log(r.msg || 'Failed to load session.', 'err');
    _showListView();
    return;
  }
  _activeSessionData = r;
  _renderDetail(r);
}

function _renderDetail(data) {
  document.getElementById('detail-session-date').textContent = _fmtDate(data.started_at);

  const wk = data.workout || {};
  document.getElementById('detail-workout-info').innerHTML = `
    <div class="stat-box">
      <div class="stat-val">${wk.interval_distance ?? '—'}</div>
      <div class="stat-label">Distance (m)</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">${wk.rest_time ?? '—'}</div>
      <div class="stat-label">Rest Time (s)</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">${data.athletes.length}</div>
      <div class="stat-label">Athletes</div>
    </div>`;

  const accordion = document.getElementById('detail-athletes-accordion');
  if (!data.athletes || !data.athletes.length) {
    accordion.innerHTML =
      '<div style="color:var(--muted);padding:8px 0">No athletes with completed intervals.</div>';
    return;
  }
  accordion.innerHTML = data.athletes.map((a, idx) => _buildAthletePanel(a, wk, idx)).join('');
}

// ── Athlete accordion panel ───────────────────────────────────

function _buildAthletePanel(a, wk, idx) {
  const id       = _safeId(a.lap_id || `${a.name}_${a.lname}`);
  const fullName = `${a.name} ${a.lname}`.trim();
  const n        = a.intervals_ms.length;

  // Slowdown %
  const slowdown    = _calcSlowdown(a.intervals_ms);
  const slowdownStr = slowdown !== null
    ? `${slowdown >= 0 ? '+' : ''}${slowdown.toFixed(1)}%`
    : '—';
  const slowdownColor = slowdown === null ? 'var(--muted)'
    : slowdown > 10                       ? 'var(--danger)'
    : slowdown > 5                        ? 'var(--warning)'
    :                                       'var(--success)';

  // Slowdown pill only when we have data
  const slowdownPill = slowdown !== null
    ? `<span class="acc-pill" style="color:${slowdownColor};border-color:${slowdownColor}">${slowdownStr}&thinsp;slowdown</span>`
    : '';

  // Interval + rest rows
  let rows = '';
  for (let i = 0; i < n; i++) {
    const iv   = a.intervals_ms[i];
    const rest = a.rests_ms[i];
    rows += `<tr>
      <td class="acc-td-num">${i + 1}</td>
      <td class="acc-td-dur">${_fmtMs(iv)}</td>
      <td class="acc-td-rest">${rest !== undefined ? _fmtMs(rest) : '<span style="color:var(--muted)">—</span>'}</td>
    </tr>`;
  }

  const chart = _buildFatigueCurve(a.intervals_ms);

  return `
<div class="acc-item" id="acc-${id}">

  <div class="acc-header" onclick="toggleAthletePanel('${id}')">
    <span class="acc-arrow" id="acc-arrow-${id}">▶</span>
    <span class="acc-name">${fullName}</span>
    <div class="acc-header-pills">
      <span class="acc-pill">${n}&thinsp;interval${n !== 1 ? 's' : ''}</span>
      <span class="acc-pill acc-pill-accent">${_fmtMs(a.avg_pace_ms)}&thinsp;/&thinsp;1600&thinsp;m</span>
      ${slowdownPill}
    </div>
    <label class="acc-cb-label" onclick="event.stopPropagation()">
      <input type="checkbox" class="athlete-report-cb"
             data-id="${_esc(a.lap_id)}" onchange="_updateGenerateBtn()"/>
      <span class="acc-cb-text">Export</span>
    </label>
  </div>

  <div class="acc-body" id="acc-body-${id}">

    <!-- Workout parameters strip -->
    <div class="acc-params-strip">
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.interval_distance ?? '—'}&thinsp;m</div>
        <div class="acc-param-label">per interval</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.rest_time ?? '—'}&thinsp;s</div>
        <div class="acc-param-label">rest time</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${n}</div>
        <div class="acc-param-label">completed</div>
      </div>
    </div>

    <!-- Interval data table (left) + performance stats (right) -->
    <div class="acc-middle-row">
      <div class="acc-table-col">
        <div class="acc-col-label">Interval Data</div>
        <table class="acc-table">
          <thead><tr>
            <th class="acc-th-num">#</th>
            <th>Duration</th>
            <th>Rest After</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="acc-stats-col">
        <div class="acc-col-label">Performance</div>
        <div class="acc-stat-card">
          <div class="acc-stat-val">${_fmtMs(a.avg_pace_ms)}</div>
          <div class="acc-stat-label">Avg Pace / 1600 m</div>
        </div>
        <div class="acc-stat-card">
          <div class="acc-stat-val" style="color:${slowdownColor}">${slowdownStr}</div>
          <div class="acc-stat-label">Slowdown (1st → last interval)</div>
        </div>
      </div>
    </div>

    <!-- Full-width fatigue curve -->
    <div class="acc-chart-section">
      <div class="acc-col-label">Fatigue Curve</div>
      ${chart}
      <div class="acc-chart-xlabel">Interval Number</div>
    </div>

  </div>
</div>`;
}

function toggleAthletePanel(id) {
  const body  = document.getElementById(`acc-body-${id}`);
  const arrow = document.getElementById(`acc-arrow-${id}`);
  const open  = body.classList.toggle('open');
  arrow.textContent = open ? '▼' : '▶';
}

// ── Analytics helpers ─────────────────────────────────────────

function _calcSlowdown(intervals_ms) {
  if (!intervals_ms || intervals_ms.length < 2) return null;
  const first = intervals_ms[0];
  const last  = intervals_ms[intervals_ms.length - 1];
  if (!first) return null;
  return ((last - first) / first) * 100;
}

function _buildFatigueCurve(intervals_ms) {
  if (!intervals_ms || intervals_ms.length < 2) {
    return '<p style="color:var(--muted);font-size:13px;margin:8px 0">Need at least 2 intervals to draw chart.</p>';
  }

  // SVG coordinate space (responsive: width driven by CSS, height fixed via aspect-ratio)
  const W = 760, H = 220;
  const ml = 72, mr = 20, mt = 20, mb = 44;
  const pw = W - ml - mr;
  const ph = H - mt - mb;
  const n  = intervals_ms.length;

  const minMs = Math.min(...intervals_ms);
  const maxMs = Math.max(...intervals_ms);

  // Pad y-range so dots don't clip at the edges
  const pad  = (maxMs - minMs) * 0.12 || 2000;
  const yLo  = minMs - pad;
  const yHi  = maxMs + pad;
  const span = yHi - yLo;

  const toX = i  => ml + (n === 1 ? pw / 2 : (i / (n - 1)) * pw);
  const toY = ms => mt + ((yHi - ms) / span) * ph;

  const pts = intervals_ms.map((ms, i) => [toX(i), toY(ms)]);

  // 5 y-axis ticks covering the actual data range (not the padded range)
  const dataRange = maxMs - minMs || 1;
  const yTicks = maxMs === minMs
    ? [maxMs]
    : [0, 0.25, 0.5, 0.75, 1].map(t => maxMs - t * dataRange);

  // X-axis tick stride (keep readable at any interval count)
  const stride = n <= 10 ? 1 : Math.ceil(n / 10);

  // Smooth bezier path through the data points
  const linePath = _smoothPath(pts);
  const areaPath = linePath
    + ` L ${f(pts[n - 1][0])},${f(mt + ph)}`
    + ` L ${f(pts[0][0])},${f(mt + ph)} Z`;

  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" class="fatigue-chart">`;

  // Horizontal grid lines
  yTicks.forEach(ms => {
    const y = f(toY(ms));
    s += `<line x1="${ml}" y1="${y}" x2="${ml + pw}" y2="${y}" class="chart-grid"/>`;
  });

  // Axes
  s += `<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt + ph}" class="chart-axis"/>`;
  s += `<line x1="${ml}" y1="${mt + ph}" x2="${ml + pw}" y2="${mt + ph}" class="chart-axis"/>`;

  // Y-axis labels
  yTicks.forEach(ms => {
    s += `<text x="${ml - 8}" y="${f(toY(ms) + 4)}" class="chart-label chart-label-y">${_fmtMs(ms)}</text>`;
  });

  // X-axis labels (interval numbers)
  pts.forEach(([x], i) => {
    if (i % stride === 0 || i === n - 1) {
      s += `<text x="${f(x)}" y="${f(mt + ph + 20)}" class="chart-label chart-label-x">${i + 1}</text>`;
    }
  });

  // Area fill, smooth line, data-point dots
  s += `<path d="${areaPath}" class="chart-area"/>`;
  s += `<path d="${linePath}" class="chart-line"/>`;

  pts.forEach(([x, y]) => {
    s += `<circle cx="${f(x)}" cy="${f(y)}" r="4" class="chart-dot"/>`;
  });

  s += '</svg>';
  return s;
}

/**
 * Smooth cubic-bezier path through an array of [x,y] points.
 * Uses midpoint control points to produce a gentle S-curve between segments.
 */
function _smoothPath(pts) {
  if (pts.length < 2) return `M ${f(pts[0][0])},${f(pts[0][1])}`;
  let d = `M ${f(pts[0][0])},${f(pts[0][1])}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1];
    const [x1, y1] = pts[i];
    const cx = (x0 + x1) / 2;
    d += ` C ${f(cx)},${f(y0)} ${f(cx)},${f(y1)} ${f(x1)},${f(y1)}`;
  }
  return d;
}

function f(n) { return n.toFixed(1); }

// ── Athlete selection ─────────────────────────────────────────

function toggleSelectAllAthletes(cb) {
  document.querySelectorAll('.athlete-report-cb').forEach(c => { c.checked = cb.checked; });
  _updateGenerateBtn();
}

function _getSelectedIds() {
  return Array.from(document.querySelectorAll('.athlete-report-cb:checked'))
    .map(c => c.dataset.id);
}

function _updateGenerateBtn() {
  const selected = _getSelectedIds();
  const dir      = document.getElementById('report-dir').value.trim();
  const ok       = selected.length > 0 && !!dir;
  document.getElementById('generate-reports-btn').disabled = !ok;
  document.getElementById('email-reports-btn').disabled    = selected.length === 0;

  const hint = document.getElementById('generate-reports-hint');
  if (!dir && !selected.length)  hint.textContent = 'Select athletes and an output directory';
  else if (!dir)                 hint.textContent = 'Choose an output directory';
  else if (!selected.length)     hint.textContent = 'Select at least one athlete';
  else hint.textContent = `${selected.length} athlete${selected.length !== 1 ? 's' : ''} selected`;
}

// ── Export ────────────────────────────────────────────────────

async function pickReportDir() {
  const r = await pywebview.api.pick_directory();
  if (r && r.path) {
    document.getElementById('report-dir').value = r.path;
    const disp = document.getElementById('report-dir-display');
    disp.textContent = r.path;
    disp.style.color = 'var(--text)';
    _updateGenerateBtn();
  }
}

// CSS is fetched once and cached for the session
let _cssCache = null;
async function _loadCss() {
  if (_cssCache) return _cssCache;
  const [shared, idx] = await Promise.all([
    fetch('./css/shared.css').then(r => r.text()),
    fetch('./css/index.css').then(r => r.text()),
  ]);
  _cssCache = shared + '\n' + idx;
  return _cssCache;
}

async function exportHtmlReports() {
  const selectedIds = _getSelectedIds();
  const dir         = document.getElementById('report-dir').value.trim();
  if (!_activeSessionId || !selectedIds.length || !dir) return;

  const btn = document.getElementById('generate-reports-btn');
  btn.disabled    = true;
  btn.textContent = 'Exporting…';

  const [r, css] = await Promise.all([
    pywebview.api.get_session_details(_activeSessionId),
    _loadCss(),
  ]);

  if (!r.ok) {
    log(r.msg || 'Failed to load session.', 'err');
    btn.textContent = 'Export HTML Reports';
    _updateGenerateBtn();
    return;
  }

  const wk          = r.workout || {};
  const sessionDate = _fmtDate(r.started_at);
  const baseDir     = dir.replace(/\/+$/, '');
  const selected    = r.athletes.filter(a => selectedIds.includes(a.lap_id));

  const files = selected.map(a => {
    const safe = `${a.name}_${a.lname}`.replace(/[^a-zA-Z0-9_-]/g, '_');
    return {
      path:    `${baseDir}/${safe}_report.html`,
      content: _buildStandaloneHtml(a, wk, sessionDate, css),
    };
  });

  const result = await pywebview.api.write_files(files);

  btn.textContent = 'Export HTML Reports';
  _updateGenerateBtn();
  log(result.msg || (result.ok ? 'Done.' : 'Export failed.'), result.ok ? 'ok' : 'err');

  const filesEl = document.getElementById('report-files');
  if (result.ok && result.files && result.files.length) {
    filesEl.innerHTML =
      '<div class="card"><div class="card-title">Exported Files</div>'
      + result.files.map(f => `<div class="report-file-row">📄 ${f}</div>`).join('')
      + '</div>';
  } else if (result.ok) {
    filesEl.innerHTML = '';
  }
}

function _buildStandaloneHtml(a, wk, sessionDate, css) {
  const fullName = `${a.name} ${a.lname}`.trim();
  const n        = a.intervals_ms.length;

  const slowdown      = _calcSlowdown(a.intervals_ms);
  const slowdownStr   = slowdown !== null
    ? `${slowdown >= 0 ? '+' : ''}${slowdown.toFixed(1)}%` : '—';
  const slowdownColor = slowdown === null ? 'var(--muted)'
    : slowdown > 10 ? 'var(--danger)'
    : slowdown > 5  ? 'var(--warning)'
    :                 'var(--success)';

  let rows = '';
  for (let i = 0; i < n; i++) {
    const iv   = a.intervals_ms[i];
    const rest = a.rests_ms[i];
    rows += `<tr>
      <td class="acc-td-num">${i + 1}</td>
      <td class="acc-td-dur">${_fmtMs(iv)}</td>
      <td class="acc-td-rest">${rest !== undefined ? _fmtMs(rest) : '—'}</td>
    </tr>`;
  }

  const chart = _buildFatigueCurve(a.intervals_ms);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>${fullName} — Splits Report</title>
<style>
${css}
/* ── Standalone report overrides ── */
body { height: auto !important; overflow: auto !important; }
.rpt-wrap  { max-width: 860px; margin: 0 auto; padding: 48px 40px; }
.card { break-inside: avoid; page-break-inside: avoid; }
.rpt-brand { font-family: var(--font-head); font-size: 13px; font-weight: 700;
             letter-spacing: 3px; text-transform: uppercase; color: var(--accent);
             margin-bottom: 20px; }
.rpt-name  { font-family: var(--font-head); font-size: 42px; font-weight: 700;
             color: var(--text); line-height: 1; margin-bottom: 6px; }
.rpt-date  { color: var(--muted); font-size: 16px; margin-bottom: 36px; }
</style>
</head>
<body class="light-mode">
<div class="rpt-wrap">

  <div class="rpt-brand">Splits</div>
  <div class="rpt-name">${fullName}</div>
  <div class="rpt-date">${sessionDate}</div>

  <div class="card">
    <div class="card-title">Workout</div>
    <div class="acc-params-strip" style="border-radius:var(--radius)">
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.interval_distance ?? '—'}&thinsp;m</div>
        <div class="acc-param-label">per interval</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.rest_time ?? '—'}&thinsp;s</div>
        <div class="acc-param-label">rest time</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${n}</div>
        <div class="acc-param-label">completed</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Performance</div>
    <div class="acc-middle-row" style="border-bottom:none">
      <div class="acc-table-col">
        <div class="acc-col-label">Interval Data</div>
        <table class="acc-table">
          <thead><tr>
            <th class="acc-th-num">#</th>
            <th>Duration</th>
            <th>Rest After</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="acc-stats-col">
        <div class="acc-col-label">Summary</div>
        <div class="acc-stat-card">
          <div class="acc-stat-val">${_fmtMs(a.avg_pace_ms)}</div>
          <div class="acc-stat-label">Avg Pace / 1600 m</div>
        </div>
        <div class="acc-stat-card">
          <div class="acc-stat-val" style="color:${slowdownColor}">${slowdownStr}</div>
          <div class="acc-stat-label">Slowdown (1st → last interval)</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Fatigue Curve</div>
    <div style="padding:8px 0">
      ${chart}
      <div class="acc-chart-xlabel">Interval Number</div>
    </div>
  </div>

</div>
</body>
</html>`;
}

// ── Email reports ─────────────────────────────────────────────

async function emailReports() {
  const selectedIds = _getSelectedIds();
  if (!_activeSessionData || !selectedIds.length) return;

  const btn = document.getElementById('email-reports-btn');
  btn.disabled    = true;
  btn.textContent = 'Loading…';

  const css = await _loadCss();

  const wk          = _activeSessionData.workout || {};
  const sessionDate = _fmtDate(_activeSessionData.started_at);
  const selected    = _activeSessionData.athletes.filter(a => selectedIds.includes(a.lap_id));

  // Build standalone HTML — Python converts it to PDF server-side via WeasyPrint
  _emailModalReports = selected.map(a => ({
    lap_id: a.lap_id,
    name:   `${a.name} ${a.lname}`.trim(),
    email:  a.email || '',
    html:   _buildStandaloneHtml(a, wk, sessionDate, css),
  }));

  // Build modal rows
  const rows = _emailModalReports.map((r, i) => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span style="flex:1;font-size:15px;font-weight:600;color:var(--text)">${_esc(r.name)}</span>
      <input type="email" class="email-modal-input"
             data-idx="${i}"
             placeholder="Enter email address"
             value="${_esc(r.email)}"
             oninput="_updateEmailSendBtn()"
             style="flex:2;padding:7px 10px;border-radius:var(--radius-sm);
                    border:1px solid var(--input-border);background:var(--input-bg);
                    color:var(--text);font-size:14px;min-width:0"/>
    </div>`).join('');

  document.getElementById('email-modal-rows').innerHTML = rows;
  document.getElementById('email-modal-status').textContent = '';
  document.getElementById('email-modal-status').style.color = '';
  _updateEmailSendBtn();

  btn.disabled    = false;
  btn.textContent = 'Email Reports';

  document.getElementById('email-modal').style.display = 'flex';
}

function _updateEmailSendBtn() {
  const inputs    = document.querySelectorAll('.email-modal-input');
  const allFilled = Array.from(inputs).every(inp => inp.value.trim() !== '');
  document.getElementById('email-send-btn').disabled = !allFilled;
}

function closeEmailModal() {
  document.getElementById('email-modal').style.display = 'none';
}

async function sendEmails() {
  if (!_emailModalReports) return;

  // Read current email values from inputs
  document.querySelectorAll('.email-modal-input').forEach(inp => {
    _emailModalReports[parseInt(inp.dataset.idx)].email = inp.value.trim();
  });

  const sendBtn   = document.getElementById('email-send-btn');
  const cancelBtn = document.getElementById('email-modal-cancel-btn');
  sendBtn.disabled   = true;
  sendBtn.textContent = 'Sending…';
  cancelBtn.disabled  = true;
  const statusEl = document.getElementById('email-modal-status');
  statusEl.textContent = '';

  // Persist updated emails to rosters
  await Promise.all(
    _emailModalReports.map(r => pywebview.api.update_athlete_email(r.lap_id, r.email))
  );

  // Send reports
  const result = await pywebview.api.send_reports(
    _emailModalReports.map(r => ({ name: r.name, email: r.email, html: r.html, lap_id: r.lap_id }))
  );

  statusEl.textContent = result.msg || (result.ok ? 'Done.' : 'Failed.');
  statusEl.style.color = result.ok ? 'var(--success)' : 'var(--danger)';

  sendBtn.textContent  = 'Send Emails';
  cancelBtn.disabled   = false;
  sendBtn.disabled     = !result.ok; // allow retry only on failure
}

// ── Email chart helpers ───────────────────────────────────────

/**
 * Build a self-contained SVG for the fatigue curve with embedded <style>
 * using hardcoded light-mode colors so it can be rasterized via canvas
 * without any external CSS.
 */
function _buildFatigueCurveSvgStandalone(intervals_ms) {
  if (!intervals_ms || intervals_ms.length < 2) return null;

  const W = 760, H = 220;
  const ml = 72, mr = 20, mt = 20, mb = 44;
  const pw = W - ml - mr;
  const ph = H - mt - mb;
  const n  = intervals_ms.length;

  const minMs = Math.min(...intervals_ms);
  const maxMs = Math.max(...intervals_ms);
  const pad   = (maxMs - minMs) * 0.12 || 2000;
  const yLo   = minMs - pad;
  const yHi   = maxMs + pad;
  const span  = yHi - yLo;

  const toX = i  => ml + (n === 1 ? pw / 2 : (i / (n - 1)) * pw);
  const toY = ms => mt + ((yHi - ms) / span) * ph;

  const pts = intervals_ms.map((ms, i) => [toX(i), toY(ms)]);

  const dataRange = maxMs - minMs || 1;
  const yTicks = maxMs === minMs
    ? [maxMs]
    : [0, 0.25, 0.5, 0.75, 1].map(t => maxMs - t * dataRange);

  const stride  = n <= 10 ? 1 : Math.ceil(n / 10);
  const linePath = _smoothPath(pts);
  const areaPath = linePath
    + ` L ${f(pts[n - 1][0])},${f(mt + ph)}`
    + ` L ${f(pts[0][0])},${f(mt + ph)} Z`;

  // Hardcoded light-mode palette
  const BORDER = '#bbbbbb', ACCENT = '#0044bb', MUTED = '#555555', BG = '#f0f0f0';

  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
  s += `<style>
    .cg{stroke:${BORDER};stroke-width:1;stroke-dasharray:4 4;fill:none}
    .ca{stroke:${BORDER};stroke-width:1;fill:none}
    .cl{font-family:monospace;font-size:13px;fill:${MUTED}}
    .cy{text-anchor:end}.cx{text-anchor:middle}
    .cf{fill:${ACCENT};fill-opacity:0.1;stroke:none}
    .cs{fill:none;stroke:${ACCENT};stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
    .cd{fill:${BG};stroke:${ACCENT};stroke-width:2}
  </style>`;

  yTicks.forEach(ms => {
    const y = f(toY(ms));
    s += `<line x1="${ml}" y1="${y}" x2="${ml + pw}" y2="${y}" class="cg"/>`;
  });
  s += `<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt + ph}" class="ca"/>`;
  s += `<line x1="${ml}" y1="${mt + ph}" x2="${ml + pw}" y2="${mt + ph}" class="ca"/>`;

  yTicks.forEach(ms => {
    s += `<text x="${ml - 8}" y="${f(toY(ms) + 4)}" class="cl cy">${_fmtMs(ms)}</text>`;
  });
  pts.forEach(([x], i) => {
    if (i % stride === 0 || i === n - 1) {
      s += `<text x="${f(x)}" y="${f(mt + ph + 20)}" class="cl cx">${i + 1}</text>`;
    }
  });

  s += `<path d="${areaPath}" class="cf"/>`;
  s += `<path d="${linePath}" class="cs"/>`;
  pts.forEach(([x, y]) => {
    s += `<circle cx="${f(x)}" cy="${f(y)}" r="4" class="cd"/>`;
  });

  s += '</svg>';
  return s;
}

/**
 * Rasterize an SVG string to a PNG and return a base64 data URL.
 * Uses 2× pixel density for crisp rendering in email clients.
 */
function _svgToPngDataUrl(svgStr, width, height) {
  return new Promise((resolve, reject) => {
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const img  = new Image();
    img.onload = () => {
      const scale  = 2;
      const canvas = document.createElement('canvas');
      canvas.width  = width  * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#f0f0f0';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/png'));
    };
    img.onerror = e => { URL.revokeObjectURL(url); reject(e); };
    img.src = url;
  });
}

/**
 * Like _buildStandaloneHtml but embeds the chart as a <img> PNG data URL
 * instead of an SVG, so it renders correctly in all email clients.
 */
function _buildEmailHtml(a, wk, sessionDate, css, chartPngDataUrl) {
  const fullName = `${a.name} ${a.lname}`.trim();
  const n        = a.intervals_ms.length;

  const slowdown      = _calcSlowdown(a.intervals_ms);
  const slowdownStr   = slowdown !== null
    ? `${slowdown >= 0 ? '+' : ''}${slowdown.toFixed(1)}%` : '—';
  const slowdownColor = slowdown === null ? '#555555'
    : slowdown > 10 ? '#cc0000'
    : slowdown > 5  ? '#bb5500'
    :                 '#006600';

  let rows = '';
  for (let i = 0; i < n; i++) {
    const iv   = a.intervals_ms[i];
    const rest = a.rests_ms[i];
    rows += `<tr>
      <td class="acc-td-num">${i + 1}</td>
      <td class="acc-td-dur">${_fmtMs(iv)}</td>
      <td class="acc-td-rest">${rest !== undefined ? _fmtMs(rest) : '—'}</td>
    </tr>`;
  }

  const chartHtml = chartPngDataUrl
    ? `<img src="${chartPngDataUrl}" alt="Fatigue Curve"
            style="width:100%;max-width:760px;height:auto;display:block"/>`
    : `<p style="color:#555555;font-size:13px;margin:8px 0">Need at least 2 intervals to draw chart.</p>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>${fullName} — Splits Report</title>
<style>
${css}
/* ── Email report overrides ── */
body { height: auto !important; overflow: auto !important; font-size: 13px; }
.rpt-wrap    { max-width: 640px; margin: 0 auto; padding: 28px 20px; }
.rpt-brand   { font-size: 10px; font-weight: 700; letter-spacing: 3px;
               text-transform: uppercase; color: var(--accent); margin-bottom: 12px; }
.rpt-name    { font-size: 26px; font-weight: 700; color: var(--text);
               line-height: 1.1; margin-bottom: 4px; }
.rpt-date    { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
.acc-param-val   { font-size: 18px; }
.acc-param-label { font-size: 11px; }
.acc-stat-val    { font-size: 20px; }
.acc-stat-label  { font-size: 12px; }
.acc-col-label   { font-size: 11px; }
.acc-table       { font-size: 13px; }
.card-title      { font-size: 13px; }

@media (max-width: 600px) {
  .rpt-wrap       { padding: 16px 12px; }
  .rpt-name       { font-size: 20px; }
  .card           { padding: 12px !important; }
  .acc-param-cell { padding: 8px 10px; }
  .acc-param-val  { font-size: 15px; }
  .acc-middle-row { flex-direction: column; }
  .acc-table-col  { border-right: none !important;
                    border-bottom: 1px solid var(--border);
                    width: 100%; box-sizing: border-box; }
  .acc-stats-col  { width: 100%; box-sizing: border-box; }
  .acc-stat-val   { font-size: 18px; }
}
</style>
</head>
<body class="light-mode">
<div class="rpt-wrap">

  <div class="rpt-brand">Splits</div>
  <div class="rpt-name">${fullName}</div>
  <div class="rpt-date">${sessionDate}</div>

  <div class="card">
    <div class="card-title">Workout</div>
    <div class="acc-params-strip" style="border-radius:var(--radius)">
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.interval_distance ?? '—'}&thinsp;m</div>
        <div class="acc-param-label">per interval</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${wk.rest_time ?? '—'}&thinsp;s</div>
        <div class="acc-param-label">rest time</div>
      </div>
      <div class="acc-param-cell">
        <div class="acc-param-val">${n}</div>
        <div class="acc-param-label">completed</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Performance</div>
    <div class="acc-middle-row" style="border-bottom:none">
      <div class="acc-table-col">
        <div class="acc-col-label">Interval Data</div>
        <table class="acc-table">
          <thead><tr>
            <th class="acc-th-num">#</th>
            <th>Duration</th>
            <th>Rest After</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="acc-stats-col">
        <div class="acc-col-label">Summary</div>
        <div class="acc-stat-card">
          <div class="acc-stat-val">${_fmtMs(a.avg_pace_ms)}</div>
          <div class="acc-stat-label">Avg Pace / 1600 m</div>
        </div>
        <div class="acc-stat-card">
          <div class="acc-stat-val" style="color:${slowdownColor}">${slowdownStr}</div>
          <div class="acc-stat-label">Slowdown (1st → last interval)</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Fatigue Curve</div>
    <div style="padding:8px 0">
      ${chartHtml}
      <div class="acc-chart-xlabel">Interval Number</div>
    </div>
  </div>

</div>
</body>
</html>`;
}

// ── Helpers ───────────────────────────────────────────────────

function _fmtDate(isoStr) {
  if (!isoStr) return 'Unknown date';
  try {
    return new Date(isoStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: true
    });
  } catch (_) { return isoStr; }
}

/** Format milliseconds → M:SS.ss  (e.g. 80500 → "1:20.50") */
function _fmtMs(ms) {
  if (ms === undefined || ms === null) return '—';
  const totalSec = ms / 1000;
  const min = Math.floor(totalSec / 60);
  const sec = (totalSec % 60).toFixed(2).padStart(5, '0');
  return `${min}:${sec}`;
}

function _esc(str) {
  return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function _safeId(str) {
  return (str || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}
