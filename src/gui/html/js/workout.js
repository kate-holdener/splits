// ============================================================
// PERFORMANCE TOOLTIP
// ============================================================

const _perfData = new Map(); // start_tag -> athlete data

function formatInterval(ms) {
  const total  = Math.round(ms);
  const mins   = Math.floor(total / 60000);
  const secs   = Math.floor((total % 60000) / 1000);
  const millis = total % 1000;
  return `${mins}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
}

function formatRest(ms) {
  return Math.round(ms / 1000) + 's';
}

function buildTooltipHTML(a) {
  const name      = `${a.first_name || ''} ${a.last_name || ''}`.trim() || '—';
  const intervals = a.intervals || [];
  const rests     = a.rests     || [];
  const isRunning = a.status === 'RUNNING';

  if (!intervals.length && !isRunning) {
    return { name, body: '<div class="tip-empty">No completed intervals yet</div>' };
  }

  let rows = '';
  for (let i = 0; i < intervals.length; i++) {
    const restCell = rests[i] != null
      ? `<td class="tip-label">Rest</td><td>${formatRest(rests[i])}</td>`
      : '<td></td><td></td>';
    rows += `<tr>
      <td class="tip-label">Interval ${i + 1}</td>
      <td>${formatInterval(intervals[i])}</td>
      ${restCell}
    </tr>`;
  }
  if (isRunning) {
    rows += `<tr>
      <td class="tip-label">Interval ${intervals.length + 1}</td>
      <td style="color:var(--muted)">—</td>
      <td></td><td></td>
    </tr>`;
  }

  return { name, body: `<table>${rows}</table>` };
}

function showTooltip(e, startTag) {
  const a = _perfData.get(startTag);
  if (!a) return;
  const tip = document.getElementById('perf-tooltip');
  const { name, body } = buildTooltipHTML(a);
  document.getElementById('tip-name').textContent = name;
  document.getElementById('tip-body').innerHTML   = body;
  tip.style.display = 'block';
  positionTooltip(e);
}

function positionTooltip(e) {
  const tip  = document.getElementById('perf-tooltip');
  const x    = e.clientX + 16;
  const y    = e.clientY + 8;
  const tipW = tip.offsetWidth  || 280;
  const tipH = tip.offsetHeight || 100;
  tip.style.left = (x + tipW > window.innerWidth  ? x - tipW - 32 : x) + 'px';
  tip.style.top  = (y + tipH > window.innerHeight ? y - tipH - 16 : y) + 'px';
}

function hideTooltip() {
  document.getElementById('perf-tooltip').style.display = 'none';
}

// ============================================================
// WORKOUT ATHLETES TABLE — sorting + drag-and-drop
// ============================================================

let _originalOrder = [];
let _athleteOrder  = [];
let _dragSrcRow    = null;
let _isDragging    = false;

function _statusPriority(status) {
  return (status === 'RUNNING' || status === 'RESTING') ? 0 : 1;
}

function _onDragStart(e) {
  _dragSrcRow = e.currentTarget;
  _isDragging = true;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', _dragSrcRow.dataset.tag);
  setTimeout(() => { if (_dragSrcRow) _dragSrcRow.classList.add('dragging'); }, 0);
}

function _onDragOver(e) {
  if (!_dragSrcRow) return;
  const row = e.currentTarget;
  if (row === _dragSrcRow) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; return; }
  if (row.dataset.inactive === 'true') return;
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const rect = row.getBoundingClientRect();
  if (e.clientY < rect.top + rect.height / 2) {
    row.parentNode.insertBefore(_dragSrcRow, row);
  } else {
    row.parentNode.insertBefore(_dragSrcRow, row.nextSibling);
  }
}

function _onDrop(e) {
  e.preventDefault();
  const tbody = _dragSrcRow
    ? _dragSrcRow.closest('tbody')
    : document.getElementById('athletes-status-tbody');
  if (tbody) {
    _athleteOrder = [...tbody.querySelectorAll('tr.athlete-row:not([data-inactive="true"])')].map(r => r.dataset.tag);
  }
}

function _onDragEnd(e) {
  if (_dragSrcRow) _dragSrcRow.classList.remove('dragging');
  _dragSrcRow = null;
  _isDragging = false;
}

async function loadWorkoutAthletes() {
  if (_isDragging) return;
  const r     = await pywebview.api.list_athletes_with_status();
  const tbody = document.getElementById('athletes-status-tbody');
  if (!tbody) return;
  if (!r.ok || !r.athletes || !r.athletes.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted)">No athletes loaded.</td></tr>';
    return;
  }

  r.athletes.forEach(a => _perfData.set(a.start_tag, a));

  const checked = new Set([...document.querySelectorAll('.athlete-cb:checked')].map(cb => cb.value));

  if (_originalOrder.length === 0) {
    _originalOrder = r.athletes.map(a => a.start_tag);
  }

  const sorted = [...r.athletes].sort((a, b) => {
    const pa = _statusPriority(a.status), pb = _statusPriority(b.status);
    if (pa !== pb) return pa - pb;
    const ia = _athleteOrder.indexOf(a.start_tag);
    const ib = _athleteOrder.indexOf(b.start_tag);
    if (ia !== -1 && ib !== -1) return ia - ib;
    return _originalOrder.indexOf(a.start_tag) - _originalOrder.indexOf(b.start_tag);
  });

  tbody.innerHTML = sorted.map(a => {
    const name     = `${a.first_name || ''} ${a.last_name || ''}`.trim() || '—';
    const inactive = a.status === 'INACTIVE';
    const isChecked = inactive && checked.has(a.start_tag);

    let statusCell = '';
    if (a.status === 'RUNNING') {
      const t = a.elapsed_seconds != null ? ` · ${a.elapsed_seconds}s` : '';
      statusCell = `<span class="tag running">RUNNING${t}</span>`;
    } else if (a.status === 'RESTING') {
      const t = a.rest_remaining_seconds != null ? ` · ${a.rest_remaining_seconds}s left` : '';
      statusCell = `<span class="tag resting">RESTING${t}</span>`;
    } else {
      statusCell = `<span class="tag inactive">INACTIVE</span>`;
    }

    const tag       = a.start_tag ? a.start_tag.replace(/'/g, "&#39;") : '';
    const dragAttrs = inactive ? 'draggable="false"' : 'draggable="true" ondragstart="_onDragStart(event)"';
    const dropAttrs = inactive ? '' : 'ondrop="_onDrop(event)"';
    const handle    = inactive
      ? '<td class="drag-handle drag-handle--inactive" aria-hidden="true"></td>'
      : '<td class="drag-handle" title="Drag to reorder" aria-label="Drag to reorder">⠿</td>';

    return `<tr class="athlete-row" ${dragAttrs} data-tag="${a.start_tag || ''}" data-inactive="${inactive}"
      onmouseenter="showTooltip(event,'${tag}')" onmouseleave="hideTooltip()"
      ondragover="_onDragOver(event)" ${dropAttrs} ondragend="_onDragEnd(event)">
      ${handle}
      <td><input type="checkbox" class="athlete-cb" value="${a.start_tag || ''}"
        ${inactive ? '' : 'disabled'} ${isChecked ? 'checked' : ''}
        onchange="updateSelectedCount()"/></td>
      <td>${name}</td>
      <td>${statusCell}</td>
    </tr>`;
  }).join('');

  updateSelectedCount();
}

// ============================================================
// WORKOUT CONTROLS
// ============================================================

async function startSelected() {
  const checked = [...document.querySelectorAll('.athlete-cb:checked')].map(cb => cb.value);
  if (!checked.length) { log('No athletes selected.', 'err'); return; }
  const r = await pywebview.api.start_selected(JSON.stringify(checked));
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
  document.querySelectorAll('.athlete-cb').forEach(cb => cb.checked = false);
  document.getElementById('select-all-cb').checked = false;
  updateSelectedCount();
}

function updateSelectedCount() {
  const n = document.querySelectorAll('.athlete-cb:checked').length;
  document.getElementById('selected-count').textContent = n + ' selected';
  document.getElementById('start-selected-btn').disabled = (n === 0);
}

function toggleSelectAll(masterCb) {
  document.querySelectorAll('.athlete-cb:not(:disabled)').forEach(cb => cb.checked = masterCb.checked);
  updateSelectedCount();
}

async function finishWorkout() {
  if (!confirm('End the workout? This will clear all running and resting state.')) return;
  const r = await pywebview.api.finish_workout();
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
}

async function showRestingRunners() {
  const r = await pywebview.api.show_resting_runners();
  log(r.msg, r.ok ? 'ok' : 'err');
}
