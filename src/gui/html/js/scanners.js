// ============================================================
// SCANNERS MODAL
// ============================================================

// Switch the RFID section between three views:
//   'connected' — scanner is connected, show Disconnect button
//   'options'   — not connected, show Auto-detect + Manual setup buttons
//   'manual'    — manual config form with Connect + Cancel
function setRfidModalView(view) {
  const options          = document.getElementById('rfid-options');
  const manualForm       = document.getElementById('rfid-manual-form');
  const connectedActions = document.getElementById('rfid-connected-actions');
  if (!options || !manualForm || !connectedActions) return;
  options.style.display          = (view === 'options')   ? 'flex'  : 'none';
  manualForm.style.display       = (view === 'manual')    ? 'block' : 'none';
  connectedActions.style.display = (view === 'connected') ? 'flex'  : 'none';
}

function updateNfcBtn(connected) {
  const btn = document.getElementById('nfc-btn');
  if (!btn) return;
  if (connected) {
    btn.textContent = 'Disconnect';
    btn.className   = 'btn btn-ghost btn-sm';
    btn.onclick     = disconnectNfc;
  } else {
    btn.textContent = 'Connect';
    btn.className   = 'btn btn-primary btn-sm';
    btn.onclick     = connectNfc;
  }
}

async function openScannersModal() {
  document.getElementById('scanners-modal').style.display = 'flex';

  const info  = await pywebview.api.get_rfid_connection_info();
  const state = await pywebview.api.get_state();

  // RFID
  const rfidStatusEl = document.getElementById('rfid-status-text');
  const nameEl       = document.getElementById('rfid-name');

  if (info.connected) {
    nameEl.textContent    = `${info.protocol.toUpperCase()} RFID`;
    rfidStatusEl.innerHTML = `Connected <span style="font-weight:normal">(${info.address}:${info.port})</span>`;
    rfidStatusEl.className = 'connector-status ok';
    setRfidModalView('connected');
  } else {
    nameEl.textContent = 'RFID Scanner';
    if (state.rfidFailed) {
      rfidStatusEl.textContent = 'Connection failed';
      rfidStatusEl.className   = 'connector-status fail';
    } else {
      rfidStatusEl.textContent = 'Not connected';
      rfidStatusEl.className   = 'connector-status idle';
    }
    setRfidModalView('options');
  }

  // NFC
  updateConnector('nfc-status-text', state.nfcConnected, state.nfcFailed);
  updateNfcBtn(state.nfcConnected);

  // Topbar button color
  updateScannersBtnColor(info.connected, state.nfcConnected);
}

function closeScannersModal() {
  document.getElementById('scanners-modal').style.display = 'none';
}

// Close when clicking the dark overlay
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('scanners-modal').addEventListener('click', e => {
    if (e.target === document.getElementById('scanners-modal')) closeScannersModal();
  });
});

// ============================================================
// RFID CONNECTION STATUS DISPLAY
// ============================================================

function updateScannersBtnColor(rfidConnected, nfcConnected) {
  const btn = document.getElementById('scanners-btn');
  if (!btn) return;
  btn.className = (rfidConnected && nfcConnected) ? 'btn btn-sm btn-success' : 'btn btn-sm btn-danger';
}

function updateRfidStatus(result, connectionDetails = null) {
  const statusText = document.getElementById('rfid-status-text');
  if (result.ok) {
    let connectedText = 'Connected';
    if (connectionDetails) {
      connectedText += ` <span style="font-weight:normal">(${connectionDetails.address}:${connectionDetails.port} via ${connectionDetails.protocol.toUpperCase()})</span>`;
    }
    statusText.innerHTML  = connectedText;
    statusText.className  = 'connector-status ok';
  } else {
    statusText.innerHTML = `<span style="font-weight:normal">${result.msg}</span>`;
    statusText.className = 'connector-status fail';
  }
}

// ============================================================
// RFID MODAL VIEW TRANSITIONS
// ============================================================

function showRfidManualConfig() {
  setRfidModalView('manual');
}

function cancelRfidManualConfig() {
  setRfidModalView('options');
}

// ============================================================
// RFID RECONNECT — called on first visit to workout screen
// ============================================================

async function reconnectRfid() {
  log('Attempting reconnect to RFID scanner…', 'info');
  const r = await pywebview.api.try_auto_connect_rfid();
  if (r.ok) {
    log(r.msg, 'ok');
  } else {
    log('Reconnection failed — open Scanners to auto-detect or configure manually.', 'warn');
  }
  if (r.state) {
    applyState(r.state);
    const info = await pywebview.api.get_rfid_connection_info();
    updateScannersBtnColor(info.connected, r.state.nfcConnected);
  }
}

// ============================================================
// RFID AUTO-DETECT
// ============================================================

async function connectRfidAutoDetect() {
  const autoBtn   = document.getElementById('rfid-autodetect-btn');
  const manualBtn = document.querySelector('#rfid-options .btn-ghost');
  if (autoBtn)   autoBtn.disabled   = true;
  if (manualBtn) manualBtn.disabled = true;

  log('Auto-discovering RFID scanner…', 'info');
  const r = await pywebview.api.connect_rfid();
  log(r.msg, r.ok ? 'ok' : 'err');

  if (r.ok) {
    const cd     = r.connection_details || null;
    const nameEl = document.getElementById('rfid-name');
    if (cd && nameEl) nameEl.textContent = `${cd.protocol.toUpperCase()} RFID`;
    updateRfidStatus(r, cd);
    setRfidModalView('connected');
  } else {
    updateRfidStatus(r);
    if (autoBtn)   autoBtn.disabled   = false;
    if (manualBtn) manualBtn.disabled = false;
  }

  if (r.state) applyState(r.state);
}

// ============================================================
// RFID MANUAL CONNECT
// ============================================================

async function connectRfidManualSubmit() {
  const address  = (document.getElementById('rfid-address').value || '').trim();
  const port     = parseInt(document.getElementById('rfid-port').value) || 5084;
  const protocol = document.getElementById('rfid-protocol').value;

  if (!address) {
    log('Please enter an IP address for the RFID scanner.', 'err');
    return;
  }

  const btn = document.getElementById('rfid-manual-connect-btn');
  if (btn) btn.disabled = true;

  const connectionDetails = { address, port, protocol };
  log(`Connecting to RFID scanner at ${address}:${port} using ${protocol.toUpperCase()}…`, 'info');
  const r = await pywebview.api.connect_rfid_manual(address, port, protocol);
  log(r.msg, r.ok ? 'ok' : 'err');

  if (r.ok) {
    const nameEl = document.getElementById('rfid-name');
    if (nameEl) nameEl.textContent = `${protocol.toUpperCase()} RFID`;
    updateRfidStatus(r, connectionDetails);
    setRfidModalView('connected');
  } else {
    updateRfidStatus(r);
  }

  if (r.state) applyState(r.state);
  if (btn) btn.disabled = false;
}

// ============================================================
// RFID DISCONNECT
// ============================================================

async function disconnectRfid() {
  const btn = document.querySelector('#rfid-connected-actions .btn');
  if (btn) btn.disabled = true;

  log('Disconnecting RFID scanner…', 'info');
  const r = await pywebview.api.disconnect_rfid();
  log(r.msg, r.ok ? 'ok' : 'err');

  if (r.ok) {
    const nameEl       = document.getElementById('rfid-name');
    const rfidStatusEl = document.getElementById('rfid-status-text');
    if (nameEl) nameEl.textContent = 'RFID Scanner';
    if (rfidStatusEl) {
      rfidStatusEl.textContent = 'Not connected';
      rfidStatusEl.className   = 'connector-status idle';
    }
    setRfidModalView('options');
  }

  if (r.state) {
    applyState(r.state);
    updateScannersBtnColor(false, r.state.nfcConnected);
  }
  if (btn) btn.disabled = false;
}

// ============================================================
// NFC CONNECT / DISCONNECT
// ============================================================

async function connectNfc() {
  const btn = document.getElementById('nfc-btn');
  if (btn) btn.disabled = true;
  log('Connecting to NFC scanner…', 'info');
  const r = await pywebview.api.connect_nfc();
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
  if (r.ok) updateNfcBtn(true);
  if (btn) btn.disabled = false;
}

async function disconnectNfc() {
  const btn = document.getElementById('nfc-btn');
  if (btn) btn.disabled = true;
  log('Disconnecting NFC scanner…', 'info');
  const r = await pywebview.api.disconnect_nfc();
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
  if (r.ok) updateNfcBtn(false);
  if (btn) btn.disabled = false;
}

async function autoConnectScanners() {
  log('Setup complete — auto-connecting scanners…', 'info');
  log('Auto-discovering RFID scanner…', 'info');
  const rfidResult       = await pywebview.api.connect_rfid();
  log(rfidResult.msg, rfidResult.ok ? 'ok' : 'err');
  const connectionDetails = rfidResult.ok && rfidResult.connection_details ? rfidResult.connection_details : null;
  updateRfidStatus(rfidResult, connectionDetails);
  if (rfidResult.state) applyState(rfidResult.state);
  await connectNfc();
}
