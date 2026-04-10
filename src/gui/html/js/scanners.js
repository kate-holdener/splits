// ============================================================
// SCANNERS — RFID + NFC connection
// ============================================================

async function connectRfid() {
  document.getElementById('rfid-btn').disabled = true;
  const address = (document.getElementById('rfid-address').value || '').trim();
  if (!address) {
    log('Please enter an IP address for the RFID scanner.', 'err');
    document.getElementById('rfid-btn').disabled = false;
    return;
  }
  log(`Connecting to RFID scanner at ${address}…`, 'info');
  const r = await pywebview.api.connect_rfid_with_address(address);
  log(r.msg, r.ok ? 'ok' : 'err');
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
  if (rfidResult.state) applyState(rfidResult.state);
  document.getElementById('rfid-btn').disabled = false;
  await connectNfc();
}
