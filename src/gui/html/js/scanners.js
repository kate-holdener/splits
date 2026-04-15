// ============================================================
// SCANNERS MODAL
// ============================================================

function openScannersModal() {
  document.getElementById('scanners-modal').style.display = 'flex';
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

function updateRfidStatus(result, connectionDetails = null) {
  const statusText = document.getElementById('rfid-status-text');

  if (result.ok) {
    connectedText = 'Connected to '
    if (connectionDetails) {
      connectedText+= ` <span style="font-weight: normal;">${connectionDetails.address}:${connectionDetails.port} via ${connectionDetails.protocol.toUpperCase()}</span>`;
    }
    statusText.innerHTML = connectedText;
    statusText.className = 'connector-status ok';
  } else {
    statusText.innerHTML = `<span style="font-weight: normal;">${result.msg}</span>`;
    statusText.className = 'connector-status fail';
  }
}

// ============================================================
// SCANNERS — RFID + NFC connection
// ============================================================

function toggleRfidManualConfig() {
  const configGroup = document.getElementById('rfid-config-group');
  const btn = document.getElementById('rfid-manual-btn');
  
  if (configGroup.style.display === 'none') {
    configGroup.style.display = 'block';
    btn.textContent = 'Auto Connect';
  } else {
    configGroup.style.display = 'none';
    btn.textContent = 'Manual Config';
  }
}

async function connectRfid() {
  document.getElementById('rfid-btn').disabled = true;
  
  const configGroup = document.getElementById('rfid-config-group');
  const isManualMode = configGroup.style.display !== 'none';
  
  let r;
  let connectionDetails = null;

  if (isManualMode) {
    const address = (document.getElementById('rfid-address').value || '').trim();
    const port = parseInt(document.getElementById('rfid-port').value) || 5084;
    const protocol = document.getElementById('rfid-protocol').value;

    if (!address) {
      log('Please enter an IP address for the RFID scanner.', 'err');
      document.getElementById('rfid-btn').disabled = false;
      return;
    }

    connectionDetails = { address, port, protocol };
    log(`Connecting to RFID scanner at ${address}:${port} using ${protocol.toUpperCase()}…`, 'info');
    r = await pywebview.api.connect_rfid_manual(address, port, protocol);
    log(r.msg, r.ok ? 'ok' : 'err');
  } else {
    // Auto-connect mode
    log('Auto-discovering RFID scanner…', 'info');
    r = await pywebview.api.connect_rfid();
    log(r.msg, r.ok ? 'ok' : 'err');
    if (r.ok && r.connection_details) connectionDetails = r.connection_details;
  }

  updateRfidStatus(r, connectionDetails);
  if (r.state) applyState(r.state);
  document.getElementById('rfid-btn').disabled = false;
}

async function disconnectRfid() {
  log('Disconnect functionality not yet implemented.', 'info');
}

async function connectNfc() {
  document.getElementById('nfc-btn').disabled = true;
  log('Connecting to NFC scanner…', 'info');
  const r = await pywebview.api.connect_nfc();
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
  document.getElementById('nfc-btn').disabled = false;
}

async function autoConnectScanners() {
  log('Setup complete — auto-connecting scanners…', 'info');
  document.getElementById('rfid-btn').disabled = true;
  log('Auto-discovering RFID scanner…', 'info');
  const rfidResult = await pywebview.api.connect_rfid();
  log(rfidResult.msg, rfidResult.ok ? 'ok' : 'err');
  const connectionDetails = rfidResult.ok && rfidResult.connection_details ? rfidResult.connection_details : null;
  updateRfidStatus(rfidResult, connectionDetails);
  if (rfidResult.state) applyState(rfidResult.state);
  document.getElementById('rfid-btn').disabled = false;
  await connectNfc();
}
