// auth.js (defer on login & register pages)
const AUTH_API_BASE = (function() {
  // Use window.API_BASE_URL if available (set by utils.js or HTML)
  if (typeof window !== 'undefined' && window.API_BASE_URL) {
    return `${window.API_BASE_URL.replace(/\/$/, '')}/auth`;
  }
  // Fallback to default
  return 'http://localhost:5000/api/auth';
})();

function storeAuthPayload(payload) {
  if (!payload) return;
  if (payload.access_token) {
    try {
      localStorage.setItem('access_token', payload.access_token);
    } catch (err) {
      console.warn('Unable to persist access token', err);
    }
  }
  if (payload.user) {
    try {
      localStorage.setItem('current_user', JSON.stringify(payload.user));
    } catch (err) {
      console.warn('Unable to persist user profile', err);
    }
  }
}

function extractErrorMessage(result) {
  if (!result) return 'Request failed';
  return result.error || result.message || 'Request failed';
}

function showAuthLoader(text) {
  const overlay = document.getElementById('auth-loader');
  const caption = document.getElementById('auth-loader-text');
  if (caption && text) caption.textContent = text;
  if (overlay) overlay.classList.add('visible');
}

function hideAuthLoader() {
  const overlay = document.getElementById('auth-loader');
  if (overlay) {
    overlay.classList.remove('visible');
    overlay.classList.remove('success');
  }
}

function setAuthLoaderSuccess(state = false) {
  const overlay = document.getElementById('auth-loader');
  if (!overlay) return;
  overlay.classList.toggle('success', Boolean(state));
}

document.addEventListener('DOMContentLoaded', () => {
  // login form
  const loginForm = document.getElementById('loginForm');
  if(loginForm){
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = document.getElementById('login-identifier').value.trim();
      const pw = document.getElementById('login-password').value;
      const msg = document.getElementById('loginMessage');
      msg.textContent = 'Signing in...';
      try{
        showAuthLoader('Signing you in...');
        const res = await fetch(`${AUTH_API_BASE}/login`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({username:id,password:pw})
        });
        let result = null;
        let rawText = null;
        try {
          rawText = await res.text();
          result = rawText ? JSON.parse(rawText) : null;
        } catch (parseError) {
          console.warn('Login response could not be parsed as JSON', parseError, rawText);
        }
        if(res.ok){
          storeAuthPayload(result);
          setAuthLoaderSuccess(true);
          showAuthLoader('Welcome back! Preparing your dashboard…');
          msg.textContent = 'Signed in successfully. Redirecting...';
          loginForm.dataset.redirecting = 'true';
          
          // Reset expiry popup counter for new session
          if (typeof sessionStorage !== 'undefined') {
            const today = new Date().toDateString();
            const key = 'expiryPopupCount_' + today;
            sessionStorage.removeItem(key);
            console.log('✨ Expiry popup counter reset for new session');
          }
          
          setTimeout(()=> location.href = 'dashboard.html', 900);
        } else {
          msg.textContent = extractErrorMessage(result) || rawText || `Request failed (${res.status})`;
        }
      } catch(err){
        console.error('Login network error', err);
        msg.textContent = 'Network error. Make sure the backend is running on http://localhost:5000.';
      } finally {
        if (!loginForm.dataset.redirecting) {
          hideAuthLoader();
        }
      }
    });
  }

  // register form
  const registerForm = document.getElementById('registerForm');
  if(registerForm){
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('reg-name').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const pw = document.getElementById('reg-password').value;
      const household = document.getElementById('reg-household').value || '1';
      const msg = document.getElementById('registerMessage');
      msg.textContent = 'Creating account...';
      try{
        showAuthLoader('Creating your profile...');
        const res = await fetch(`${AUTH_API_BASE}/register`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            username: name,
            email,
            password: pw,
            household_size: household ? String(household).trim() : '1'
          })
        });
        let result = null;
        let rawText = null;
        try {
          rawText = await res.text();
          result = rawText ? JSON.parse(rawText) : null;
        } catch (parseError) {
          console.warn('Register response could not be parsed as JSON', parseError, rawText);
        }
        if(res.ok){
          storeAuthPayload(result);
          setAuthLoaderSuccess(true);
          showAuthLoader('Welcome! Taking you to your dashboard…');
          msg.textContent = 'Account created. Signing in...';
          registerForm.dataset.redirecting = 'true';
          setTimeout(()=> location.href = 'dashboard.html', 1000);
        } else {
          msg.textContent = extractErrorMessage(result) || rawText || `Request failed (${res.status})`;
        }
      } catch(err){
        console.error('Registration network error', err);
        msg.textContent = 'Network error. Make sure the backend is running on http://localhost:5000.';
      } finally {
        if (!registerForm.dataset.redirecting) {
          hideAuthLoader();
        }
      }
    });
  }
});
