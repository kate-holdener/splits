// ============================================================
// SETTINGS SCREEN — Roster and Athlete Management
// ============================================================

let settingsRosters = [];
let settingsAthletes = [];
let selectedSettingsRosterId = null;

let _activeScanInterval = null;

function _cancelActiveScan() {
  if (_activeScanInterval) {
    clearInterval(_activeScanInterval);
    _activeScanInterval = null;
  }
  pywebview.api.cancel_nfc_capture().catch(() => {});
}

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

  if (!await showConfirm(
    `This will hide "${roster.name}" from normal views.`,
    { title: `Archive "${roster.name}"?`, confirmText: 'Archive' }
  )) return;

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
  _cancelActiveScan();
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

    const nfcCell = athlete.start_tag
      ? `<td><code>${escapeHtml(athlete.start_tag)}</code></td>`
      : `<td style="white-space:nowrap">
           <button class="btn btn-ghost btn-sm" id="nfc-scan-btn-${id}"
                   onclick="scanNfcForAthlete('${id}')"
                   ${_sessionActive ? 'disabled title="Workout in progress"' : ''}>
             Scan
           </button>
           <span id="nfc-scan-status-${id}" style="font-size:12px;color:var(--muted);margin-left:6px"></span>
         </td>`;

    row.innerHTML = `
      <td><strong>${escapeHtml(fullName)}</strong></td>
      <td style="color:${athlete.email ? 'var(--text)' : 'var(--muted)'};font-size:13px">
        ${escapeHtml(athlete.email || '—')}
      </td>
      <td><code>${escapeHtml(athlete.finish_tag || '-')}</code></td>
      ${nfcCell}
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
// NFC TAG SCAN CAPTURE
// ============================================================

async function scanNfcForAthlete(athleteId) {
  _cancelActiveScan();

  const btn = document.getElementById(`nfc-scan-btn-${athleteId}`);
  const status = document.getElementById(`nfc-scan-status-${athleteId}`);

  btn.disabled = true;
  status.textContent = 'Waiting…';

  const startResult = await pywebview.api.start_nfc_capture();
  if (!startResult.ok) {
    status.textContent = startResult.msg || 'Failed to start scan.';
    btn.disabled = false;
    return;
  }

  let attempts = 0;
  const maxAttempts = 32; // 32 × 500ms = 16s (matches 15s backend timeout + buffer)
  _activeScanInterval = setInterval(async () => {
    attempts++;
    const result = await pywebview.api.poll_nfc_capture();

    if (result.pending) {
      if (attempts >= maxAttempts) {
        _cancelActiveScan();
        status.textContent = 'Timed out.';
        btn.disabled = false;
      }
      return;
    }

    _cancelActiveScan();

    if (!result.ok) {
      status.textContent = result.msg || 'Scan failed.';
      btn.disabled = false;
      return;
    }

    const athlete = settingsAthletes.find(a => a.id === athleteId);
    const saveResult = await pywebview.api.update_athlete(athleteId, {
      first_name: athlete.first_name || athlete.name  || '',
      last_name:  athlete.last_name  || athlete.lname || '',
      rfid_tag:   athlete.finish_tag || athlete.id    || '',
      nfc_tag:    result.tag,
      email:      athlete.email || '',
    });

    if (saveResult.ok) {
      if (window.log) window.log(`NFC tag assigned to ${athlete.first_name || athlete.name}.`, 'ok');
      loadSettingsAthletesForRoster(selectedSettingsRosterId);
    } else {
      status.textContent = saveResult.msg || 'Failed to save.';
      btn.disabled = false;
    }
  }, 500);
}

// ============================================================
// GMAIL SIGN-IN  (topbar of the Reports screen)
// ============================================================

let _gmailPollInterval = null;
let _gmailSignedIn = false;

function _renderGmailStatus(status) {
  _gmailSignedIn = !!status.signed_in;

  const label     = document.getElementById('reports-gmail-label');
  const signinBtn = document.getElementById('reports-gmail-signin-btn');
  const signoutBtn = document.getElementById('reports-gmail-signout-btn');

  if (status.signed_in) {
    if (label) { label.textContent = status.email || ''; }
    if (signinBtn)  signinBtn.style.display  = 'none';
    if (signoutBtn) signoutBtn.style.display = 'inline-flex';
  } else {
    if (label) { label.textContent = ''; }
    if (signinBtn)  signinBtn.style.display  = 'inline-flex';
    if (signoutBtn) signoutBtn.style.display = 'none';
  }

  // Keep the Email Reports button in sync.
  _updateGenerateBtn();
}

function loadGmailAuthStatus() {
  pywebview.api.get_gmail_auth_status().then(_renderGmailStatus).catch(() => {});
}

function startGmailSignIn() {
  const signinBtn = document.getElementById('reports-gmail-signin-btn');
  const label     = document.getElementById('reports-gmail-label');
  if (signinBtn) signinBtn.disabled = true;
  if (label) label.textContent = 'Opening browser…';

  pywebview.api.start_gmail_sign_in().then(result => {
    if (!result.ok) {
      if (label) label.textContent = result.msg || 'Sign-in failed.';
      if (signinBtn) signinBtn.disabled = false;
      return;
    }
    if (label) label.textContent = 'Waiting for sign-in…';
    _gmailPollInterval = setInterval(_pollGmailSignIn, 1500);
  }).catch(() => {
    if (label) label.textContent = '';
    if (signinBtn) signinBtn.disabled = false;
  });
}

function _pollGmailSignIn() {
  pywebview.api.poll_gmail_sign_in().then(result => {
    const signinBtn = document.getElementById('reports-gmail-signin-btn');
    if (!result.ok) {
      clearInterval(_gmailPollInterval);
      _gmailPollInterval = null;
      if (signinBtn) signinBtn.disabled = false;
      _renderGmailStatus({ signed_in: false, email: null });
      return;
    }
    if (result.done) {
      clearInterval(_gmailPollInterval);
      _gmailPollInterval = null;
      if (signinBtn) signinBtn.disabled = false;
      _renderGmailStatus({ signed_in: true, email: result.email });
    }
  }).catch(() => {});
}

function gmailSignOut() {
  pywebview.api.gmail_sign_out().then(() => {
    _renderGmailStatus({ signed_in: false, email: null });
  }).catch(() => {});
}

// ============================================================
// INITIALIZATION
// ============================================================

window.addEventListener('DOMContentLoaded', () => {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      const id = mutation.target.id;
      const active = mutation.target.classList.contains('active');
      if (id === 'settings-screen') {
        if (active) loadSettingsRosters();
        else _cancelActiveScan();
      } else if (id === 'reports-screen' && active) {
        loadGmailAuthStatus();
      }
    });
  });

  ['settings-screen', 'reports-screen'].forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el, { attributes: true, attributeFilter: ['class'] });
  });

  // Close settings roster picker when clicking outside it
  document.addEventListener('click', e => {
    if (!document.getElementById('settings-roster-picker')?.contains(e.target)) {
      closeSettingsRosterDropdown();
    }
  });
});
