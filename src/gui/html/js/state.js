// ============================================================
// UTILITIES
// ============================================================

function digitsOnly(el) {
  el.value = el.value.replace(/[^0-9]/g, '');
}

// ============================================================
// SCREEN NAVIGATION
// ============================================================

let _workoutRefreshTimer = null;
let _workoutScreenVisited = false;
let _sessionActive = false;

function setSessionActive(val) {
  _sessionActive = val;
  const tile    = document.getElementById('settings-tile');
  const tileSub = document.getElementById('settings-tile-sub');
  if (!tile || !tileSub) return;
  if (val) {
    tile.classList.add('locked');
    tileSub.innerHTML = 'Not available during an active workout.<br>Terminate the workout to update settings.';
  } else {
    tile.classList.remove('locked');
    tileSub.innerHTML = 'Manage rosters, athletes<br>and system configuration';
  }
}

function goTo(screenId) {
  if (_workoutRefreshTimer) {
    clearInterval(_workoutRefreshTimer);
    _workoutRefreshTimer = null;
  }
  if (screenId === 'workout-screen' && !_sessionActive) {
    openSessionSetup();
    return;
  }
  if (screenId === 'settings-screen' && _sessionActive) {
    const tile = document.getElementById('settings-tile');
    if (tile) {
      tile.classList.add('locked-flash');
      setTimeout(() => tile.classList.remove('locked-flash'), 500);
    }
    return;
  }
  _activateScreen(screenId);
}

function _activateScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
  if (screenId === 'workout-screen') {
    if (!_workoutScreenVisited) {
      _workoutScreenVisited = true;
      reconnectRfid();
      connectNfc();
    }
    loadWorkoutAthletes();
    _workoutRefreshTimer = setInterval(loadWorkoutAthletes, 1000);
  }
  if (screenId === 'reports-screen') {
    loadSessions();
  }
}


// ============================================================
// STATE — pills, tab dots, connector labels
// ============================================================

let _autoConnectAttempted = false;

function applyState(s) {
  if (!s) return;
  updateRosterUI(s.currentRoster || null);

  updateRfidConnector(s);
  updateConnector('nfc-status-text', s.nfcConnected, s.nfcFailed);

  const setupOk = s.athletesLoaded && s.workoutConfigured;
  if (setupOk && !_autoConnectAttempted) {
    //_autoConnectAttempted = true;
    //autoConnectScanners();
  }
}



function updateConnector(id, ok, failed) {
  const el = document.getElementById(id);
  if (!el) return;
  if (ok)          { el.textContent = 'Connected';         el.className = 'connector-status ok'; }
  else if (failed) { el.textContent = 'Connection failed'; el.className = 'connector-status fail'; }
  else             { el.textContent = 'Not connected';     el.className = 'connector-status idle'; }
}

function updateRfidConnector(state) {
  const statusEl = document.getElementById('rfid-status-text');
  const nameEl   = document.getElementById('rfid-name');
  if (!statusEl || !nameEl) return;

  if (state.rfidConnected) {
    if (state.rfidProtocol && state.rfidAddress) {
      const port = state.rfidPort ? `:${state.rfidPort}` : '';
      nameEl.textContent  = `${state.rfidProtocol.toUpperCase()} RFID`;
      statusEl.innerHTML  = `Connected <span style="font-weight:normal">(${state.rfidAddress}${port})</span>`;
    } else {
      nameEl.textContent  = 'RFID Scanner';
      statusEl.textContent = 'Connected';
    }
    statusEl.className = 'connector-status ok';
    if (typeof setRfidModalView === 'function') setRfidModalView('connected');
  } else {
    nameEl.textContent = 'RFID Scanner';
    if (state.rfidFailed) {
      statusEl.textContent = 'Connection failed';
      statusEl.className   = 'connector-status fail';
    } else {
      statusEl.textContent = 'Not connected';
      statusEl.className   = 'connector-status idle';
    }
    // Don't reset to options view if the user is currently in manual config mode
    const manualForm = document.getElementById('rfid-manual-form');
    const isManual   = manualForm && manualForm.style.display !== 'none';
    if (!isManual && typeof setRfidModalView === 'function') setRfidModalView('options');
  }
}
