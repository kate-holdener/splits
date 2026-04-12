// ============================================================
// SETTINGS SCREEN — Season and Athlete Management
// ============================================================

let currentSettingsTab = 'seasons';
let settingsSeasons = [];
let settingsAthletes = [];
let currentSeasonFilter = 'all';
let currentAthleteFilter = 'all';
let selectedSettingsSeasonId = null;

// ============================================================
// TAB SWITCHING
// ============================================================

function switchSettingsTab(tab) {
  if (tab === currentSettingsTab) return;
  
  currentSettingsTab = tab;
  
  // Update tab buttons
  document.querySelectorAll('#settings-tab-bar .tab').forEach(btn => {
    btn.classList.remove('active');
  });
  document.getElementById(`tab-${tab}`).classList.add('active');
  
  // Update tab content
  document.querySelectorAll('#settings-body .tab-content').forEach(content => {
    content.classList.remove('active');
  });
  document.getElementById(`stc-${tab}`).classList.add('active');
  
  // Load data for the tab
  if (tab === 'seasons') {
    loadSettingsSeasons();
  } else if (tab === 'athletes') {
    loadSettingsSeasons(); // Load seasons for the dropdown
    resetAthleteSelection();
  }
}

// ============================================================
// SEASON SELECTION FOR ATHLETES TAB
// ============================================================

function resetAthleteSelection() {
  selectedSettingsSeasonId = null;
  const label = document.getElementById('settings-season-selected-label');
  const card = document.getElementById('athletes-management-card');
  
  if (label) {
    label.textContent = '— Select a season —';
    label.classList.add('placeholder');
  }
  
  if (card) {
    card.style.display = 'none';
  }
  
  closeSettingsSeasonDropdown();
}

function toggleSettingsSeasonDropdown(event) {
  event.stopPropagation();
  const trigger = document.getElementById('settings-season-trigger');
  const menu = document.getElementById('settings-season-picker-menu');
  
  if (!trigger || !menu) return;
  
  const isOpen = trigger.classList.contains('open');
  
  if (isOpen) {
    closeSettingsSeasonDropdown();
  } else {
    openSettingsSeasonDropdown();
  }
}

function openSettingsSeasonDropdown() {
  const trigger = document.getElementById('settings-season-trigger');
  const menu = document.getElementById('settings-season-picker-menu');
  
  if (!trigger || !menu) return;
  
  trigger.classList.add('open');
  menu.classList.add('open');
  
  // Populate the dropdown with active seasons only
  renderSettingsSeasonDropdown();
}

function closeSettingsSeasonDropdown() {
  const trigger = document.getElementById('settings-season-trigger');
  const menu = document.getElementById('settings-season-picker-menu');
  
  if (trigger) trigger.classList.remove('open');
  if (menu) menu.classList.remove('open');
}

function renderSettingsSeasonDropdown() {
  const menu = document.getElementById('settings-season-picker-menu');
  if (!menu) return;
  
  menu.innerHTML = '';
  
  // Only show active (non-archived) seasons
  const activeSeasons = settingsSeasons.filter(s => !s.archived);
  
  if (!activeSeasons.length) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:14px 18px;color:var(--muted);font-size:15px';
    empty.textContent = 'No active seasons available.';
    menu.appendChild(empty);
    return;
  }
  
  activeSeasons.forEach(season => {
    const option = document.createElement('div');
    option.className = 'settings-season-picker__option';
    option.addEventListener('click', () => selectSettingsSeason(season));
    
    const dot = document.createElement('span');
    dot.className = 'settings-season-picker__dot';
    
    const name = document.createElement('span');
    name.className = 'settings-season-picker__option-name';
    name.textContent = season.name;
    
    const date = document.createElement('span');
    date.className = 'settings-season-picker__option-date';
    date.textContent = season.created_at ? new Date(season.created_at).toLocaleDateString() : '';
    
    option.append(dot, name, date);
    menu.appendChild(option);
  });
}

function selectSettingsSeason(season) {
  selectedSettingsSeasonId = season.id;
  
  const label = document.getElementById('settings-season-selected-label');
  const card = document.getElementById('athletes-management-card');
  const display = document.getElementById('athlete-season-display');
  
  if (label) {
    label.textContent = season.name;
    label.classList.remove('placeholder');
  }
  
  if (display) {
    display.textContent = `— ${season.name}`;
  }
  
  if (card) {
    card.style.display = 'block';
  }
  
  closeSettingsSeasonDropdown();
  
  // Load athletes for the selected season
  loadSettingsAthletesForSeason(season.id);
}

// ============================================================
// SEASON MANAGEMENT
// ============================================================

async function loadSettingsSeasons() {
  try {
    const result = await pywebview.api.list_all_seasons_with_archived();
    if (result.ok) {
      settingsSeasons = result.seasons || [];
      renderSettingsSeasons();
    } else {
      console.error('Failed to load seasons:', result.msg);
    }
  } catch (e) {
    console.error('Error loading seasons:', e);
  }
}

function renderSettingsSeasons() {
  const tbody = document.getElementById('seasons-tbody');
  tbody.innerHTML = '';
  
  const filteredSeasons = filterSeasonsByStatus(settingsSeasons, currentSeasonFilter);
  
  filteredSeasons.forEach(season => {
    const row = document.createElement('tr');
    
    const isActive = season.is_active;
    const isArchived = season.archived || false;
    const status = isArchived ? 'archived' : (isActive ? 'active' : 'inactive');
    const athleteCount = season.athlete_count || 0;
    const createdDate = season.created_at ? new Date(season.created_at).toLocaleDateString() : '-';
    
    row.innerHTML = `
      <td><strong>${escapeHtml(season.name)}</strong></td>
      <td>${createdDate}</td>
      <td>${athleteCount}</td>
      <td><span class="settings-status-badge ${status}">${status}</span></td>
      <td>
        <div class="settings-actions">
          ${!isActive && !isArchived ? `<button class="btn btn-primary btn-sm" onclick="activateSeason('${season.id}')">Activate</button>` : ''}
          ${!isArchived ? `<button class="btn btn-ghost btn-sm" onclick="archiveSeason('${season.id}')">Archive</button>` : ''}
          ${isArchived ? `<button class="btn btn-ghost btn-sm" onclick="restoreSeason('${season.id}')">Restore</button>` : ''}
        </div>
      </td>
    `;
    
    tbody.appendChild(row);
  });
  
  if (filteredSeasons.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = '<td colspan="5" style="text-align:center;color:var(--muted);padding:24px">No seasons found</td>';
    tbody.appendChild(emptyRow);
  }
}

function filterSeasonsByStatus(seasons, filter) {
  if (filter === 'all') return seasons;
  if (filter === 'active') return seasons.filter(s => s.is_active && !s.archived);
  if (filter === 'archived') return seasons.filter(s => s.archived);
  return seasons;
}

function filterSeasons(status) {
  currentSeasonFilter = status;
  
  // Update filter buttons
  document.querySelectorAll('#stc-seasons .filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`#stc-seasons .filter-btn[data-filter="${status}"]`).classList.add('active');
  
  renderSettingsSeasons();
}

async function activateSeason(seasonId) {
  try {
    const result = await pywebview.api.select_season(seasonId);
    if (result.ok) {
      console.log('Season activated:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      loadSettingsSeasons(); // Refresh the list
    } else {
      console.error('Failed to activate season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error activating season:', e);
    if (window.log) window.log('Error activating season: ' + e.message, 'err');
  }
}

async function archiveSeason(seasonId) {
  if (!confirm('Are you sure you want to archive this season? This will hide it from normal views.')) {
    return;
  }
  
  try {
    const result = await pywebview.api.archive_season(seasonId);
    if (result.ok) {
      console.log('Season archived:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      loadSettingsSeasons(); // Refresh the list
    } else {
      console.error('Failed to archive season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error archiving season:', e);
    if (window.log) window.log('Error archiving season: ' + e.message, 'err');
  }
}

async function restoreSeason(seasonId) {
  try {
    const result = await pywebview.api.restore_season(seasonId);
    if (result.ok) {
      console.log('Season restored:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      loadSettingsSeasons(); // Refresh the list
    } else {
      console.error('Failed to restore season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error restoring season:', e);
    if (window.log) window.log('Error restoring season: ' + e.message, 'err');
  }
}

// ============================================================
// ATHLETE MANAGEMENT  
// ============================================================

async function loadSettingsAthletesForSeason(seasonId) {
  try {
    // Load all athletes and filter by the selected season
    const result = await pywebview.api.list_all_athletes();
    if (result.ok) {
      settingsAthletes = (result.athletes || []).filter(a => a.season_id === seasonId);
      renderSettingsAthletes();
    } else {
      console.error('Failed to load athletes:', result.msg);
    }
  } catch (e) {
    console.error('Error loading athletes:', e);
  }
}

async function loadSettingsAthletes() {
  try {
    const result = await pywebview.api.list_all_athletes();
    if (result.ok) {
      settingsAthletes = result.athletes || [];
      renderSettingsAthletes();
    } else {
      console.error('Failed to load athletes:', result.msg);
    }
  } catch (e) {
    console.error('Error loading athletes:', e);
  }
}

function renderSettingsAthletes() {
  const tbody = document.getElementById('athletes-settings-tbody');
  tbody.innerHTML = '';
  
  let filteredAthletes = filterAthletesByStatus(settingsAthletes, currentAthleteFilter);
  
  filteredAthletes.forEach(athlete => {
    const row = document.createElement('tr');
    
    const isArchived = athlete.archived || false;
    const status = isArchived ? 'archived' : 'active';
    const fullName = `${athlete.first_name || athlete.name || ''} ${athlete.last_name || athlete.lname || ''}`.trim();
    
    row.innerHTML = `
      <td><strong>${escapeHtml(fullName)}</strong></td>
      <td><code>${escapeHtml(athlete.lap_id || '-')}</code></td>
      <td><code>${escapeHtml(athlete.start_id || '-')}</code></td>
      <td><span class="settings-status-badge ${status}">${status}</span></td>
      <td>
        <div class="settings-actions">
          ${!isArchived ? `<button class="btn btn-ghost btn-sm" onclick="archiveAthlete('${athlete.id}')">Archive</button>` : ''}
          ${isArchived ? `<button class="btn btn-ghost btn-sm" onclick="restoreAthlete('${athlete.id}')">Restore</button>` : ''}
          <button class="btn btn-ghost btn-sm" onclick="editAthlete('${athlete.id}')">Edit</button>
        </div>
      </td>
    `;
    
    tbody.appendChild(row);
  });
  
  if (filteredAthletes.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = '<td colspan="5" style="text-align:center;color:var(--muted);padding:24px">No athletes found</td>';
    tbody.appendChild(emptyRow);
  }
}

function filterAthletesByStatus(athletes, filter) {
  if (filter === 'all') return athletes;
  if (filter === 'active') return athletes.filter(a => !a.archived);
  if (filter === 'archived') return athletes.filter(a => a.archived);
  return athletes;
}

function filterAthletes(status) {
  currentAthleteFilter = status;
  
  // Update filter buttons
  document.querySelectorAll('#stc-athletes .filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`#stc-athletes .filter-btn[data-filter="${status}"]`).classList.add('active');
  
  renderSettingsAthletes();
}

async function archiveAthlete(athleteId) {
  if (!confirm('Are you sure you want to archive this athlete? This will hide them from normal views.')) {
    return;
  }
  
  try {
    const result = await pywebview.api.archive_athlete(athleteId);
    if (result.ok) {
      console.log('Athlete archived:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      // Refresh athletes for the current season
      if (selectedSettingsSeasonId) {
        loadSettingsAthletesForSeason(selectedSettingsSeasonId);
      }
    } else {
      console.error('Failed to archive athlete:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error archiving athlete:', e);
    if (window.log) window.log('Error archiving athlete: ' + e.message, 'err');
  }
}

async function restoreAthlete(athleteId) {
  try {
    const result = await pywebview.api.restore_athlete(athleteId);
    if (result.ok) {
      console.log('Athlete restored:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      // Refresh athletes for the current season
      if (selectedSettingsSeasonId) {
        loadSettingsAthletesForSeason(selectedSettingsSeasonId);
      }
    } else {
      console.error('Failed to restore athlete:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error restoring athlete:', e);
    if (window.log) window.log('Error restoring athlete: ' + e.message, 'err');
  }
}

function editAthlete(athleteId) {
  // TODO: Implement athlete editing modal
  alert(`Edit athlete functionality coming soon! (ID: ${athleteId})`);
  console.log('Edit athlete:', athleteId);
}

function openAddAthleteModal() {
  // TODO: Implement add athlete modal
  alert('Add athlete functionality coming soon! Use "Import CSV" for now.');
  console.log('Open add athlete modal');
}

async function importAthletesModal() {
  if (!selectedSettingsSeasonId) {
    alert('Please select a season first.');
    return;
  }
  
  try {
    // Pick CSV file
    const result = await pywebview.api.pick_csv_file();
    if (!result || !result.path) {
      console.log('No CSV file selected');
      return;
    }
    
    // Add athletes from CSV to the selected season
    const addResult = await pywebview.api.add_athletes_to_season_from_csv(selectedSettingsSeasonId, result.path);
    
    if (addResult.ok) {
      console.log('Athletes imported successfully:', addResult.msg);
      if (window.log) window.log(addResult.msg, 'ok');
      // Refresh the athletes list for the current season
      loadSettingsAthletesForSeason(selectedSettingsSeasonId);
    } else {
      console.error('Failed to import athletes:', addResult.msg);
      if (window.log) window.log(addResult.msg, 'err');
      alert('Failed to import athletes: ' + addResult.msg);
    }
  } catch (e) {
    console.error('Error importing athletes:', e);
    if (window.log) window.log('Error importing athletes: ' + e.message, 'err');
    alert('Error importing athletes: ' + e.message);
  }
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================
// INITIALIZATION
// ============================================================

// Initialize settings screen when it becomes active
window.addEventListener('DOMContentLoaded', () => {
  // Set up observer for settings screen
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.target.id === 'settings-screen' && 
          mutation.target.classList.contains('active')) {
        // Settings screen became active, load initial data
        loadSettingsSeasons();
        if (currentSettingsTab === 'athletes') {
          resetAthleteSelection();
        }
      }
    });
  });
  
  const settingsScreen = document.getElementById('settings-screen');
  if (settingsScreen) {
    observer.observe(settingsScreen, { 
      attributes: true, 
      attributeFilter: ['class'] 
    });
  }
  
  // Close settings season picker when clicking outside it
  document.addEventListener('click', e => {
    if (!document.getElementById('settings-season-picker')?.contains(e.target)) {
      closeSettingsSeasonDropdown();
    }
  });
});