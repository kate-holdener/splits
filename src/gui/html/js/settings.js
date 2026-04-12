// ============================================================
// SETTINGS SCREEN — Season and Athlete Management
// ============================================================

let settingsSeasons = [];
let settingsAthletes = [];
let selectedSettingsSeasonId = null;
let currentAthleteFilter = 'all';

// ============================================================
// SETTINGS SCREEN — Season dropdown functionality
// ============================================================

function toggleSettingsSeasonDropdown(event) {
  event.stopPropagation();
  const menu = document.getElementById('settings-season-picker-menu');
  const isOpen = menu.classList.contains('open');
  
  if (isOpen) {
    closeSettingsSeasonDropdown();
  } else {
    openSettingsSeasonDropdown();
  }
}

function openSettingsSeasonDropdown() {
  const menu = document.getElementById('settings-season-picker-menu');
  const trigger = document.getElementById('settings-season-trigger');
  
  menu.classList.add('open');
  trigger.classList.add('open');
  
  // Render seasons in dropdown
  renderSettingsSeasonDropdown();
}

function closeSettingsSeasonDropdown() {
  const menu = document.getElementById('settings-season-picker-menu');
  const trigger = document.getElementById('settings-season-trigger');
  
  menu.classList.remove('open');
  trigger.classList.remove('open');
}

function renderSettingsSeasonDropdown() {
  const menu = document.getElementById('settings-season-picker-menu');
  renderSeasonDropdownOptions(
    menu, 
    settingsSeasons, 
    selectedSettingsSeasonId, 
    selectSettingsSeason, 
    { 
      emptyMessage: 'No seasons available',
      showArchived: true 
    }
  );
}

function selectSettingsSeason(season) {
  selectedSettingsSeasonId = season.id;
  
  // Update dropdown display
  const label = document.getElementById('settings-season-selected-label');
  label.textContent = season.name;
  label.classList.remove('placeholder');
  
  closeSettingsSeasonDropdown();
  
  // Show management cards and load athletes
  showSeasonManagement(season);
  loadSettingsAthletesForSeason(season.id);
}

function showSeasonManagement(season) {
  // Show the athletes card
  const athletesCard = document.getElementById('athletes-management-card');
  athletesCard.style.display = 'block';
  
  // Update athlete season display
  const seasonDisplay = document.getElementById('athlete-season-display');
  seasonDisplay.textContent = `for ${season.name}`;
  
  // Show season management card
  const seasonCard = document.getElementById('season-management-card');
  seasonCard.style.display = 'block';
  
  // Update season management buttons based on season status
  updateSeasonManagementButtons(season);
}

function updateSeasonManagementButtons(season) {
  const archiveBtn = document.getElementById('archive-season-btn');
  const restoreBtn = document.getElementById('restore-season-btn');
  const activateBtn = document.getElementById('activate-season-btn');
  const statusDisplay = document.getElementById('season-status-display');
  
  const isArchived = season.archived || false;
  const isActive = season.is_active || false;
  
  // Show/hide appropriate buttons
  archiveBtn.style.display = isArchived ? 'none' : 'inline-block';
  restoreBtn.style.display = isArchived ? 'inline-block' : 'none';
  activateBtn.style.display = (!isArchived && !isActive) ? 'inline-block' : 'none';
  
  // Update status display
  let statusText = '';
  if (isArchived) statusText = 'Status: Archived';
  else if (isActive) statusText = 'Status: Active Season';
  else statusText = 'Status: Inactive';
  
  statusDisplay.textContent = statusText;
}

// ============================================================
// SETTINGS SCREEN — Season management actions
// ============================================================

async function archiveSelectedSeason() {
  if (!selectedSettingsSeasonId) return;
  
  const season = settingsSeasons.find(s => s.id === selectedSettingsSeasonId);
  if (!season) return;
  
  if (!confirm(`Are you sure you want to archive "${season.name}"? This will hide it from normal views.`)) {
    return;
  }
  
  try {
    const result = await pywebview.api.archive_season(selectedSettingsSeasonId);
    if (result.ok) {
      console.log('Season archived:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      
      // Refresh seasons and update current selection
      await loadSettingsSeasons();
      const updatedSeason = settingsSeasons.find(s => s.id === selectedSettingsSeasonId);
      if (updatedSeason) {
        updateSeasonManagementButtons(updatedSeason);
        renderSettingsSeasonDropdown();
      }
    } else {
      console.error('Failed to archive season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error archiving season:', e);
    if (window.log) window.log('Error archiving season: ' + e.message, 'err');
  }
}

async function restoreSelectedSeason() {
  if (!selectedSettingsSeasonId) return;
  
  try {
    const result = await pywebview.api.restore_season(selectedSettingsSeasonId);
    if (result.ok) {
      console.log('Season restored:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      
      // Refresh seasons and update current selection
      await loadSettingsSeasons();
      const updatedSeason = settingsSeasons.find(s => s.id === selectedSettingsSeasonId);
      if (updatedSeason) {
        updateSeasonManagementButtons(updatedSeason);
        renderSettingsSeasonDropdown();
      }
    } else {
      console.error('Failed to restore season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error restoring season:', e);
    if (window.log) window.log('Error restoring season: ' + e.message, 'err');
  }
}

async function activateSelectedSeason() {
  if (!selectedSettingsSeasonId) return;
  
  const season = settingsSeasons.find(s => s.id === selectedSettingsSeasonId);
  if (!season) return;
  
  try {
    const result = await pywebview.api.select_season(selectedSettingsSeasonId);
    if (result.ok) {
      console.log('Season activated:', result.msg);
      if (window.log) window.log(result.msg, 'ok');
      
      // Refresh seasons and update current selection
      await loadSettingsSeasons();
      const updatedSeason = settingsSeasons.find(s => s.id === selectedSettingsSeasonId);
      if (updatedSeason) {
        updateSeasonManagementButtons(updatedSeason);
        renderSettingsSeasonDropdown();
      }
    } else {
      console.error('Failed to activate season:', result.msg);
      if (window.log) window.log(result.msg, 'err');
    }
  } catch (e) {
    console.error('Error activating season:', e);
    if (window.log) window.log('Error activating season: ' + e.message, 'err');
  }
}

// ============================================================
// SEASON LOADING AND RENDERING
// ============================================================

async function loadSettingsSeasons() {
  try {
    const result = await pywebview.api.list_all_seasons_with_archived();
    if (result.ok) {
      settingsSeasons = result.seasons || [];
      renderSettingsSeasonDropdown();
    } else {
      console.error('Failed to load seasons:', result.msg);
    }
  } catch (e) {
    console.error('Error loading seasons:', e);
  }
}

// ============================================================
// ATHLETE MANAGEMENT  
// ============================================================

async function loadSettingsAthletesForSeason(seasonId) {
  try {
    const result = await pywebview.api.list_athletes_for_season_including_archived(seasonId);
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
      <td><code>${escapeHtml(athlete.finish_tag || '-')}</code></td>
      <td><code>${escapeHtml(athlete.start_tag || '-')}</code></td>
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
  document.querySelectorAll('.settings-filters .filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`.settings-filters .filter-btn[data-filter="${status}"]`).classList.add('active');
  
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

// ============================================================
// CSV IMPORT AND ATHLETE ACTIONS
// ============================================================

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

function openAddAthleteModal() {
  alert('Add individual athlete functionality coming soon!');
  console.log('Open add athlete modal');
}

function editAthlete(athleteId) {
  alert('Edit athlete functionality coming soon!');
  console.log('Edit athlete:', athleteId);
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