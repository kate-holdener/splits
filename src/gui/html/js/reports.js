// ============================================================
// REPORTS
// ============================================================

let _activeSessionId = null;   // session currently open in detail view

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
  document.getElementById('reports-list-view').style.display  = '';
  document.getElementById('reports-detail-view').style.display = 'none';
  document.getElementById('reports-back-label').textContent    = 'Home';
  document.getElementById('reports-refresh-btn').style.display = '';
}

function _showDetailView() {
  document.getElementById('reports-list-view').style.display  = 'none';
  document.getElementById('reports-detail-view').style.display = '';
  document.getElementById('reports-back-label').textContent    = 'All Sessions';
  document.getElementById('reports-refresh-btn').style.display = 'none';
}

// ── Session list ─────────────────────────────────────────────

// Called by state.js when the reports screen activates
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

  // Clear stale content while loading
  document.getElementById('detail-session-date').textContent     = 'Loading…';
  document.getElementById('detail-session-subtitle').textContent = '';
  document.getElementById('detail-workout-info').innerHTML       = '';
  document.getElementById('detail-athletes-thead').innerHTML     = '';
  document.getElementById('detail-athletes-tbody').innerHTML     = '';
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
  // ── heading ──
  document.getElementById('detail-session-date').textContent = _fmtDate(data.started_at);

  // ── workout stat boxes ──
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

  // ── performance table ──
  const maxInt = data.max_intervals || 0;

  // header — interleave Interval N / Rest N columns for readability
  let hCells = '<th style="width:36px"></th><th>Name</th>';
  for (let i = 0; i < maxInt; i++) {
    hCells += `<th class="perf-int-hdr">Interval ${i + 1}</th>`;
    if (i < maxInt - 1) {
      hCells += `<th class="perf-rest-hdr">Rest ${i + 1}</th>`;
    }
  }
  hCells += '<th class="perf-pace-hdr">Avg Pace / 1600 m</th>';
  document.getElementById('detail-athletes-thead').innerHTML = `<tr>${hCells}</tr>`;

  // rows
  document.getElementById('detail-athletes-tbody').innerHTML =
    data.athletes.map(a => {
      const rowId = _safeId(a.lap_id || `${a.name}_${a.lname}`);
      let cells = `
        <td><input type="checkbox" class="athlete-report-cb"
             data-id="${_esc(a.lap_id)}" onchange="_updateGenerateBtn()"/></td>
        <td><span class="athlete-report-name">${a.name} ${a.lname}</span></td>`;

      for (let i = 0; i < maxInt; i++) {
        const iv = a.intervals_ms[i];
        cells += iv !== undefined
          ? `<td class="perf-val">${_fmtMs(iv)}</td>`
          : `<td class="perf-dash">—</td>`;
        if (i < maxInt - 1) {
          const rest = a.rests_ms[i];
          cells += rest !== undefined
            ? `<td class="perf-rest">${_fmtMs(rest)}</td>`
            : `<td class="perf-dash">—</td>`;
        }
      }
      cells += `<td class="perf-pace">${_fmtMs(a.avg_pace_ms)}</td>`;
      return `<tr id="arow-${rowId}">${cells}</tr>`;
    }).join('');
}

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
  if (!dir && !selected.length)      hint.textContent = 'Select athletes and an output directory';
  else if (!dir)                      hint.textContent = 'Choose an output directory';
  else if (!selected.length)          hint.textContent = 'Select at least one athlete';
  else hint.textContent = `${selected.length} athlete${selected.length !== 1 ? 's' : ''} selected`;
}

// ── Export ────────────────────────────────────────────────────

async function pickReportDir() {
  const r = await pywebview.api.pick_directory();
  if (r && r.path) {
    document.getElementById('report-dir').value = r.path;
    const disp = document.getElementById('report-dir-display');
    disp.textContent  = r.path;
    disp.style.color  = 'var(--text)';
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
      + r.files.map(f =>
          `<div class="report-file-row">📄 ${f}</div>`
        ).join('')
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
