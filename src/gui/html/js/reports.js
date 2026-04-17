// ============================================================
// REPORTS
// ============================================================

let _activeSessionId = null;

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
      ? `${wk.interval_distance} m &times; ${wk.laps_per_interval} `
        + `lap${wk.laps_per_interval !== 1 ? 's' : ''}`
        + `&nbsp;&nbsp;·&nbsp;&nbsp;${wk.rest_time} s rest`
      : 'Unknown workout';
    const n = s.athletes_with_data;
    return `
      <div class="session-item" onclick="openSession('${_esc(s.session_id)}')">
        <div class="session-dot"></div>
        <div class="session-info">
          <div class="session-date">${date}</div>
          <div class="session-meta">${wkStr}&nbsp;&nbsp;·&nbsp;&nbsp;${n} athlete${n !== 1 ? 's' : ''}</div>
        </div>
        <div class="session-arrow">›</div>
      </div>`;
  }).join('');
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
  _updateGenerateBtn();

  const r = await pywebview.api.get_session_details(sessionId);
  if (!r.ok) {
    log(r.msg || 'Failed to load session.', 'err');
    _showListView();
    return;
  }
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
      <div class="stat-val">${wk.laps_per_interval ?? '—'}</div>
      <div class="stat-label">Laps / Interval</div>
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

  // Interval + rest data rows
  let rows = '';
  for (let i = 0; i < n; i++) {
    const iv   = a.intervals_ms[i];
    const rest = a.rests_ms[i];
    rows += `<tr>
      <td style="color:var(--muted);width:40px">${i + 1}</td>
      <td class="perf-val">${_fmtMs(iv)}</td>
      <td class="${rest !== undefined ? 'perf-rest' : 'perf-dash'}">${rest !== undefined ? _fmtMs(rest) : '—'}</td>
    </tr>`;
  }

  // Slowdown %
  const slowdown      = _calcSlowdown(a.intervals_ms);
  const slowdownStr   = slowdown !== null
    ? `${slowdown >= 0 ? '+' : ''}${slowdown.toFixed(1)}%`
    : '—';
  const slowdownColor = slowdown === null  ? 'var(--muted)'
    : slowdown > 10                        ? 'var(--danger)'
    : slowdown > 5                         ? 'var(--warning)'
    :                                        'var(--success)';

  const chart = _buildFatigueCurve(a.intervals_ms);

  return `
<div class="acc-item" id="acc-${id}">
  <div class="acc-header" onclick="toggleAthletePanel('${id}')">
    <span class="acc-arrow" id="acc-arrow-${id}">▶</span>
    <span class="acc-name">${fullName}</span>
    <span class="acc-meta">${n} interval${n !== 1 ? 's' : ''}&nbsp;·&nbsp;${_fmtMs(a.avg_pace_ms)}&thinsp;/&thinsp;1600 m</span>
    <label class="acc-cb-label" onclick="event.stopPropagation()">
      <input type="checkbox" class="athlete-report-cb"
             data-id="${_esc(a.lap_id)}" onchange="_updateGenerateBtn()"/>
      <span style="font-size:13px;color:var(--muted);font-family:var(--font-mono);font-weight:normal">Export</span>
    </label>
  </div>
  <div class="acc-body" id="acc-body-${id}">

    <div class="acc-section">
      <div class="acc-section-title">Workout Parameters</div>
      <div class="acc-params-row">
        <div class="acc-param"><div class="acc-param-val">${wk.interval_distance ?? '—'} m</div><div class="acc-param-label">per interval</div></div>
        <div class="acc-param"><div class="acc-param-val">${wk.laps_per_interval ?? '—'}</div><div class="acc-param-label">laps / interval</div></div>
        <div class="acc-param"><div class="acc-param-val">${wk.rest_time ?? '—'} s</div><div class="acc-param-label">rest</div></div>
        <div class="acc-param"><div class="acc-param-val">${n}</div><div class="acc-param-label">completed</div></div>
      </div>
    </div>

    <div class="acc-section">
      <div class="acc-section-title">Interval Data</div>
      <table class="acc-table">
        <thead><tr>
          <th style="width:40px">#</th>
          <th>Duration</th>
          <th>Rest After</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>

    <div class="acc-section">
      <div class="acc-section-title">Analytics — Fatigue Curve</div>
      <div class="acc-analytics-wrap">
        <div class="acc-chart-wrap">${chart}</div>
        <div class="acc-kpi-wrap">
          <div class="acc-kpi">
            <div class="acc-kpi-val">${_fmtMs(a.avg_pace_ms)}</div>
            <div class="acc-kpi-label">Avg Pace / 1600 m</div>
          </div>
          <div class="acc-kpi">
            <div class="acc-kpi-val" style="color:${slowdownColor}">${slowdownStr}</div>
            <div class="acc-kpi-label">Slowdown (1st → last)</div>
          </div>
        </div>
      </div>
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
    return '<p style="color:var(--muted);font-size:13px;margin:0">Need at least 2 intervals to draw chart.</p>';
  }

  const W = 460, H = 160;
  const ml = 64, mr = 16, mt = 16, mb = 36;
  const pw  = W - ml - mr;
  const ph  = H - mt - mb;
  const n   = intervals_ms.length;

  const minMs = Math.min(...intervals_ms);
  const maxMs = Math.max(...intervals_ms);
  const range = maxMs - minMs || 1000;   // avoid divide-by-zero if all times equal

  const toX = i  => ml + (n === 1 ? pw / 2 : (i / (n - 1)) * pw);
  const toY = ms => mt + ((maxMs - ms) / range) * ph;

  const pts = intervals_ms.map((ms, i) => [toX(i), toY(ms)]);

  // Y-axis reference ticks
  const yTicks = [maxMs, (maxMs + minMs) / 2, minMs];

  // Area fill path (closes along the x-axis baseline)
  const areaD = `M ${f(pts[0][0])},${f(mt + ph)} `
    + pts.map(([x, y]) => `L ${f(x)},${f(y)}`).join(' ')
    + ` L ${f(pts[n - 1][0])},${f(mt + ph)} Z`;

  const polyPts = pts.map(([x, y]) => `${f(x)},${f(y)}`).join(' ');

  // Skip x-labels if crowded
  const stride = n <= 8 ? 1 : Math.ceil(n / 8);

  let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" `
        + `viewBox="0 0 ${W} ${H}" class="fatigue-chart">`;

  // Grid lines
  yTicks.forEach(ms => {
    const y = f(toY(ms));
    s += `<line x1="${ml}" y1="${y}" x2="${ml + pw}" y2="${y}" class="chart-grid"/>`;
  });

  // Axes
  s += `<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt + ph}" class="chart-axis"/>`;
  s += `<line x1="${ml}" y1="${mt + ph}" x2="${ml + pw}" y2="${mt + ph}" class="chart-axis"/>`;

  // Y labels
  yTicks.forEach(ms => {
    const y = f(toY(ms) + 4);
    s += `<text x="${ml - 6}" y="${y}" class="chart-label chart-label-y">${_fmtMs(ms)}</text>`;
  });

  // X labels
  pts.forEach(([x], i) => {
    if (i % stride === 0 || i === n - 1) {
      s += `<text x="${f(x)}" y="${f(mt + ph + 18)}" class="chart-label chart-label-x">${i + 1}</text>`;
    }
  });

  // Area, line, dots
  s += `<path d="${areaD}" class="chart-area"/>`;
  s += `<polyline points="${polyPts}" class="chart-line"/>`;
  pts.forEach(([x, y]) => {
    s += `<circle cx="${f(x)}" cy="${f(y)}" r="4" class="chart-dot"/>`;
  });

  s += '</svg>';
  return s;
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

async function generateReports() {
  const selectedIds = _getSelectedIds();
  const dir         = document.getElementById('report-dir').value.trim();
  if (!_activeSessionId || !selectedIds.length || !dir) return;

  const btn = document.getElementById('generate-reports-btn');
  btn.disabled    = true;
  btn.textContent = 'Generating…';

  const r = await pywebview.api.generate_reports(
    _activeSessionId, dir, JSON.stringify(selectedIds)
  );

  btn.textContent = '📊 Generate PDF Reports';
  _updateGenerateBtn();
  log(r.msg, r.ok ? 'ok' : 'err');

  const filesEl = document.getElementById('report-files');
  if (r.ok && r.files && r.files.length) {
    filesEl.innerHTML =
      '<div class="card" style="max-width:900px">'
      + '<div class="card-title">Generated Files</div>'
      + r.files.map(f => `<div class="report-file-row">📄 ${f}</div>`).join('')
      + '</div>';
  } else if (r.ok) {
    filesEl.innerHTML = '';
  }
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
