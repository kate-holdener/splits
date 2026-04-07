/**
 * IntervalTrack — shared theme toggle logic.
 * Loaded by both index.html and resting.html.
 * Preference is persisted in localStorage under 'intervaltrack-theme'.
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
  localStorage.setItem('intervaltrack-theme', next);
  applyTheme(next);
}

// Apply saved theme after the DOM is fully parsed
document.addEventListener('DOMContentLoaded', function () {
  const saved = localStorage.getItem('intervaltrack-theme') || 'dark';
  applyTheme(saved);
});
