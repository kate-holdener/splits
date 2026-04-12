// ============================================================
// SEASON PICKER — dropdown
// ============================================================

function renderSeasonsList(seasons) {
  const menu  = document.getElementById('season-picker-menu');
  const label = document.getElementById('season-selected-label');
  if (!menu || !label) return;

  const activeSeason = (seasons || []).find(s => s.is_active);

  if (activeSeason) {
    label.textContent = activeSeason.name;
    label.classList.remove('placeholder');
  } else {
    label.textContent = '— No season selected —';
    label.classList.add('placeholder');
  }

  menu.replaceChildren();

  // Create wrapper function for season selection
  const onSeasonSelect = (season) => onSeasonOptionClick(season.id);
  
  renderSeasonDropdownOptions(
    menu,
    seasons,
    null, // No specific selection highlighting for workout screen
    onSeasonSelect,
    {
      emptyMessage: 'No seasons yet.',
      showArchived: false,
      customEmptyStyle: true
    }
  );
}

function toggleSeasonDropdown(e) {
  e.stopPropagation();
  const trigger = document.getElementById('season-trigger');
  const menu    = document.getElementById('season-picker-menu');
  const isOpen  = menu.classList.contains('open');
  closeSeasonDropdown();
  if (!isOpen) {
    trigger.classList.add('open');
    menu.classList.add('open');
  }
}

function closeSeasonDropdown() {
  document.getElementById('season-trigger')?.classList.remove('open');
  document.getElementById('season-picker-menu')?.classList.remove('open');
}

async function onSeasonOptionClick(seasonId) {
  closeSeasonDropdown();
  const r = await pywebview.api.select_season(seasonId);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (!r.ok) return;
  if (r.state) applyState(r.state);
  loadAthleteList();
  const lr = await pywebview.api.list_seasons();
  if (lr.seasons) renderSeasonsList(lr.seasons);
}

// ============================================================
// SEASON UI — athletes card subtitle + Add button state
// ============================================================

function updateSeasonUI(season) {
  const subtitle = document.getElementById('athletes-subtitle');
  if (subtitle) subtitle.textContent = season
    ? `Athletes in ${season.name}.`
    : 'Select a season to view and manage its roster.';
}

// ============================================================
// NEW SEASON MODAL
// ============================================================

let _modalCsvPath = '';

function openSeasonModal() {
  _modalCsvPath = '';
  document.getElementById('modal-season-name').value = '';
  const disp = document.getElementById('modal-csv-display');
  disp.textContent = 'No file selected…';
  disp.style.color = 'var(--input-placeholder)';
  document.getElementById('modal-create-btn').disabled = true;
  const err = document.getElementById('modal-error');
  err.style.display = 'none';
  err.textContent = '';
  document.getElementById('season-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('modal-season-name').focus(), 50);
}

function closeSeasonModal() {
  document.getElementById('season-modal').style.display = 'none';
}

function updateModalCreateBtn() {
  const name = document.getElementById('modal-season-name').value.trim();
  document.getElementById('modal-create-btn').disabled = !name;
  const err = document.getElementById('modal-error');
  if (name) { err.style.display = 'none'; err.textContent = ''; }
}

async function pickModalCsv() {
  const result = await window.pywebview.api.pick_csv_file();
  if (result && result.path) {
    _modalCsvPath = result.path;
    const disp = document.getElementById('modal-csv-display');
    disp.textContent = result.path.split(/[/\\]/).pop();
    disp.style.color = 'var(--text)';
  }
}

async function submitNewSeason() {
  const name = document.getElementById('modal-season-name').value.trim();
  if (!name) return;

  document.getElementById('modal-create-btn').disabled = true;

  const r = await pywebview.api.create_season(name);
  if (!r.ok) {
    const err = document.getElementById('modal-error');
    err.textContent = r.msg || 'Failed to create season.';
    err.style.display = 'block';
    document.getElementById('modal-create-btn').disabled = false;
    return;
  }
  log(`Season "${r.season.name}" created.`, 'ok');

  if (_modalCsvPath) {
    const ar = await pywebview.api.add_athletes_from_csv(_modalCsvPath);
    log(ar.msg, ar.ok ? 'ok' : 'err');
    if (ar.state)   applyState(ar.state);
    if (ar.seasons) renderSeasonsList(ar.seasons);
    if (ar.ok)      loadAthleteList();
  } else {
    if (r.state)   applyState(r.state);
    if (r.seasons) renderSeasonsList(r.seasons);
    updateSeasonUI(r.season);
    document.getElementById('athletes-ok').style.display = 'none';
    document.getElementById('athlete-tbody').innerHTML = '';
  }

  closeSeasonModal();
}

async function loadSeasonsList() {
  const r = await pywebview.api.list_seasons();
  if (r.seasons) renderSeasonsList(r.seasons);
}
