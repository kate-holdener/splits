// ============================================================
// ROSTER DATA
// ============================================================

let _savedRosters = [];   // active (non-archived) — used by workout setup
let _allRosters   = [];   // all including archived — used by settings screen
let _selectedSettingsRosterId = null;

function renderRostersList(rosters) {
  _savedRosters = rosters || [];
}

// ============================================================
// ROSTER UI — athletes card subtitle
// ============================================================

function updateRosterUI(roster) {
  const subtitle = document.getElementById('athletes-subtitle');
  if (subtitle) subtitle.textContent = roster
    ? `Athletes in ${roster.name}.`
    : 'Select a roster to view and manage its athletes.';
}

// ============================================================
// DATA LOADING
// ============================================================

async function loadRostersList() {
  const r = await pywebview.api.list_rosters();
  if (r.rosters) renderRostersList(r.rosters);
}

async function loadAllRosters() {
  try {
    const result = await pywebview.api.list_all_rosters_with_archived();
    if (result.ok) {
      _allRosters = result.rosters || [];
      renderSettingsRosterDropdown();
    } else {
      console.error('Failed to load rosters:', result.msg);
    }
  } catch (e) {
    console.error('Error loading rosters:', e);
  }
}

// ============================================================
// SETTINGS SCREEN — roster dropdown
// ============================================================

function toggleSettingsRosterDropdown(event) {
  event.stopPropagation();
  const menu = document.getElementById('settings-roster-picker-menu');
  if (menu.classList.contains('open')) closeSettingsRosterDropdown();
  else openSettingsRosterDropdown();
}

function openSettingsRosterDropdown() {
  document.getElementById('settings-roster-picker-menu').classList.add('open');
  document.getElementById('settings-roster-trigger').classList.add('open');
  renderSettingsRosterDropdown();
}

function closeSettingsRosterDropdown() {
  document.getElementById('settings-roster-picker-menu').classList.remove('open');
  document.getElementById('settings-roster-trigger').classList.remove('open');
}

function renderSettingsRosterDropdown() {
  const menu = document.getElementById('settings-roster-picker-menu');
  if (!menu) return;
  renderRosterDropdownOptions(
    menu,
    _allRosters,
    _selectedSettingsRosterId,
    selectSettingsRoster,
    { emptyMessage: 'No rosters available', showArchived: true }
  );
}

function selectSettingsRoster(roster) {
  _selectedSettingsRosterId = roster.id;
  const label = document.getElementById('settings-roster-selected-label');
  label.textContent = roster.name;
  label.classList.remove('placeholder');
  closeSettingsRosterDropdown();
  onSettingsRosterSelected(roster); // defined in settings.js
}

// ============================================================
// SETTINGS SCREEN — roster actions
// ============================================================

async function archiveSelectedRoster() {
  if (!_selectedSettingsRosterId) return;
  const roster = _allRosters.find(r => r.id === _selectedSettingsRosterId);
  if (!roster) return;

  if (!await showConfirm(
    `This will hide "${roster.name}" from normal views.`,
    { title: `Archive "${roster.name}"?`, confirmText: 'Archive' }
  )) return;

  try {
    const result = await pywebview.api.archive_roster(_selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');
      await loadAllRosters();
      const updated = _allRosters.find(r => r.id === _selectedSettingsRosterId);
      if (updated) updateRosterManagementButtons(updated);
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error archiving roster: ' + e.message, 'err');
  }
}

async function restoreSelectedRoster() {
  if (!_selectedSettingsRosterId) return;

  try {
    const result = await pywebview.api.restore_roster(_selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');
      await loadAllRosters();
      const updated = _allRosters.find(r => r.id === _selectedSettingsRosterId);
      if (updated) updateRosterManagementButtons(updated);
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error restoring roster: ' + e.message, 'err');
  }
}

async function activateSelectedRoster() {
  if (!_selectedSettingsRosterId) return;

  try {
    const result = await pywebview.api.select_roster(_selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');
      await loadAllRosters();
      const updated = _allRosters.find(r => r.id === _selectedSettingsRosterId);
      if (updated) updateRosterManagementButtons(updated);
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error activating roster: ' + e.message, 'err');
  }
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

  await loadAllRosters();
  const newRoster = _allRosters.find(r2 => r2.id === r.roster.id) || r.roster;
  selectSettingsRoster(newRoster);
  closeRosterModal();
}
