// ============================================================
// INITIALISATION — runs after pywebview is ready
// ============================================================

async function loadInitialState() {
  try {
    const [state, seasonsResult] = await Promise.all([
      pywebview.api.get_state(),
      pywebview.api.list_seasons()
    ]);
    applyState(state);
    if (seasonsResult.seasons) renderSeasonsList(seasonsResult.seasons);

    if (state.athletesLoaded && state.athleteCount > 0) {
      loadAthleteList();
      if (state.currentSeason) {
        log(`Season '${state.currentSeason.name}' loaded with ${state.athleteCount} athletes.`, 'info');
      }
    } else if (state.currentSeason) {
      log(`Season '${state.currentSeason.name}' is active (no athletes yet).`, 'info');
    }
  } catch (e) {
    console.error('Error loading initial state:', e);
  }
}

window.addEventListener('pywebviewready', () => {
  log('IntervalTrack ready.', 'info');
  loadInitialState();
});

// Close season picker when clicking outside it
document.addEventListener('click', e => {
  if (!document.getElementById('season-picker')?.contains(e.target)) {
    closeSeasonDropdown();
  }
});

// Tooltip follows the mouse
document.addEventListener('mousemove', e => {
  if (document.getElementById('perf-tooltip').style.display !== 'none') positionTooltip(e);
});

// Season modal: Escape to close, Enter to submit
document.addEventListener('keydown', e => {
  const modal = document.getElementById('season-modal');
  if (modal && modal.style.display === 'flex') {
    if (e.key === 'Escape') closeSeasonModal();
    if (e.key === 'Enter' && document.getElementById('modal-season-name').value.trim()) {
      submitNewSeason();
    }
  }
});

// Close modal when clicking the dark overlay
document.getElementById('season-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('season-modal')) closeSeasonModal();
});
