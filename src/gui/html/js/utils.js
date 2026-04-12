// ============================================================
// SHARED UTILITIES — Season Dropdown Rendering
// ============================================================

/**
 * Renders season dropdown options with consistent styling
 * @param {HTMLElement} menu - The menu container element  
 * @param {Array} seasons - Array of season objects
 * @param {string|null} selectedSeasonId - Currently selected season ID
 * @param {Function} onSelectCallback - Callback function when season is selected
 * @param {Object} options - Additional options
 */
function renderSeasonDropdownOptions(menu, seasons, selectedSeasonId, onSelectCallback, options = {}) {
  menu.innerHTML = '';
  
  const emptyMessage = options.emptyMessage || 'No seasons yet.';
  const showArchived = options.showArchived || false;
  const customEmptyStyle = options.customEmptyStyle || false;
  
  if (!seasons || !seasons.length) {
    const empty = document.createElement('div');
    if (customEmptyStyle) {
      // Special styling for workout screen
      empty.style.cssText = 'padding:14px 18px;color:var(--muted);font-size:15px';
    } else {
      // Standard styling for Settings screen
      empty.className = 'season-picker__option disabled';
    }
    empty.textContent = emptyMessage;
    menu.appendChild(empty);
    return;
  }
  
  seasons.forEach(season => {
    const option = document.createElement('div');
    option.className = 'season-picker__option';
    
    // Add active class for current active season (workout screen)
    if (season.is_active) {
      option.classList.add('active');
    }
    
    // Add selected class for currently selected season (settings screen)
    if (season.id === selectedSeasonId) {
      option.classList.add('selected');
    }
    
    const dot = document.createElement('span');
    dot.className = 'season-picker__dot';
    
    const name = document.createElement('span');
    name.className = 'season-picker__option-name';
    const isArchived = season.archived || false;
    const statusBadge = isArchived ? ' (Archived)' : '';
    name.textContent = season.name + statusBadge;
    if (isArchived) {
      name.style.color = 'var(--danger)';
    }
    
    const date = document.createElement('span');
    date.className = 'season-picker__option-date';
    date.textContent = season.created_at ? new Date(season.created_at).toLocaleDateString() : '';
    
    option.append(dot, name, date);
    option.addEventListener('click', () => onSelectCallback(season));
    menu.appendChild(option);
  });
}

/**
 * Utility function to escape HTML content
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}