/**
 * IntervalTrack — shared theme logic.
 * Loaded by both index.html and resting.html.
 * The toggle button lives in index.html only; resting.html receives live
 * updates when the Python backend calls evaluate_js('applyTheme(...)').
 * Preference is stored in the Python backend (PyWebViewAPI._theme) so it
 * works correctly inside pywebview without relying on localStorage.
 */

function applyTheme(mode) {
  const toggle = document.getElementById('theme-toggle');
  if (mode === 'light') {
    document.body.classList.add('light-mode');
    if (toggle) toggle.textContent = '🌙';
  } else {
    document.body.classList.remove('light-mode');
    if (toggle) toggle.textContent = '☀';
  }
}

function toggleTheme() {
  const isLight = document.body.classList.contains('light-mode');
  const next = isLight ? 'dark' : 'light';
  applyTheme(next);
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.set_theme(next);
  }
}

// Ask the Python backend for the saved theme as soon as the API is ready.
function tryApplyTheme() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.get_theme) {
    window.pywebview.api.get_theme().then(function (mode) {
      applyTheme(mode || 'light');
    });
  } else {
    setTimeout(tryApplyTheme, 100);
  }
}

window.addEventListener('pywebviewready', tryApplyTheme);
tryApplyTheme();
