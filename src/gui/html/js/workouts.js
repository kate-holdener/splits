// ============================================================
// WORKOUT PICKER — dropdown for saved workout configurations
// ============================================================

let _savedWorkouts = [];

/**
 * Load saved workouts from the backend and refresh the picker.
 */
async function loadWorkoutsList() {
  try {
    const r = await pywebview.api.list_workouts();
    if (r.ok) {
      _savedWorkouts = r.workouts || [];
      renderWorkoutsList(_savedWorkouts);
    }
  } catch (e) {
    console.error('Error loading workouts:', e);
  }
}

/**
 * Render the workout picker dropdown options.
 * @param {Array} workouts - Array of workout objects
 * @param {string|null} selectedId - ID of the currently active workout
 */
function renderWorkoutsList(workouts, selectedId = null) {
  const menu  = document.getElementById('workout-picker-menu');
  const label = document.getElementById('workout-selected-label');
  if (!menu || !label) return;

  menu.innerHTML = '';

  if (!workouts || !workouts.length) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:14px 18px;color:var(--muted);font-size:15px';
    empty.textContent = 'No saved workouts yet.';
    menu.appendChild(empty);
    return;
  }

  workouts.forEach(w => {
    const option = document.createElement('div');
    option.className = 'roster-picker__option';
    if (w.id === selectedId) option.classList.add('selected');

    const dot = document.createElement('span');
    dot.className = 'roster-picker__dot';

    const name = document.createElement('span');
    name.className = 'roster-picker__option-name';
    name.textContent = w.name;

    const date = document.createElement('span');
    date.className = 'roster-picker__option-date';
    date.textContent = w.created_at ? new Date(w.created_at).toLocaleDateString() : '';

    option.append(dot, name, date);
    option.addEventListener('click', () => onWorkoutOptionClick(w));
    menu.appendChild(option);
  });
}

function toggleWorkoutDropdown(e) {
  e.stopPropagation();
  const trigger = document.getElementById('workout-trigger');
  const menu    = document.getElementById('workout-picker-menu');
  const isOpen  = menu.classList.contains('open');
  closeWorkoutDropdown();
  if (!isOpen) {
    trigger.classList.add('open');
    menu.classList.add('open');
  }
}

function closeWorkoutDropdown() {
  document.getElementById('workout-trigger')?.classList.remove('open');
  document.getElementById('workout-picker-menu')?.classList.remove('open');
}

/**
 * Called when the user picks a workout from the dropdown.
 * Populates the form fields and configures the workout (without re-saving).
 */
async function onWorkoutOptionClick(workout) {
  closeWorkoutDropdown();

  // Populate form fields
  document.getElementById('wk-distance').value = workout.distance;
  document.getElementById('wk-laps').value     = workout.laps;
  document.getElementById('wk-rest').value     = workout.rest;

  // Update picker label
  const label = document.getElementById('workout-selected-label');
  label.textContent = workout.name;
  label.classList.remove('placeholder');

  // Configure (apply) the selected workout without re-saving to the list
  const r = await pywebview.api.configure_workout(
    String(workout.distance),
    String(workout.laps),
    String(workout.rest)
  );
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.state) applyState(r.state);

  // Highlight the selected entry
  renderWorkoutsList(_savedWorkouts, workout.id);
}

/**
 * Called when the coach clicks "Save Workout".
 * Saves the entered values to the persistent list and configures the workout.
 */
async function saveAndConfigureWorkout() {
  const distance = document.getElementById('wk-distance').value.trim();
  const laps     = document.getElementById('wk-laps').value.trim();
  const rest     = document.getElementById('wk-rest').value.trim();

  if (!distance || !laps) {
    log('Distance and laps are required.', 'err');
    return;
  }

  const r = await pywebview.api.save_and_configure_workout(distance, laps, rest || '0');
  log(r.msg, r.ok ? 'ok' : 'err');
  if (!r.ok) return;

  if (r.state) applyState(r.state);

  if (r.workouts) {
    _savedWorkouts = r.workouts;
    const selectedId = r.workout_config ? r.workout_config.id : null;
    renderWorkoutsList(_savedWorkouts, selectedId);

    // Update picker label
    if (r.workout_config) {
      const label = document.getElementById('workout-selected-label');
      label.textContent = r.workout_config.name;
      label.classList.remove('placeholder');
    }
  }
}
