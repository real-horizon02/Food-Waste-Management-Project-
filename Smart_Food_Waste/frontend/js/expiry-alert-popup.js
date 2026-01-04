/**
 * Expiry Alert Popup
 * Shows a popup when the dashboard loads if there are items expiring within 30 days
 * Limited to 5 times per session using sessionStorage
 */

const MAX_ALERTS_PER_SESSION = 5;
const EXPIRY_POPUP_COUNT_KEY = 'expiryPopupCount_' + new Date().toDateString();

console.log('✓ Expiry Alert Popup script loaded');

/**
 * Get the current alert count from sessionStorage
 */
function getExpiryAlertCount() {
  const count = sessionStorage.getItem(EXPIRY_POPUP_COUNT_KEY);
  return count ? parseInt(count) : 0;
}

/**
 * Increment the alert count in sessionStorage
 */
function incrementExpiryAlertCount() {
  const newCount = getExpiryAlertCount() + 1;
  sessionStorage.setItem(EXPIRY_POPUP_COUNT_KEY, newCount.toString());
  console.log(`Expiry popup count: ${newCount}/${MAX_ALERTS_PER_SESSION}`);
  return newCount;
}

/**
 * Check if we've reached the alert limit for today
 */
function hasReachedAlertLimit() {
  return getExpiryAlertCount() >= MAX_ALERTS_PER_SESSION;
}

/**
 * Check for expiring items and show popup if needed
 * Call this after user is authenticated
 * Limited to MAX_ALERTS_PER_SESSION (5) times per session
 */
async function checkAndShowExpiryPopup() {
  // Check if alert limit reached
  if (hasReachedAlertLimit()) {
    console.log(`⛔ Alert limit reached (${MAX_ALERTS_PER_SESSION}). Skipping popup.`);
    return;
  }
  
  try {
    const user = getCurrentUser();
    if (!user || !user.email) {
      console.log('⚠️ No authenticated user, skipping expiry check');
      return;
    }
    
    console.log('🔍 Fetching expiring items for user:', user.email);
    
    let allExpiringItems = [];
    
    // Fetch items from GroceryItem collection
    try {
      const url = `${getApiBaseUrl()}/tracker/items?userEmail=${encodeURIComponent(user.email)}`;
      console.log('📡 Fetching tracker items from:', url);
      
      const token = getToken();
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        method: 'GET',
        headers: headers,
        credentials: 'include'
      });
      
      console.log('📦 GroceryItem API Response Status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Expiry items response:', data);
        
        if (data && data.expiringItems && data.expiringItems.length > 0) {
          allExpiringItems = [...allExpiringItems, ...data.expiringItems];
          console.log(`📊 Found ${data.expiringItems.length} expiring grocery items`);
        }
      } else {
        const errorText = await response.text();
        console.warn('⚠️ GroceryItem API Error:', response.status, errorText);
      }
    } catch (error) {
      console.warn('⚠️ Error fetching grocery items:', error.message);
      console.log('💡 Continuing without grocery items...');
    }
    
    // Fetch items from QRDecodedData collection
    try {
      const qrUrl = `${getApiBaseUrl()}/tracker/qr-alerts`;
      console.log('📡 Fetching QR alerts from:', qrUrl);
      
      const token = getToken();
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const qrResponse = await fetch(qrUrl, {
        method: 'GET',
        headers: headers,
        credentials: 'include'
      });
      
      console.log('📦 QR Alerts API Response Status:', qrResponse.status);
      
      if (qrResponse.ok) {
        const qrData = await qrResponse.json();
        console.log('✅ QR alerts response:', qrData);
        
        if (qrData && qrData.alerts && qrData.alerts.length > 0) {
          // Transform QR alerts to match GroceryItem format for display
          const qrItems = qrData.alerts.map(alert => ({
            itemName: alert.productName || alert.ean || 'Unknown Product',
            expiryDate: alert.expiryDate,
            daysUntilExpiry: alert.daysUntilExpiry,
            source: 'QR',
            ean: alert.ean,
            expiryStatus: alert.expiryStatus
          }));
          allExpiringItems = [...allExpiringItems, ...qrItems];
          console.log(`📊 Found ${qrItems.length} expiring QR items`);
        }
      } else {
        console.warn('⚠️ QR Alerts API returned status:', qrResponse.status);
      }
    } catch (error) {
      console.warn('⚠️ Error fetching QR alerts:', error.message);
      console.log('💡 Continuing without QR items...');
    }
    
    // Show popup if we have any expiring items
    if (allExpiringItems && allExpiringItems.length > 0) {
      console.log(`🎯 Found expiring items (total: ${allExpiringItems.length}), showing popup`);
      displayExpiryPopup(allExpiringItems);
      incrementExpiryAlertCount(); // Increment alert counter
      console.log(`✅ Alert shown`);
    } else {
      console.log('ℹ️ No expiring items found');
    }
  } catch (error) {
    console.error('❌ Error checking for expiring items:', error);
    // Silent fail - don't disrupt user experience
  }
}

/**
 * Display the expiry alert popup with items
 */
function displayExpiryPopup(expiringItems) {
  const modal = document.getElementById('expiry-popup-modal');
  const content = document.getElementById('expiry-popup-content');
  
  if (!modal || !content) {
    console.error('❌ Expiry popup elements not found');
    return;
  }
  
  console.log('🎨 Rendering popup with items...');
  
  // Build items HTML
  let itemsHTML = '';
  expiringItems.forEach((item, index) => {
    const daysLeft = item.daysUntilExpiry || daysUntilExpiry(item.expiryDate);
    const emoji = getExpiryEmoji(daysLeft);
    const badgeClass = daysLeft <= 3 ? 'expiry-item-critical' : 'expiry-item-warning';
    const badgeText = daysLeft <= 1 ? '⏰ Urgent!' : '⚠️ Soon';
    
    itemsHTML += `
      <div class="expiry-item" style="animation-delay: ${index * 100}ms;">
        <div class="expiry-item-emoji">${emoji}</div>
        <div class="expiry-item-info">
          <div class="expiry-item-name">${escapeHtml(item.itemName)}</div>
          <div class="expiry-item-days">Expires in ${daysLeft} day${daysLeft !== 1 ? 's' : ''}</div>
          <div class="expiry-item-info-text">${formatDate(item.expiryDate)}</div>
        </div>
        <div class="expiry-item-badge ${badgeClass}">${badgeText}</div>
      </div>
    `;
  });
  
  content.innerHTML = itemsHTML;
  
  // Show modal with animation
  modal.style.display = 'flex';
  
  // Force reflow to trigger animation
  modal.offsetHeight;
  
  // Add show class for animation (if needed)
  modal.classList.add('show');
  
  console.log('✅ Popup displayed successfully with ' + expiringItems.length + ' items');
}

/**
 * Get emoji based on days until expiry
 */
function getExpiryEmoji(daysLeft) {
  if (daysLeft <= 1) return '🚨';
  if (daysLeft <= 3) return '⚠️';
  if (daysLeft <= 7) return '🥦';
  return '📦';
}

/**
 * Calculate days until expiry
 */
function daysUntilExpiry(expiryDateStr) {
  const expiry = new Date(expiryDateStr);
  const now = new Date();
  
  // Reset time to midnight for accurate day calculation
  expiry.setHours(0, 0, 0, 0);
  now.setHours(0, 0, 0, 0);
  
  const diff = expiry - now;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/**
 * Format date for display
 */
function formatDate(isoDate) {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch (e) {
    return isoDate;
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Close the expiry popup
 */
function closeExpiryPopup() {
  const modal = document.getElementById('expiry-popup-modal');
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('show');
  }
}

/**
 * Navigate to food tracker section
 */
function navigateToTracker() {
  closeExpiryPopup();
  
  // Click the food tracker nav button
  const trackerBtn = document.querySelector('[data-target="food-tracker-section"]');
  if (trackerBtn) {
    trackerBtn.click();
  }
}

/**
 * Close popup when clicking outside of it
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log('🎯 DOMContentLoaded event triggered');
  
  const modal = document.getElementById('expiry-popup-modal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      // Close only if clicking on the overlay itself, not the container
      if (e.target === modal) {
        closeExpiryPopup();
      }
    });
  }
  
  // Try to check for expiry items on initial load (with minimal delay)
  console.log('⏳ Scheduling expiry check in 500ms...');
  setTimeout(() => {
    if (typeof getCurrentUser === 'function') {
      const user = getCurrentUser();
      if (user && user.email) {
        console.log('👤 User detected, checking for expiry items');
        checkAndShowExpiryPopup();
      } else {
        console.log('⚠️ No user detected yet, will retry when app section is shown');
      }
    }
  }, 500);
});

/**
 * Auto-check for expiry items when app is shown
 * Hook into the showApp function
 */
const originalShowApp = window.showApp;
window.showApp = function() {
  console.log('🚀 showApp() called');
  if (originalShowApp) {
    originalShowApp.call(this);
  }
  
  // Check for expiry items after app is fully loaded
  console.log('⏳ Scheduling expiry check in 600ms after showApp...');
  setTimeout(() => {
    if (typeof checkAndShowExpiryPopup === 'function') {
      console.log('🔍 Calling checkAndShowExpiryPopup from showApp hook');
      checkAndShowExpiryPopup();
    }
  }, 600);
};
