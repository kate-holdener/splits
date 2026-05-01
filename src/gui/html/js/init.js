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

window.addEventListener('pywebviewready', async () => {
  log('Splits ready.', 'info');
  await loadInitialState();
  checkForRecovery();
});

async function checkForRecovery() {
  try {
    const r = await pywebview.api.get_pending_recovery();
    if (!r.hasPendingRecovery) return;
    const started = r.started_at
      ? new Date(r.started_at).toLocaleTimeString() : '(unknown time)';
    const w = r.workout;
    const desc = w ? `${w.interval_distance}m \u00d7 ${w.laps_per_interval} laps, ${w.rest_time}s rest` : 'Unknown workout';
    document.getElementById('recovery-detail').innerHTML =
      `A workout from <strong>${started}</strong> was interrupted.<br>` +
      `Workout: ${desc}&nbsp;&nbsp;|&nbsp;&nbsp;${r.athlete_count} athletes`;
    document.getElementById('recovery-modal').style.display = 'flex';
  } catch (e) {
    console.error('Recovery check failed:', e);
  }
}

async function resumeSession() {
  document.getElementById('recovery-modal').style.display = 'none';
  const r = await pywebview.api.resume_session();
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) {
    if (r.state) applyState(r.state);
    setSessionActive(true);
    _activateScreen('workout-screen');
  }
}

async function discardRecovery() {
  document.getElementById('recovery-modal').style.display = 'none';
  await pywebview.api.discard_recovery();
  log('Previous session discarded.', 'info');
}

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
document.getElementById('recovery-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('recovery-modal')) discardRecovery();
});
document.getElementById('confirm-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('confirm-modal')) {
    document.getElementById('confirm-modal-cancel').click();
  }
});
