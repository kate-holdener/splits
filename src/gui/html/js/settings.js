// ============================================================
// SETTINGS SCREEN — Roster and Athlete Management
// ============================================================

let settingsRosters = [];
let settingsAthletes = [];
let selectedSettingsRosterId = null;

// ============================================================
// SETTINGS SCREEN — Roster dropdown functionality
// ============================================================

function toggleSettingsRosterDropdown(event) {
  event.stopPropagation();
  const menu = document.getElementById('settings-roster-picker-menu');
  const isOpen = menu.classList.contains('open');

  if (isOpen) {
    closeSettingsRosterDropdown();
  } else {
    openSettingsRosterDropdown();
  }
}

function openSettingsRosterDropdown() {
  const menu = document.getElementById('settings-roster-picker-menu');
  const trigger = document.getElementById('settings-roster-trigger');

  menu.classList.add('open');
  trigger.classList.add('open');

  renderSettingsRosterDropdown();
}

function closeSettingsRosterDropdown() {
  const menu = document.getElementById('settings-roster-picker-menu');
  const trigger = document.getElementById('settings-roster-trigger');

  menu.classList.remove('open');
  trigger.classList.remove('open');
}

function renderSettingsRosterDropdown() {
  const menu = document.getElementById('settings-roster-picker-menu');
  renderRosterDropdownOptions(
    menu,
    settingsRosters,
    selectedSettingsRosterId,
    selectSettingsRoster,
    {
      emptyMessage: 'No rosters available',
      showArchived: true
    }
  );
}

function selectSettingsRoster(roster) {
  selectedSettingsRosterId = roster.id;

  const label = document.getElementById('settings-roster-selected-label');
  label.textContent = roster.name;
  label.classList.remove('placeholder');

  closeSettingsRosterDropdown();

  showRosterManagement(roster);
  loadSettingsAthletesForRoster(roster.id);
}

function showRosterManagement(roster) {
  const athletesCard = document.getElementById('athletes-management-card');
  athletesCard.style.display = 'block';

  const rosterDisplay = document.getElementById('athlete-roster-display');
  rosterDisplay.textContent = `for ${roster.name}`;

  const rosterCard = document.getElementById('roster-management-card');
  rosterCard.style.display = 'block';

  updateRosterManagementButtons(roster);
}

function updateRosterManagementButtons(roster) {
  const archiveBtn = document.getElementById('archive-roster-btn');
  const restoreBtn = document.getElementById('restore-roster-btn');
  const activateBtn = document.getElementById('activate-roster-btn');
  const statusDisplay = document.getElementById('roster-status-display');

  const isArchived = roster.archived || false;
  const isActive = roster.is_active || false;

  archiveBtn.style.display = isArchived ? 'none' : 'inline-block';
  restoreBtn.style.display = isArchived ? 'inline-block' : 'none';
  activateBtn.style.display = (!isArchived && !isActive) ? 'inline-block' : 'none';

  let statusText = '';
  if (isArchived) statusText = 'Status: Archived';
  else if (isActive) statusText = 'Status: Active Roster';
  else statusText = 'Status: Inactive';

  statusDisplay.textContent = statusText;
}

// ============================================================
// SETTINGS SCREEN — Roster management actions
// ============================================================

async function archiveSelectedRoster() {
  if (!selectedSettingsRosterId) return;

  const roster = settingsRosters.find(s => s.id === selectedSettingsRosterId);
  if (!roster) return;

  if (!confirm(`Are you sure you want to archive "${roster.name}"? This will hide it from normal views.`)) {
    return;
  }

  try {
    const result = await pywebview.api.archive_roster(selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');

      await loadSettingsRosters();
      const updatedRoster = settingsRosters.find(s => s.id === selectedSettingsRosterId);
      if (updatedRoster) {
        updateRosterManagementButtons(updatedRoster);
        renderSettingsRosterDropdown();
      }
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error archiving roster: ' + e.message, 'err');
  }
}

async function restoreSelectedRoster() {
  if (!selectedSettingsRosterId) return;

  try {
    const result = await pywebview.api.restore_roster(selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');

      await loadSettingsRosters();
      const updatedRoster = settingsRosters.find(s => s.id === selectedSettingsRosterId);
      if (updatedRoster) {
        updateRosterManagementButtons(updatedRoster);
        renderSettingsRosterDropdown();
      }
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error restoring roster: ' + e.message, 'err');
  }
}

async function activateSelectedRoster() {
  if (!selectedSettingsRosterId) return;

  const roster = settingsRosters.find(s => s.id === selectedSettingsRosterId);
  if (!roster) return;

  try {
    const result = await pywebview.api.select_roster(selectedSettingsRosterId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');

      await loadSettingsRosters();
      const updatedRoster = settingsRosters.find(s => s.id === selectedSettingsRosterId);
      if (updatedRoster) {
        updateRosterManagementButtons(updatedRoster);
        renderSettingsRosterDropdown();
      }
    } else {
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    if (window.log) window.log('Error activating roster: ' + e.message, 'err');
  }
}

// ============================================================
// ROSTER LOADING AND RENDERING
// ============================================================

async function loadSettingsRosters() {
  try {
    const result = await pywebview.api.list_all_rosters_with_archived();
    if (result.ok) {
      settingsRosters = result.rosters || [];
      renderSettingsRosterDropdown();
    } else {
      console.error('Failed to load rosters:', result.msg);
    }
  } catch (e) {
    console.error('Error loading rosters:', e);
  }
}

// ============================================================
// ATHLETE MANAGEMENT
// ============================================================

async function loadSettingsAthletesForRoster(rosterId) {
  try {
    const result = await pywebview.api.list_athletes_for_roster_including_archived(rosterId);
    if (result.ok) {
      settingsAthletes = result.athletes || [];
      renderSettingsAthletes();
    } else {
      console.error('Failed to load athletes:', result.msg);
    }
  } catch (e) {
    console.error('Error loading athletes:', e);
  }
}

function renderSettingsAthletes() {
  const tbody = document.getElementById('athletes-settings-tbody');
  tbody.innerHTML = '';

  if (!settingsAthletes.length) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = '<td colspan="6" style="text-align:center;color:var(--muted);padding:24px">No athletes found</td>';
    tbody.appendChild(emptyRow);
    return;
  }

  settingsAthletes.forEach(athlete => {
    const row = document.createElement('tr');
    const isActive = !(athlete.archived || false);
    const fullName = `${athlete.first_name || athlete.name || ''} ${athlete.last_name || athlete.lname || ''}`.trim();
    const id = escapeHtml(athlete.id);

    row.innerHTML = `
      <td><strong>${escapeHtml(fullName)}</strong></td>
      <td style="color:${athlete.email ? 'var(--text)' : 'var(--muted)'};font-size:13px">
        ${escapeHtml(athlete.email || '—')}
      </td>
      <td><code>${escapeHtml(athlete.finish_tag || '-')}</code></td>
      <td><code>${escapeHtml(athlete.start_tag || '-')}</code></td>
      <td>
        <label class="athlete-toggle" title="${isActive ? 'Active — click to deactivate' : 'Inactive — click to activate'}">
          <input type="checkbox" ${isActive ? 'checked' : ''} onchange="toggleAthleteActive('${id}', this.checked)"/>
          <span class="toggle-slider"></span>
        </label>
      </td>
      <td>
        <div class="settings-actions">
          <button class="btn btn-ghost btn-sm" onclick="editAthlete('${id}')">Edit</button>
        </div>
      </td>
    `;

    tbody.appendChild(row);
  });
}

async function toggleAthleteActive(athleteId, isActive) {
  try {
    const result = isActive
      ? await pywebview.api.restore_athlete(athleteId)
      : await pywebview.api.archive_athlete(athleteId);
    if (result.ok) {
      if (window.log) window.log(result.msg, 'ok');
      if (selectedSettingsRosterId) {
        loadSettingsAthletesForRoster(selectedSettingsRosterId);
      }
    } else {
      if (window.log) window.log(result.msg, 'err');
      // Revert the toggle on failure
      renderSettingsAthletes();
    }
  } catch (e) {
    if (window.log) window.log('Error updating athlete: ' + e.message, 'err');
    renderSettingsAthletes();
  }
}

// ============================================================
// CSV IMPORT AND ATHLETE ACTIONS
// ============================================================

async function importAthletesModal() {
  if (!selectedSettingsRosterId) {
    alert('Please select a roster first.');
    return;
  }

  try {
    const result = await pywebview.api.pick_csv_file();
    if (!result || !result.path) {
      return;
    }

    const addResult = await pywebview.api.add_athletes_to_roster_from_csv(selectedSettingsRosterId, result.path);

    if (addResult.ok) {
      if (window.log) window.log(addResult.msg, 'ok');
      loadSettingsAthletesForRoster(selectedSettingsRosterId);
    } else {
      if (window.log) window.log(addResult.msg, 'err');
      alert('Failed to import athletes: ' + addResult.msg);
    }
  } catch (e) {
    if (window.log) window.log('Error importing athletes: ' + e.message, 'err');
    alert('Error importing athletes: ' + e.message);
  }
}

// ============================================================
// ADD / EDIT ATHLETE MODAL
// ============================================================

let _athleteModalMode = 'add'; // 'add' | 'edit'
let _editingAthleteId = null;

function openAddAthleteModal() {
  if (!selectedSettingsRosterId) {
    log('Select a roster before adding athletes.', 'err');
    return;
  }
  _athleteModalMode = 'add';
  _editingAthleteId = null;
  document.getElementById('athlete-modal-title').textContent        = 'Add Athlete';
  document.getElementById('athlete-modal-submit-btn').textContent   = 'Add Athlete';
  document.getElementById('athlete-modal-fname').value  = '';
  document.getElementById('athlete-modal-lname').value  = '';
  document.getElementById('athlete-modal-rfid').value   = '';
  document.getElementById('athlete-modal-rfid').disabled = false;
  document.getElementById('athlete-modal-nfc').value    = '';
  document.getElementById('athlete-modal-email').value  = '';
  _clearAthleteModalError();
  updateAthleteModalBtn();
  document.getElementById('athlete-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('athlete-modal-fname').focus(), 50);
}

function editAthlete(athleteId) {
  const athlete = settingsAthletes.find(a => a.id === athleteId);
  if (!athlete) return;
  _athleteModalMode = 'edit';
  _editingAthleteId = athleteId;
  document.getElementById('athlete-modal-title').textContent        = 'Edit Athlete';
  document.getElementById('athlete-modal-submit-btn').textContent   = 'Save Changes';
  document.getElementById('athlete-modal-fname').value  = athlete.first_name || athlete.name  || '';
  document.getElementById('athlete-modal-lname').value  = athlete.last_name  || athlete.lname || '';
  document.getElementById('athlete-modal-rfid').value   = athlete.finish_tag || athlete.lap_id || '';
  document.getElementById('athlete-modal-rfid').disabled = true; // RFID is the unique key — can't change
  document.getElementById('athlete-modal-nfc').value    = athlete.start_tag  || athlete.start_id || '';
  document.getElementById('athlete-modal-email').value  = athlete.email || '';
  _clearAthleteModalError();
  updateAthleteModalBtn();
  document.getElementById('athlete-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('athlete-modal-fname').focus(), 50);
}

function closeAthleteModal() {
  document.getElementById('athlete-modal').style.display = 'none';
}

function updateAthleteModalBtn() {
  const fname = document.getElementById('athlete-modal-fname').value.trim();
  const rfid  = document.getElementById('athlete-modal-rfid').value.trim();
  const ok = !!fname && (_athleteModalMode === 'edit' || !!rfid);
  document.getElementById('athlete-modal-submit-btn').disabled = !ok;
}

function _showAthleteModalError(msg) {
  const el = document.getElementById('athlete-modal-error');
  el.textContent = msg;
  el.style.display = 'block';
}

function _clearAthleteModalError() {
  const el = document.getElementById('athlete-modal-error');
  el.textContent = '';
  el.style.display = 'none';
}

async function submitAthleteModal() {
  const data = {
    first_name: document.getElementById('athlete-modal-fname').value.trim(),
    last_name:  document.getElementById('athlete-modal-lname').value.trim(),
    rfid_tag:   document.getElementById('athlete-modal-rfid').value.trim(),
    nfc_tag:    document.getElementById('athlete-modal-nfc').value.trim(),
    email:      document.getElementById('athlete-modal-email').value.trim(),
  };

  const submitBtn = document.getElementById('athlete-modal-submit-btn');
  submitBtn.disabled = true;
  _clearAthleteModalError();

  const result = _athleteModalMode === 'add'
    ? await pywebview.api.add_athlete_to_roster(selectedSettingsRosterId, data)
    : await pywebview.api.update_athlete(_editingAthleteId, data);

  if (!result.ok) {
    _showAthleteModalError(result.msg || 'Operation failed.');
    submitBtn.disabled = false;
    return;
  }

  log(result.msg, 'ok');
  closeAthleteModal();
  loadSettingsAthletesForRoster(selectedSettingsRosterId);
}

async function downloadCsvTemplate() {
  const result = await pywebview.api.download_csv_template();
  if (result.ok) log(result.msg, 'ok');
  else if (result.msg) log(result.msg, 'err');
}


// ============================================================
// INITIALIZATION
// ============================================================

window.addEventListener('DOMContentLoaded', () => {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.target.id === 'settings-screen' &&
          mutation.target.classList.contains('active')) {
        loadSettingsRosters();
      }
    });
  });

  const settingsScreen = document.getElementById('settings-screen');
  if (settingsScreen) {
    observer.observe(settingsScreen, {
      attributes: true,
      attributeFilter: ['class']
    });
  }

  // Close settings roster picker when clicking outside it
  document.addEventListener('click', e => {
    if (!document.getElementById('settings-roster-picker')?.contains(e.target)) {
      closeSettingsRosterDropdown();
    }
  });
});
