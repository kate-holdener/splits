// ============================================================
// SCANNERS MODAL
// ============================================================

async function openScannersModal() {
  document.getElementById('scanners-modal').style.display = 'flex';

  const [info, state] = await Promise.all([
    pywebview.api.get_rfid_connection_info(),
    pywebview.api.get_state()
  ]);

  // RFID
  const rfidStatusEl = document.getElementById('rfid-status-text');
  const nameEl = document.getElementById('rfid-name');
  const configGroup = document.getElementById('rfid-config-group');
  const connectBtn = document.getElementById('rfid-btn');

  if (info.connected) {
    nameEl.textContent = `${info.protocol.toUpperCase()} RFID`;
    rfidStatusEl.innerHTML = `Connected <span style="font-weight:normal">(${info.address}:${info.port})</span>`;
    rfidStatusEl.className = 'connector-status ok';
    configGroup.style.display = 'none';
    connectBtn.textContent = 'Disconnect';
    connectBtn.onclick = disconnectRfid;
  } else {
    nameEl.textContent = 'RFID Scanner';
    rfidStatusEl.textContent = 'Not connected';
    rfidStatusEl.className = 'connector-status idle';
    configGroup.style.display = 'none';
    connectBtn.textContent = 'Connect';
    connectBtn.onclick = connectRfid;
  }

  // NFC
  updateConnector('nfc-status-text', state.nfcConnected, state.nfcFailed);

  // Topbar button color
  updateScannersBtnColor(info.connected, state.nfcConnected);
}

function updateScannersBtnColor(rfidConnected, nfcConnected) {
  const btn = document.getElementById('scanners-btn');
  if (!btn) return;
  if (rfidConnected && nfcConnected) {
    btn.className = 'btn btn-sm btn-success';
  } else {
    btn.className = 'btn btn-sm btn-danger';
  }
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

async function reconnectRfid() {
    // Reconnect to previously saved rfid scanner: try saved config
    log('Attempting reconnect to RFID scanner…', 'info');
    const r = await pywebview.api.try_auto_connect_rfid();

    if (r.ok) {
      log(r.msg, 'ok');
    } else {
      log('Reconnection failed, try auto-discovery or manual config', 'error');
    }

    if (r.state) {
      applyState(r.state);
      const info = await pywebview.api.get_rfid_connection_info();
      updateScannersBtnColor(info.connected, r.state.nfcConnected);
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
    // Auto-connect mode: try saved config first, then discovery
    log('Attempting auto-connect to RFID scanner…', 'info');
    r = await pywebview.api.try_auto_connect_rfid();
    
    if (r.ok) {
      log(r.msg, 'ok');
      // Extract connection details from the state if available
      if (r.state && r.state.rfidAddress && r.state.rfidPort && r.state.rfidProtocol) {
        connectionDetails = {
          address: r.state.rfidAddress,
          port: r.state.rfidPort,
          protocol: r.state.rfidProtocol
        };
      }
    } else {
      // Fallback to discovery if saved config failed
      log('Saved config failed, trying auto-discovery…', 'info');
      r = await pywebview.api.connect_rfid();
      log(r.msg, r.ok ? 'ok' : 'err');
      if (r.ok && r.connection_details) connectionDetails = r.connection_details;
    }
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
