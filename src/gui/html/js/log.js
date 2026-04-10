// ============================================================
// LOG BAR
// ============================================================

function log(msg, type = 'info') {
  const body = document.getElementById('log-body');
  const ts   = new Date().toLocaleTimeString();
  const div  = document.createElement('div');
  div.className = `log-entry ${type}`;
  div.innerHTML = `<span class="ts">${ts}</span><span class="msg">${msg}</span>`;
  body.prepend(div);
}

function clearLog() {
  document.getElementById('log-body').innerHTML = '';
}

function toggleLog() {
  document.getElementById('log-bar').classList.toggle('collapsed');
}
