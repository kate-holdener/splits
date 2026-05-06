// ============================================================
// WORKOUT CONFIG
// ============================================================

async function configureWorkout() {
  const dist = document.getElementById('wk-distance').value;
  const laps = document.getElementById('wk-laps').value;
  const rest = document.getElementById('wk-rest').value;
  const r    = await pywebview.api.configure_workout(dist, laps, rest, _currentRosterId);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
}
