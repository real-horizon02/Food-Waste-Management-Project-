/**
 * Expiry Alert Module
 * Shows cute animated alerts when dashboard loads if items are expiring soon
 * Prevents food waste by notifying users early
 */

/**
 * Show cute expiry alert popup on dashboard load
 * Notifies user about items expiring soon to prevent food waste
 */
async function showExpiryAlertOnDashboardLoad() {
  const user = getCurrentUser();
  if (!user || !user.email) return;
  
  try {
    // Fetch tracker items for current user
    const response = await apiRequest(`/tracker/items?userEmail=${encodeURIComponent(user.email)}`);
    
    if (!response || response.total === 0) return;
    
    // Get expiring items (expiring within 7 days) and expired items
    const expiringItems = response.expiringItems || [];
    const expiredItems = response.expiredItems || [];
    const criticalItems = [...(expiredItems || []), ...expiringItems];
    
    if (criticalItems.length === 0) return;
    
    // Show the cute alert popup
    showExpiryAlertPopup(criticalItems);
  } catch (error) {
    console.warn('[Expiry Alert] Could not load alert:', error);
  }
}

/**
 * Display the cute expiry alert popup with animations
 * Features: Animated emoji, smooth transitions, auto-dismiss with fade-out
 */
function showExpiryAlertPopup(items) {
  // Remove any existing popup first
  const existing = document.querySelector('.expiring-popup');
  if (existing) existing.remove();
  
  if (!items || items.length === 0) return;
  
  const itemCount = items.length;
  const firstItem = items[0];
  const firstItemName = firstItem.itemName || 'Item';
  
  // Calculate days until expiry
  let daysLeft = firstItem.daysUntilExpiry;
  if (daysLeft === undefined) {
    const expiry = new Date(firstItem.expiryDate);
    const now = new Date();
    const diff = expiry - now;
    daysLeft = Math.ceil(diff / (1000 * 60 * 60 * 24));
  }
  
  // Determine emoji and title based on urgency
  let emoji = '⏰';
  let title = 'Items Expiring Soon';
  let urgency = 'normal';
  
  if (daysLeft < 0) {
    emoji = '❌';
    title = 'Items Have Expired!';
    urgency = 'critical';
  } else if (daysLeft === 0) {
    emoji = '🚨';
    title = 'Expires Today!';
    urgency = 'critical';
  } else if (daysLeft === 1) {
    emoji = '⚠️';
    title = 'Expires Tomorrow!';
    urgency = 'high';
  } else if (daysLeft <= 3) {
    emoji = '🔥';
    title = 'Expiring Very Soon!';
    urgency = 'high';
  }
  
  // Create popup HTML
  const popup = document.createElement('div');
  popup.className = 'expiring-popup';
  popup.style.opacity = '0';
  popup.style.transform = 'translateY(-14px) scale(0.95)';
  
  popup.innerHTML = `
    <div class="emoji">${emoji}</div>
    <div class="meta">
      <h4>${title}</h4>
      <p><strong>${firstItemName}</strong>${itemCount > 1 ? ` + ${itemCount - 1} more` : ''}</p>
    </div>
    <div class="actions">
      <button class="btn btn-view" onclick="if(typeof showSection === 'function') showSection('food-tracker-section'); this.closest('.expiring-popup').remove();">
        View All
      </button>
      <button class="btn btn-dismiss" onclick="this.closest('.expiring-popup').remove();">
        ✕
      </button>
    </div>
  `;
  
  // Append to body
  document.body.appendChild(popup);
  
  // Trigger animation: fade in with scale and slide
  requestAnimationFrame(() => {
    popup.style.transition = 'opacity 0.56s cubic-bezier(0.2, 0.9, 0.3, 1), transform 0.56s cubic-bezier(0.2, 0.9, 0.3, 1)';
    popup.style.opacity = '1';
    popup.style.transform = 'translateY(0) scale(1)';
  });
  
  // Auto-dismiss after 8 seconds with smooth fade-out
  const dismissTimer = setTimeout(() => {
    if (popup.parentNode) {
      popup.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
      popup.style.opacity = '0';
      popup.style.transform = 'translateY(-20px)';
      setTimeout(() => {
        if (popup.parentNode) popup.remove();
      }, 400);
    }
  }, 8000);
  
  // Allow manual dismiss to clear the timer
  const dismissBtn = popup.querySelector('.btn-dismiss');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      clearTimeout(dismissTimer);
    });
  }
  
  console.log(`[Expiry Alert] ✨ Showing ${urgency} popup for ${itemCount} expiring item(s): "${firstItemName}"`);
}

// Wire to dashboard load
document.addEventListener('DOMContentLoaded', () => {
  // Delay slightly to ensure food tracker is initialized and user data is loaded
  setTimeout(() => {
    showExpiryAlertOnDashboardLoad();
  }, 500);
});
