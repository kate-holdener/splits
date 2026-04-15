// ============================================================
// INITIALISATION — runs after pywebview is ready
// ============================================================

async function loadInitialState() {
  try {
    const [state, rostersResult, workoutsResult, savedConfig] = await Promise.all([
      pywebview.api.get_state(),
      pywebview.api.list_rosters(),
      pywebview.api.list_workouts(),
      pywebview.api.get_saved_scanner_config()
    ]);
    applyState(state);
    if (rostersResult.rosters) renderRostersList(rostersResult.rosters);
    if (workoutsResult.ok) {
      _savedWorkouts = workoutsResult.workouts || [];
    }

    // Load saved scanner configuration into the manual config fields
    if (savedConfig) {
      document.getElementById('rfid-address').value = savedConfig.hostname;
      document.getElementById('rfid-port').value = savedConfig.port;
      document.getElementById('rfid-protocol').value = savedConfig.protocol;
    }

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

// Close setup modal pickers when clicking outside them
document.addEventListener('click', e => {
  if (!document.getElementById('setup-workout-picker')?.contains(e.target)) {
    closeSetupWorkoutDropdown();
  }
  if (!document.getElementById('setup-roster-picker')?.contains(e.target)) {
    closeSetupRosterDropdown();
  }
});

// Tooltip follows the mouse
document.addEventListener('mousemove', e => {
  if (document.getElementById('perf-tooltip').style.display !== 'none') positionTooltip(e);
});

// Roster modal: Escape to close, Enter to submit
document.addEventListener('keydown', e => {
  const rosterModal  = document.getElementById('roster-modal');
  const workoutModal = document.getElementById('workout-modal');
  if (rosterModal && rosterModal.style.display === 'flex') {
    if (e.key === 'Escape') closeRosterModal();
    if (e.key === 'Enter' && document.getElementById('modal-roster-name').value.trim()) {
      submitNewRoster();
    }
  }
  if (workoutModal && workoutModal.style.display === 'flex') {
    if (e.key === 'Escape') closeNewWorkoutModal();
  }
  const setupModal = document.getElementById('session-setup-modal');
  if (setupModal && setupModal.style.display === 'flex') {
    if (e.key === 'Escape') cancelSessionSetup();
  }
});

// Close modal when clicking the dark overlay
document.getElementById('roster-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('roster-modal')) closeRosterModal();
});
document.getElementById('workout-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('workout-modal')) closeNewWorkoutModal();
});
document.getElementById('session-setup-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('session-setup-modal')) cancelSessionSetup();
});
