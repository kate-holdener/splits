// ============================================================
// ROSTER PICKER — dropdown
// ============================================================

let _savedRosters = [];

function renderRostersList(rosters) {
  _savedRosters = rosters || [];
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
    if (ar.ok)      loadWorkoutAthletes();
  } else {
    if (r.state)   applyState(r.state);
    if (r.rosters) renderRostersList(r.rosters);
    updateRosterUI(r.roster);
  }

  closeRosterModal();
}

async function loadRostersList() {
  const r = await pywebview.api.list_rosters();
  if (r.rosters) renderRostersList(r.rosters);
}
