// ============================================================
// SETUP TAB — athlete list (roster view) + workout config
// ============================================================

async function loadAthleteList() {
  const r     = await pywebview.api.list_athletes();
  const tbody = document.getElementById('athlete-tbody');
  const wrap  = document.getElementById('athletes-ok');
  if (!r.ok || !r.athletes.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'block';
  tbody.innerHTML = r.athletes.map(a => `<tr>
    <td>${a.first_name || '—'}</td>
    <td>${a.last_name  || '—'}</td>
    <td><code>${a.finish_tag || '—'}</code></td>
    <td><code>${a.start_tag  || '—'}</code></td>
  </tr>`).join('');
}

async function configureWorkout() {
  const dist = document.getElementById('wk-distance').value;
  const laps = document.getElementById('wk-laps').value;
  const rest = document.getElementById('wk-rest').value;
  const r    = await pywebview.api.configure_workout(dist, laps, rest);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);
}
