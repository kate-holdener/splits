// ============================================================
// ROSTER PICKER — dropdown
// ============================================================

function renderRostersList(rosters) {
  const menu  = document.getElementById('roster-picker-menu');
  const label = document.getElementById('roster-selected-label');
  if (!menu || !label) return;

  const activeRoster = (rosters || []).find(s => s.is_active);

  if (activeRoster) {
    label.textContent = activeRoster.name;
    label.classList.remove('placeholder');
  } else {
    label.textContent = '— No roster selected —';
    label.classList.add('placeholder');
  }

  menu.replaceChildren();

  const onRosterSelect = (roster) => onRosterOptionClick(roster.id);

  renderRosterDropdownOptions(
    menu,
    rosters,
    null, // No specific selection highlighting for workout screen
    onRosterSelect,
    {
      emptyMessage: 'No rosters yet.',
      showArchived: false,
      customEmptyStyle: true
    }
  );
}

function toggleRosterDropdown(e) {
  e.stopPropagation();
  const trigger = document.getElementById('roster-trigger');
  const menu    = document.getElementById('roster-picker-menu');
  const isOpen  = menu.classList.contains('open');
  closeRosterDropdown();
  if (!isOpen) {
    trigger.classList.add('open');
    menu.classList.add('open');
  }
}

function closeRosterDropdown() {
  document.getElementById('roster-trigger')?.classList.remove('open');
  document.getElementById('roster-picker-menu')?.classList.remove('open');
}

async function onRosterOptionClick(rosterId) {
  closeRosterDropdown();
  const r = await pywebview.api.select_roster(rosterId);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (!r.ok) return;
  if (r.state) applyState(r.state);
  loadAthleteList();
  const lr = await pywebview.api.list_rosters();
  if (lr.rosters) renderRostersList(lr.rosters);
}

// ============================================================
// ROSTER UI — athletes card subtitle + Add button state
// ============================================================

function updateRosterUI(roster) {
  const subtitle = document.getElementById('athletes-subtitle');
  if (subtitle) subtitle.textContent = roster
    ? `Athletes in ${roster.name}.`
    : 'Select a roster to view and manage its athletes.';
}

// ============================================================
// NEW ROSTER MODAL
// ============================================================

let _modalCsvPath = '';

function openRosterModal() {
  _modalCsvPath = '';
  document.getElementById('modal-roster-name').value = '';
  const disp = document.getElementById('modal-csv-display');
  disp.textContent = 'No file selected…';
  disp.style.color = 'var(--input-placeholder)';
  document.getElementById('modal-create-btn').disabled = true;
  const err = document.getElementById('modal-error');
  err.style.display = 'none';
  err.textContent = '';
  document.getElementById('roster-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('modal-roster-name').focus(), 50);
}

function closeRosterModal() {
  document.getElementById('roster-modal').style.display = 'none';
}

function updateModalCreateBtn() {
  const name = document.getElementById('modal-roster-name').value.trim();
  document.getElementById('modal-create-btn').disabled = !name;
  const err = document.getElementById('modal-error');
  if (name) { err.style.display = 'none'; err.textContent = ''; }
}

async function pickModalCsv() {
  const result = await window.pywebview.api.pick_csv_file();
  if (result && result.path) {
    _modalCsvPath = result.path;
    const disp = document.getElementById('modal-csv-display');
    disp.textContent = result.path.split(/[/\\]/).pop();
    disp.style.color = 'var(--text)';
  }
}

async function submitNewRoster() {
  const name = document.getElementById('modal-roster-name').value.trim();
  if (!name) return;

  document.getElementById('modal-create-btn').disabled = true;

  const r = await pywebview.api.create_roster(name);
  if (!r.ok) {
    const err = document.getElementById('modal-error');
    err.textContent = r.msg || 'Failed to create roster.';
    err.style.display = 'block';
    document.getElementById('modal-create-btn').disabled = false;
    return;
  }
  log(`Roster "${r.roster.name}" created.`, 'ok');

  if (_modalCsvPath) {
    const ar = await pywebview.api.add_athletes_from_csv(_modalCsvPath);
    log(ar.msg, ar.ok ? 'ok' : 'err');
    if (ar.state)   applyState(ar.state);
    if (ar.rosters) renderRostersList(ar.rosters);
    if (ar.ok)      loadAthleteList();
  } else {
    if (r.state)   applyState(r.state);
    if (r.rosters) renderRostersList(r.rosters);
    updateRosterUI(r.roster);
    document.getElementById('athletes-ok').style.display = 'none';
    document.getElementById('athlete-tbody').innerHTML = '';
  }

  closeRosterModal();
}

async function loadRostersList() {
  const r = await pywebview.api.list_rosters();
  if (r.rosters) renderRostersList(r.rosters);
}
