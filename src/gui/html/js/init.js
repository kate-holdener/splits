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
      const selectedId = state.currentWorkoutConfig ? state.currentWorkoutConfig.id : null;
      renderWorkoutsList(_savedWorkouts, selectedId);

      if (state.currentWorkoutConfig && state.currentWorkoutConfig.name) {
        const label = document.getElementById('workout-selected-label');
        label.textContent = state.currentWorkoutConfig.name;
        label.classList.remove('placeholder');
      }
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

// Close roster picker when clicking outside it
document.addEventListener('click', e => {
  if (!document.getElementById('roster-picker')?.contains(e.target)) {
    closeRosterDropdown();
  }
  if (!document.getElementById('workout-picker')?.contains(e.target)) {
    closeWorkoutDropdown();
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
});

// Close modal when clicking the dark overlay
document.getElementById('roster-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('roster-modal')) closeRosterModal();
});
document.getElementById('workout-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('workout-modal')) closeNewWorkoutModal();
});
