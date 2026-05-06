// ============================================================
// SAVED WORKOUTS — list management
// ============================================================

let _savedWorkouts = [];

async function loadWorkoutsList() {
  try {
    const r = await pywebview.api.list_workouts();
    if (r.ok) _savedWorkouts = r.workouts || [];
  } catch (e) {
    console.error('Error loading workouts:', e);
  }
}

// ============================================================
// SESSION SETUP MODAL
// ============================================================

let _setupSelectedWorkout  = null;
let _setupSelectedRosterId = null;

function openSessionSetup() {
  _setupSelectedWorkout  = null;
  _setupSelectedRosterId = null;

  // Reset workout label to placeholder
  const workoutLabel = document.getElementById('setup-workout-label');
  if (workoutLabel) { workoutLabel.textContent = '— Select a workout —'; workoutLabel.classList.add('placeholder'); }
  document.getElementById('setup-workout-trigger')?.classList.remove('open');

  const confirmBtn = document.getElementById('setup-confirm-btn');
  if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = 'Begin Session'; }

  _renderSetupWorkoutMenu();
  _renderSetupRosterMenu();
  _applySetupDefaults();

  document.getElementById('session-setup-modal').style.display = 'flex';
}

function cancelSessionSetup() {
  closeSetupWorkoutDropdown();
  closeSetupRosterDropdown();
  document.getElementById('session-setup-modal').style.display = 'none';
}

async function confirmSessionSetup() {
  if (!_setupSelectedWorkout || !_setupSelectedRosterId) return;

  const confirmBtn = document.getElementById('setup-confirm-btn');
  if (confirmBtn) { confirmBtn.disabled = true; }

  const { distance, laps, rest } = _setupSelectedWorkout;

  const wr = await pywebview.api.configure_workout(String(distance), String(laps), String(rest || 0), _setupSelectedRosterId);
  log(wr.msg, wr.ok ? 'ok' : 'err');
  if (wr.state) applyState(wr.state);

  const rr = await pywebview.api.select_roster(_setupSelectedRosterId);
  log(rr.msg, rr.ok ? 'ok' : 'err');
  if (rr.state) applyState(rr.state);

  await pywebview.api.start_timer();

  const lr = await pywebview.api.list_rosters();
  if (lr.rosters) {
    _savedRosters = lr.rosters;
    renderRostersList(lr.rosters);
  }

  setSessionActive(true);

  // Wait for scanner connections before showing workout screen
  if (confirmBtn) { confirmBtn.textContent = 'Connecting to scanners…'; }

  _workoutScreenVisited = true;
  await Promise.all([reconnectRfid(), connectNfc()]);

  // Both connections have settled — do one authoritative color update.
  // reconnectRfid() snapshots nfcConnected before connectNfc() finishes,
  // so reading state here avoids the race condition.
  const [_info, _state] = await Promise.all([
    pywebview.api.get_rfid_connection_info(),
    pywebview.api.get_state(),
  ]);
  updateScannersBtnColor(_info.connected, _state.nfcConnected);

  cancelSessionSetup();
  _activateScreen('workout-screen');
}

function _renderSetupWorkoutMenu() {
  const menu = document.getElementById('setup-workout-menu');
  if (!menu) return;
  menu.innerHTML = '';

  if (!_savedWorkouts || !_savedWorkouts.length) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:14px 18px;color:var(--muted);font-size:15px';
    empty.textContent = 'No saved workouts yet.';
    menu.appendChild(empty);
  } else {
    _savedWorkouts.forEach(w => {
      const option = document.createElement('div');
      option.className = 'roster-picker__option';
      option.dataset.workoutId = w.id;

      const dot  = document.createElement('span');
      dot.className = 'roster-picker__dot';

      const name = document.createElement('span');
      name.className = 'roster-picker__option-name';
      name.textContent = w.name;

      const date = document.createElement('span');
      date.className = 'roster-picker__option-date';
      date.textContent = w.created_at ? new Date(w.created_at).toLocaleDateString() : '';

      option.append(dot, name, date);
      option.addEventListener('click', () => { closeSetupWorkoutDropdown(); _selectSetupWorkout(w); });
      menu.appendChild(option);
    });
  }

  const sep = document.createElement('div');
  sep.style.cssText = 'border-top:1px solid var(--border);margin:4px 0';
  menu.appendChild(sep);

  const createOption = document.createElement('div');
  createOption.className = 'roster-picker__option workout-picker__create';
  createOption.innerHTML = '<span style="color:var(--accent);font-size:18px;line-height:1">+</span>'
    + '<span class="roster-picker__option-name" style="color:var(--accent)">Create New Workout</span>';
  createOption.addEventListener('click', () => { closeSetupWorkoutDropdown(); openNewWorkoutModal(); });
  menu.appendChild(createOption);
}

function _renderSetupRosterMenu() {
  const menu = document.getElementById('setup-roster-menu');
  if (!menu) return;

  const active = _setupSelectedRosterId;
  renderRosterDropdownOptions(
    menu,
    (_savedRosters || []).filter(r => !r.archived),
    active,
    (roster) => { closeSetupRosterDropdown(); _selectSetupRoster(roster); },
    { emptyMessage: 'No rosters yet. Create one in Settings.', showArchived: false, customEmptyStyle: true }
  );
}

function _applySetupDefaults() {
  // Default roster: active roster
  const active = (_savedRosters || []).find(r => r.is_active);
  if (active) _selectSetupRoster(active);
}

function _selectSetupWorkout(workout) {
  _setupSelectedWorkout = workout;
  const label = document.getElementById('setup-workout-label');
  if (label) { label.textContent = workout.name; label.classList.remove('placeholder'); }
  document.querySelectorAll('#setup-workout-menu .roster-picker__option').forEach(opt => {
    const isMatch = opt.dataset.workoutId === workout.id;
    opt.classList.toggle('active', isMatch);
  });
  _updateSetupConfirmBtn();
}

function _selectSetupRoster(roster) {
  _setupSelectedRosterId = roster.id;
  const label = document.getElementById('setup-roster-label');
  if (label) { label.textContent = roster.name; label.classList.remove('placeholder'); }
  document.querySelectorAll('#setup-roster-menu .roster-picker__option').forEach(opt => {
    const isMatch = opt.querySelector('.roster-picker__option-name')?.textContent === roster.name;
    opt.classList.toggle('active', isMatch);
  });
  _updateSetupConfirmBtn();
}

function _updateSetupConfirmBtn() {
  const btn = document.getElementById('setup-confirm-btn');
  if (btn) btn.disabled = !(_setupSelectedWorkout && _setupSelectedRosterId);
}

function toggleSetupWorkoutDropdown(e) {
  e.stopPropagation();
  const trigger = document.getElementById('setup-workout-trigger');
  const menu    = document.getElementById('setup-workout-menu');
  const isOpen  = menu.classList.contains('open');
  closeSetupWorkoutDropdown();
  closeSetupRosterDropdown();
  if (!isOpen) { trigger.classList.add('open'); menu.classList.add('open'); }
}

function closeSetupWorkoutDropdown() {
  document.getElementById('setup-workout-trigger')?.classList.remove('open');
  document.getElementById('setup-workout-menu')?.classList.remove('open');
}

function toggleSetupRosterDropdown(e) {
  e.stopPropagation();
  const trigger = document.getElementById('setup-roster-trigger');
  const menu    = document.getElementById('setup-roster-menu');
  const isOpen  = menu.classList.contains('open');
  closeSetupRosterDropdown();
  closeSetupWorkoutDropdown();
  if (!isOpen) { trigger.classList.add('open'); menu.classList.add('open'); }
}

function closeSetupRosterDropdown() {
  document.getElementById('setup-roster-trigger')?.classList.remove('open');
  document.getElementById('setup-roster-menu')?.classList.remove('open');
}

// ============================================================
// NEW WORKOUT MODAL
// ============================================================

function openNewWorkoutModal() {
  const modal = document.getElementById('workout-modal');
  document.getElementById('wk-distance').value = '';
  document.getElementById('wk-laps').value     = '';
  document.getElementById('wk-rest').value     = '';
  document.getElementById('workout-modal-error').style.display = 'none';
  document.getElementById('workout-modal-save-btn').disabled   = true;
  modal.style.display = 'flex';
}

function closeNewWorkoutModal() {
  document.getElementById('workout-modal').style.display = 'none';
}

function updateWorkoutModalSaveBtn() {
  const distance = document.getElementById('wk-distance').value.trim();
  const laps     = document.getElementById('wk-laps').value.trim();
  document.getElementById('workout-modal-save-btn').disabled = !(distance && laps);
}

/**
 * Called when the coach clicks "Save Workout" in the new-workout modal.
 * Saves the workout and refreshes the setup modal's picker, auto-selecting the new entry.
 */
async function saveAndConfigureWorkout() {
  const distance = document.getElementById('wk-distance').value.trim();
  const laps     = document.getElementById('wk-laps').value.trim();
  const rest     = document.getElementById('wk-rest').value.trim();

  const errorEl = document.getElementById('workout-modal-error');
  if (!distance || !laps) {
    errorEl.textContent = 'Distance and laps are required.';
    errorEl.style.display = 'block';
    return;
  }
  errorEl.style.display = 'none';

  const r = await pywebview.api.save_and_configure_workout(distance, laps, rest || '0', _setupSelectedRosterId);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (!r.ok) {
    errorEl.textContent = r.msg || 'Failed to save workout.';
    errorEl.style.display = 'block';
    return;
  }

  closeNewWorkoutModal();
  if (r.state) applyState(r.state);

  if (r.workouts) {
    _savedWorkouts = r.workouts;
    _renderSetupWorkoutMenu();
    if (r.workout_config) {
      const newWorkout = _savedWorkouts.find(w => w.id === r.workout_config.id);
      if (newWorkout) _selectSetupWorkout(newWorkout);
    }
  }
}
