// ============================================================
// SHARED UTILITIES — Roster Dropdown Rendering
// ============================================================

/**
 * Renders roster dropdown options with consistent styling
 * @param {HTMLElement} menu - The menu container element
 * @param {Array} rosters - Array of roster objects
 * @param {string|null} selectedRosterId - Currently selected roster ID
 * @param {Function} onSelectCallback - Callback function when roster is selected
 * @param {Object} options - Additional options
 */
function renderRosterDropdownOptions(menu, rosters, selectedRosterId, onSelectCallback, options = {}) {
  menu.innerHTML = '';

  const emptyMessage = options.emptyMessage || 'No rosters yet.';
  const showArchived = options.showArchived || false;
  const customEmptyStyle = options.customEmptyStyle || false;

  if (!rosters || !rosters.length) {
    const empty = document.createElement('div');
    if (customEmptyStyle) {
      empty.style.cssText = 'padding:14px 18px;color:var(--muted);font-size:15px';
    } else {
      empty.className = 'roster-picker__option disabled';
    }
    empty.textContent = emptyMessage;
    menu.appendChild(empty);
    return;
  }

  rosters.forEach(roster => {
    const option = document.createElement('div');
    option.className = 'roster-picker__option';

    if (roster.is_active) {
      option.classList.add('active');
    }

    if (roster.id === selectedRosterId) {
      option.classList.add('selected');
    }

    const dot = document.createElement('span');
    dot.className = 'roster-picker__dot';

    const name = document.createElement('span');
    name.className = 'roster-picker__option-name';
    const isArchived = roster.archived || false;
    const statusBadge = isArchived ? ' (Archived)' : '';
    name.textContent = roster.name + statusBadge;
    if (isArchived) {
      name.style.color = 'var(--danger)';
    }

    const date = document.createElement('span');
    date.className = 'roster-picker__option-date';
    date.textContent = roster.created_at ? new Date(roster.created_at).toLocaleDateString() : '';

    option.append(dot, name, date);
    option.addEventListener('click', () => onSelectCallback(roster));
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
