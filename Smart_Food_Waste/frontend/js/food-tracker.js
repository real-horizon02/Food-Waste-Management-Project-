/**
 * Food Tracker functionality
 * Handles adding, viewing, and managing tracked grocery items
 */

// ===== UTILITY FUNCTIONS =====

/**
 * Format date to YYYY-MM-DD for display
 */
function formatDate(isoDate) {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch (e) {
    return isoDate;
  }
}

/**
 * Calculate days until expiry
 */
function daysUntilExpiry(expiryDateStr) {
  const expiry = new Date(expiryDateStr);
  const now = new Date();
  const diff = expiry - now;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/**
 * Determine status badge class
 */
function getStatusClass(daysLeft) {
  if (daysLeft < 0) return 'expired';
  if (daysLeft <= 3) return 'expiring-critical';
  if (daysLeft <= 7) return 'expiring-soon';
  if (daysLeft <= 30) return 'expiring-notice';
  return 'active';
}

/**
 * Get status badge text
 */
function getStatusText(daysLeft) {
  if (daysLeft < 0) return '❌ Expired';
  if (daysLeft === 0) return '⚠️ Expires Today';
  if (daysLeft === 1) return '⚠️ Expires Tomorrow';
  if (daysLeft <= 3) return `⚠️ ${daysLeft} days left`;
  if (daysLeft <= 7) return `⏱️ ${daysLeft} days left`;
  if (daysLeft <= 30) return `📅 ${daysLeft} days left`;
  return `✅ ${daysLeft} days`;
}

// ===== FOOD TRACKER EVENT HANDLERS =====

/**
 * Initialize food tracker on page load
 */
function initFoodTracker() {
  const form = document.getElementById('food-tracker-form');
  if (form) {
    form.addEventListener('submit', handleAddTrackerItem);
    
    // Prevent event propagation on form inputs
    const inputs = form.querySelectorAll('input, textarea, button');
    inputs.forEach(input => {
      input.addEventListener('click', (e) => {
        e.stopPropagation();
      });
      input.addEventListener('keydown', (e) => {
        e.stopPropagation();
      });
      input.addEventListener('keyup', (e) => {
        e.stopPropagation();
      });
    });
  }
  
  // Load items for current user on section view
  const trackerSection = document.getElementById('food-tracker-section');
  if (trackerSection) {
    // Load items when the section becomes active
    const observer = new MutationObserver(() => {
      if (trackerSection.classList.contains('active')) {
        loadTrackerItems();
      }
    });
    observer.observe(trackerSection, { attributes: true, attributeFilter: ['class'] });
    
    // Initial load if section is already active
    if (trackerSection.classList.contains('active')) {
      loadTrackerItems();
    }
  }
}

/**
 * Handle form submission to add new tracker item
 */
async function handleAddTrackerItem(event) {
  event.preventDefault();
  
  const itemNameInput = document.getElementById('tracker-item-name');
  const expiryDateInput = document.getElementById('tracker-expiry-date');
  
  if (!itemNameInput.value || !expiryDateInput.value) {
    showError('Please fill in all fields');
    return;
  }
  
  // Get current user email
  const user = getCurrentUser();
  if (!user || !user.email) {
    showError('Could not identify user email');
    return;
  }
  
  try {
    showLoading('Adding item...');
    
    const response = await apiRequest('/tracker/add-item', 'POST', {
      userEmail: user.email,
      itemName: itemNameInput.value,
      expiryDate: expiryDateInput.value
    });
    
    if (response.ok || response.message) {
      showSuccess('Item added successfully!');
      itemNameInput.value = '';
      expiryDateInput.value = '';
      
      // Reload items
      await loadTrackerItems();
    } else {
      showError(response.error || 'Failed to add item');
    }
  } catch (error) {
    console.error('Error adding tracker item:', error);
    showError('Error adding item: ' + error.message);
  } finally {
    hideLoading();
  }
}

/**
 * Load and display tracker items for current user
 */
async function loadTrackerItems() {
  const user = getCurrentUser();
  if (!user || !user.email) {
    console.warn('No user logged in');
    return;
  }
  
  try {
    const response = await apiRequest(`/tracker/items?userEmail=${encodeURIComponent(user.email)}`);
    
    if (response.total !== undefined) {
      displayTrackerItems(response);
    } else {
      console.warn('Invalid response format:', response);
    }
  } catch (error) {
    console.error('Error loading tracker items:', error);
    showError('Error loading items');
  }
}

/**
 * Display tracker items in the UI
 */
function displayTrackerItems(data) {
  const container = document.getElementById('food-tracker-items');
  if (!container) return;
  
  // Clear container
  container.innerHTML = '';
  
  // If no items at all
  if (data.total === 0) {
    container.innerHTML = `
      <div class="placeholder-card">
        <h3>No items tracked yet</h3>
        <p>Add items above to start tracking expiry dates.</p>
      </div>
    `;
    return;
  }
  
  // Create items container
  let html = '';
  
  // Show expired items
  if (data.expiredItems && data.expiredItems.length > 0) {
    html += `<div style="margin-bottom: 24px;">
      <h4 style="color: #ff6a88; margin: 0 0 12px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px;">
        ❌ Expired Items (${data.expiredItems.length})
      </h4>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${data.expiredItems.map(item => createTrackerItemCard(item, 'expired')).join('')}
      </div>
    </div>`;
  }
  
  // Show expiring soon items
  if (data.expiringItems && data.expiringItems.length > 0) {
    html += `<div style="margin-bottom: 24px;">
      <h4 style="color: #ffa500; margin: 0 0 12px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px;">
        ⚠️ Expiring Soon (${data.expiringItems.length})
      </h4>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${data.expiringItems.map(item => createTrackerItemCard(item, 'expiring')).join('')}
      </div>
    </div>`;
  }
  
  // Show active items
  if (data.activeItems && data.activeItems.length > 0) {
    html += `<div style="margin-bottom: 24px;">
      <h4 style="color: #32ffb4; margin: 0 0 12px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px;">
        ✅ Active Items (${data.activeItems.length})
      </h4>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${data.activeItems.map(item => createTrackerItemCard(item, 'active')).join('')}
      </div>
    </div>`;
  }
  
  container.innerHTML = html;
  
  // Attach delete event listeners
  container.querySelectorAll('.tracker-delete-btn').forEach(btn => {
    btn.addEventListener('click', handleDeleteTrackerItem);
  });
}

/**
 * Create HTML card for a tracker item
 */
function createTrackerItemCard(item, status) {
  const daysLeft = item.daysUntilExpiry || daysUntilExpiry(item.expiryDate);
  const statusClass = getStatusClass(daysLeft);
  const statusText = getStatusText(daysLeft);
  const expiryFormatted = formatDate(item.expiryDate);
  
  // Set border color based on status
  let borderColor = 'rgba(144, 123, 255, 0.16)';
  let bgColor = 'rgba(14, 8, 36, 0.7)';
  
  if (status === 'expired') {
    borderColor = 'rgba(255, 106, 136, 0.3)';
    bgColor = 'rgba(255, 106, 136, 0.05)';
  } else if (status === 'expiring') {
    borderColor = 'rgba(255, 165, 0, 0.3)';
    bgColor = 'rgba(255, 165, 0, 0.05)';
  } else if (status === 'active') {
    borderColor = 'rgba(50, 255, 180, 0.2)';
    bgColor = 'rgba(50, 255, 180, 0.05)';
  }
  
  return `
    <div class="tracker-item-card" style="
      background: ${bgColor};
      border: 1px solid ${borderColor};
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    ">
      <div style="flex: 1;">
        <div style="font-weight: 600; color: #ffffff; margin-bottom: 6px;">
          ${item.itemName}
        </div>
        <div style="font-size: 0.85rem; color: rgba(210, 220, 255, 0.75);">
          Expires: ${expiryFormatted}
        </div>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <div style="
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 0.8rem;
          font-weight: 600;
          white-space: nowrap;
          background: rgba(255, 255, 255, 0.08);
          color: rgba(235, 237, 255, 0.85);
        ">
          ${statusText}
        </div>
        <button class="tracker-delete-btn" data-item-id="${item.id}" style="
          background: rgba(255, 106, 136, 0.2);
          border: 1px solid rgba(255, 106, 136, 0.4);
          border-radius: 8px;
          color: #ff6a88;
          padding: 6px 12px;
          cursor: pointer;
          font-weight: 600;
          font-size: 0.8rem;
          transition: all 180ms ease;
        " onmouseover="this.style.background='rgba(255, 106, 136, 0.35)'" onmouseout="this.style.background='rgba(255, 106, 136, 0.2)'">
          Delete
        </button>
      </div>
    </div>
  `;
}

/**
 * Handle deletion of tracker item
 */
async function handleDeleteTrackerItem(event) {
  const btn = event.target;
  const itemId = btn.getAttribute('data-item-id');
  
  if (!itemId) return;
  
  if (!confirm('Are you sure you want to delete this item?')) {
    return;
  }
  
  try {
    showLoading(true);
    
    const response = await apiRequest(`/tracker/items/${itemId}`, 'DELETE');
    
    if (response.message) {
      showSuccess('Item deleted successfully');
      await loadTrackerItems();
    } else {
      showError(response.error || 'Failed to delete item');
    }
  } catch (error) {
    console.error('Error deleting item:', error);
    showError('Error deleting item: ' + error.message);
  } finally {
    showLoading(false);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initFoodTracker);
