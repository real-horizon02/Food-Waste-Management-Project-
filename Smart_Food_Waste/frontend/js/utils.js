/**
 * Utility helpers shared across the frontend
 */

(function establishApiBase() {
    if (typeof window === 'undefined') return;
    // Only set if not already set (allows HTML to override)
    if (!window.API_BASE_URL) {
        const defaultBase = 'http://localhost:5000/api';
        window.API_BASE_URL = defaultBase;
    }
})();

// Use window.API_BASE_URL, don't declare a const that might conflict
// Other files should use window.API_BASE_URL directly or get it from here
if (typeof window !== 'undefined' && !window.__API_BASE_SET__) {
    window.__API_BASE_SET__ = true;
}

function getToken() {
    try {
        return localStorage.getItem('access_token') || null;
    } catch (error) {
        console.warn('Unable to read access token from storage', error);
        return null;
    }
}

function setToken(token) {
    try {
        if (token) {
            localStorage.setItem('access_token', token);
        } else {
            localStorage.removeItem('access_token');
        }
    } catch (error) {
        console.warn('Unable to persist access token', error);
    }
}

function removeToken() {
    try {
        localStorage.removeItem('access_token');
    } catch (error) {
        console.warn('Unable to remove access token', error);
    }
}

function getCurrentUser() {
    try {
        const userStr = localStorage.getItem('current_user');
        return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
        console.warn('Unable to read current user', error);
        return null;
    }
}

function setCurrentUser(user) {
    try {
        if (user) {
            localStorage.setItem('current_user', JSON.stringify(user));
        } else {
            localStorage.removeItem('current_user');
        }
    } catch (error) {
        console.warn('Unable to persist current user', error);
    }
}

function removeCurrentUser() {
    try {
        localStorage.removeItem('current_user');
    } catch (error) {
        console.warn('Unable to remove current user', error);
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (!errorDiv) return;
    
    // Remove success class if present
    errorDiv.classList.remove('success-message');
    errorDiv.classList.add('error-message');
    
    // Format message with better visibility
    errorDiv.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 10px;">
            <span style="font-size: 18px; flex-shrink: 0;">❌</span>
            <div style="flex: 1;">
                <strong>Error:</strong><br/>
                ${message.replace(/\n/g, '<br/>')}
            </div>
            <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; cursor: pointer; font-size: 20px; flex-shrink: 0;">✕</button>
        </div>
    `;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 8 seconds, but allow manual close
    setTimeout(() => {
        if (errorDiv.style.display !== 'none') {
            errorDiv.style.display = 'none';
        }
    }, 8000);
}

function showSuccess(message) {
    const errorDiv = document.getElementById('error-message');
    if (!errorDiv) return;
    
    // Remove error class if present
    errorDiv.classList.remove('error-message');
    errorDiv.classList.add('success-message');
    
    // Format message with better visibility
    errorDiv.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 10px;">
            <span style="font-size: 18px; flex-shrink: 0;">✅</span>
            <div style="flex: 1;">
                <strong>Success:</strong><br/>
                ${message.replace(/\n/g, '<br/>')}
            </div>
            <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; cursor: pointer; font-size: 20px; flex-shrink: 0;">✕</button>
        </div>
    `;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 6 seconds
    setTimeout(() => {
        if (errorDiv.style.display !== 'none') {
            errorDiv.style.display = 'none';
        }
    }, 6000);
}

function showLoading() {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.style.display = 'block';
    }
}

function hideLoading() {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.style.display = 'none';
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}
