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

function goTo(screenId) {
  if (_workoutRefreshTimer) {
    clearInterval(_workoutRefreshTimer);
    _workoutRefreshTimer = null;
  }
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
  if (screenId === 'workout-screen') {
    loadWorkoutAthletes();
    _workoutRefreshTimer = setInterval(loadWorkoutAthletes, 1000);
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
    _autoConnectAttempted = true;
    autoConnectScanners();
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
  const statusEl     = document.getElementById('rfid-status-text');
  const nameEl       = document.getElementById('rfid-name');
  const addressGroup = document.getElementById('rfid-address-group');
  const connectBtn   = document.getElementById('rfid-btn');
  if (!statusEl || !nameEl || !addressGroup || !connectBtn) return;

  if (state.rfidConnected) {
    statusEl.textContent = 'Connected';
    statusEl.className   = 'connector-status ok';
    if (state.rfidProtocol && state.rfidAddress) {
      const port = state.rfidPort ? `:${state.rfidPort}` : '';
      nameEl.textContent = `${state.rfidProtocol.toUpperCase()} RFID (${state.rfidAddress}${port})`;
    } else {
      nameEl.textContent = 'RFID Scanner';
    }
    addressGroup.style.display = 'none';
    connectBtn.textContent = 'Disconnect';
    connectBtn.onclick = disconnectRfid;
  } else if (state.rfidFailed) {
    statusEl.textContent = 'Connection failed';
    statusEl.className   = 'connector-status fail';
    nameEl.textContent   = 'RFID Scanner';
    addressGroup.style.display = 'block';
    connectBtn.textContent = 'Connect';
    connectBtn.onclick = connectRfid;
  } else {
    statusEl.textContent = 'Not connected';
    statusEl.className   = 'connector-status idle';
    nameEl.textContent   = 'RFID Scanner';
    addressGroup.style.display = 'block';
    connectBtn.textContent = 'Connect';
    connectBtn.onclick = connectRfid;
  }
}
