// ============================================================
// UTILITIES
// ============================================================

function digitsOnly(el) {
  el.value = el.value.replace(/[^0-9]/g, '');
}

// ============================================================
// SCREEN NAVIGATION
// ============================================================

function goTo(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
}

// ============================================================
// TAB SWITCHING
// ============================================================

let _workoutRefreshTimer = null;

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('tc-' + name).classList.add('active');

  if (_workoutRefreshTimer) {
    clearInterval(_workoutRefreshTimer);
    _workoutRefreshTimer = null;
  }

  if (name === 'workout') {
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
  setPill('pill-athletes', s.athletesLoaded, s.athleteCount + ' Athletes');
  setPill('pill-workout',  s.workoutConfigured, 'Workout Set');
  setPill('pill-rfid',     s.rfidConnected, 'RFID', s.rfidFailed);
  setPill('pill-nfc',      s.nfcConnected,  'NFC',  s.nfcFailed);

  updateSeasonUI(s.currentSeason || null);

  const setupOk     = s.athletesLoaded && s.workoutConfigured;
  const scannersOk  = s.rfidConnected && s.nfcConnected;
  const scannersFail = s.rfidFailed || s.nfcFailed;

  setTabState('tab-setup',
    setupOk ? 'ready' : (s.athletesLoaded || s.workoutConfigured ? 'partial' : ''));
  setTabState('tab-scanners',
    scannersOk ? 'ready' : (scannersFail ? 'error' : ''));
  setTabState('tab-workout',
    (setupOk && scannersOk) ? 'ready' : '');

  const gc = document.getElementById('group-count');
  if (gc) gc.textContent = s.groupCount || 0;

  updateRfidConnector(s);
  updateConnector('nfc-status-text', s.nfcConnected, s.nfcFailed);

  if (setupOk && !_autoConnectAttempted) {
    _autoConnectAttempted = true;
    autoConnectScanners();
  }
}

function setPill(id, ok, label, failed = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = ok ? label : (failed ? 'FAILED' : label.split(' ')[0]);
  el.className = 'pill ' + (ok ? 'ok' : (failed ? 'fail' : 'idle'));
}

function setTabState(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('ready', 'partial', 'error');
  if (state) el.classList.add(state);
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
