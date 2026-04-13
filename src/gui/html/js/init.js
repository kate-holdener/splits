// ============================================================
// INITIALISATION — runs after pywebview is ready
// ============================================================

async function loadInitialState() {
  try {
    const [state, rostersResult] = await Promise.all([
      pywebview.api.get_state(),
      pywebview.api.list_rosters()
    ]);
    applyState(state);
    if (rostersResult.rosters) renderRostersList(rostersResult.rosters);

    if (state.athletesLoaded && state.athleteCount > 0 && state.currentRoster) {
      log(`Roster '${state.currentRoster.name}' loaded with ${state.athleteCount} athletes.`, 'info');
    } else if (state.currentRoster) {
      log(`Roster '${state.currentRoster.name}' is active (no athletes yet).`, 'info');
    }
  } catch (e) {
    console.error('Error loading initial state:', e);
  }
}

window.addEventListener('pywebviewready', () => {
  log('IntervalTrack ready.', 'info');
  loadInitialState();
});

// Close roster picker when clicking outside it
document.addEventListener('click', e => {
  if (!document.getElementById('roster-picker')?.contains(e.target)) {
    closeRosterDropdown();
  }
});

// Tooltip follows the mouse
document.addEventListener('mousemove', e => {
  if (document.getElementById('perf-tooltip').style.display !== 'none') positionTooltip(e);
});

// Roster modal: Escape to close, Enter to submit
document.addEventListener('keydown', e => {
  const modal = document.getElementById('roster-modal');
  if (modal && modal.style.display === 'flex') {
    if (e.key === 'Escape') closeRosterModal();
    if (e.key === 'Enter' && document.getElementById('modal-roster-name').value.trim()) {
      submitNewRoster();
    }
  }
});

// Close modal when clicking the dark overlay
document.getElementById('roster-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('roster-modal')) closeRosterModal();
});
