/**
 * Main application logic
 */

// Suppress third-party library errors (quillbot, etc)
window.addEventListener('error', (event) => {
  if (event.filename && (event.filename.includes('quillbot') || event.filename.includes('quill'))) {
    // Suppress Quill library errors - they won't affect our app
    event.preventDefault();
    return true;
  }
});

// Suppress unhandled promise rejections from third-party libraries
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason && event.reason.message && 
      event.reason.message.includes('updateCopyPasteInfo')) {
    // Suppress Quill clipboard errors
    event.preventDefault();
    return true;
  }
});

// Check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    
    // Setup form handlers
    setupFormHandlers();
});

// CHANGES 
// Smooth show/hide of sections (replace direct style changes if present)
function showSectionAnimated(sectionName) {
  const sections = document.querySelectorAll('.section');
  sections.forEach(s => {
    if (s.id === `${sectionName}-section`) {
      s.classList.add('active');
      s.classList.add('reveal');
    } else {
      s.classList.remove('active');
    }
  });
}

/**
 * Check if user is authenticated
 */
function checkAuth() {
    if (typeof getToken !== 'function') {
        return;
    }
    const token = getToken();
    const user = getCurrentUser();
    const appSection = document.getElementById('app-section');
    const authSection = document.getElementById('auth-section');
    const onDashboard = window.location.pathname.toLowerCase().includes('dashboard.html');
    
    if (!appSection && !authSection && !onDashboard) {
        // Landing or other page that doesn't use the app shell
        return;
    }

    if (token && user) {
        // User is logged in
        if (appSection) {
            showApp();
        }
    } else {
        if (onDashboard) {
            window.location.replace('login.html');
            return;
        }
        // User is not logged in but page has auth/app shells
        if (authSection) {
            showAuth();
        }
    }
}

/**
 * Show authentication section
 */
function showAuth() {
    const authSection = document.getElementById('auth-section');
    const appSection = document.getElementById('app-section');
    const landingShell = document.getElementById('landing-shell');
    if (authSection) authSection.style.display = 'block';
    if (appSection) appSection.style.display = 'none';
    if (landingShell) landingShell.style.display = '';
    if (landingShell) {
        document.body.classList.remove('app-active');
        // Only drop theme class if we're on the landing page with a shell
        if (!window.location.pathname.toLowerCase().includes('dashboard.html')) {
            document.body.classList.remove('dashboard-theme');
        }
    }
}

/**
 * Show app section
 */
function showApp() {
    const authSection = document.getElementById('auth-section');
    const appSection = document.getElementById('app-section');
    const landingShell = document.getElementById('landing-shell');
    if (authSection) authSection.style.display = 'none';
    if (landingShell) landingShell.style.display = 'none';
    if (!document.body.classList.contains('dashboard-theme')) {
        document.body.classList.add('dashboard-theme');
    }
    document.body.classList.add('app-active');
    if (appSection) {
        appSection.style.display = 'block';
    }
    
    // Show welcome message with username
    const user = getCurrentUser();
    if (user && user.username) {
        const welcomeText = document.getElementById('welcome-text');
        if (welcomeText) {
            welcomeText.textContent = `Welcome Back, ${user.username}!`;
        }
    }

    if (!showApp._initialized) {
        showApp._initialized = true;
        if (typeof showSection === 'function') {
            showSection('search');
        }
        if (typeof loadGroceryLists === 'function') {
            loadGroceryLists();
        }
        if (typeof loadProfile === 'function') {
            loadProfile();
        }
    }
}

/**
 * Setup form handlers
 */
function setupFormHandlers() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Register form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Dish search form
    const dishSearchForm = document.getElementById('dish-search-form');
    if (dishSearchForm) {
        dishSearchForm.addEventListener('submit', handleDishSearch);
    }
    
    // Recipe URL form
    const recipeUrlForm = document.getElementById('recipe-url-form');
    if (recipeUrlForm) {
        recipeUrlForm.addEventListener('submit', handleRecipeUrl);
    }
    
    // Profile form
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
}

/**
 * Handle login
 */
async function handleLogin(e) {
    e.preventDefault();
    
    // Prevent multiple submissions
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.disabled) {
        return; // Already submitting
    }
    
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    
    if (!username || !password) {
        showError('Please enter username and password');
        return;
    }
    
    try {
        showLoading();
        if (submitBtn) submitBtn.disabled = true;
        
        const result = await authAPI.login(username, password);
        
        setToken(result.access_token);
        setCurrentUser(result.user);
        
        showApp();
        showSuccess('Login successful!');
    } catch (error) {
        console.error('Login error:', error);
        showError(error.message || 'Login failed. Please check your credentials.');
    } finally {
        hideLoading();
        if (submitBtn) submitBtn.disabled = false;
    }
}

/**
 * Handle register
 */
async function handleRegister(e) {
    e.preventDefault();
    
    // Prevent multiple submissions
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.disabled) {
        return; // Already submitting
    }
    
    const username = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const householdSize = document.getElementById('register-household').value || '1';
    
    // Basic client-side validation
    if (!username || !email || !password) {
        showError('Please fill in all required fields');
        return;
    }
    
    if (password.length < 6) {
        showError('Password must be at least 6 characters');
        return;
    }
    
    try {
        showLoading();
        if (submitBtn) submitBtn.disabled = true;
        
        // Debug: Log what we're sending
        console.log('=== REGISTRATION REQUEST ===');
        console.log('Username:', username);
        console.log('Email:', email);
        console.log('Password length:', password.length);
        console.log('Household Size:', householdSize);
        
        const requestData = {
            username: username.trim(),
            email: email.trim().toLowerCase(),
            password: password,
            household_size: householdSize ? String(householdSize).trim() : '1'
        };
        console.log('Request data:', requestData);
        
        const result = await authAPI.register(username, email, password, householdSize);
        
        console.log('Registration success:', result);
        setToken(result.access_token);
        setCurrentUser(result.user);
        
        showApp();
        showSuccess('Registration successful!');
    } catch (error) {
        console.error('Registration error:', error);
        console.error('Error details:', {
            message: error.message,
            stack: error.stack
        });
        showError(error.message || 'Registration failed. Please try again.');
    } finally {
        hideLoading();
        if (submitBtn) submitBtn.disabled = false;
    }
}

/**
 * Handle dish search
 */
async function handleDishSearch(e) {
    e.preventDefault();
    
    // Ensure dishAPI is available
    if (typeof window.dishAPI === 'undefined' || !window.dishAPI) {
        console.error('dishAPI is not available. Make sure api.js is loaded.');
        showError('🔴 API not loaded. Please refresh the page.');
        return;
    }
    
    const dishAPI = window.dishAPI;
    const dishName = document.getElementById('dish-name').value.trim();
    
    if (!dishName) {
        showError('Please enter a dish name');
        return;
    }
    
    try {
        showLoading();
        const resultsContainer = document.getElementById('recipe-results');
        const placeholder = document.getElementById('recipe-hint');
        if (resultsContainer) resultsContainer.style.display = 'none';
        if (placeholder) placeholder.style.display = 'none';
        if (document.getElementById('error-message')) {
            document.getElementById('error-message').style.display = 'none';
        }
        
        const result = await dishAPI.search(dishName);
        
        // Check if we got a valid result (even if it's a fallback)
        if (result && result.recipe) {
            if (typeof displayRecipeResults === 'function') {
                displayRecipeResults(result);
            }
            
            // Check if the recipe has meaningful data
            const hasIngredients = result.recipe.ingredients && result.recipe.ingredients.length > 1;
            const hasInstructions = result.recipe.instructions && result.recipe.instructions.length > 0;
            
            if (hasIngredients && hasInstructions) {
                showSuccess(`✅ Perfect! Found recipe for "${dishName}" with complete ingredients and instructions.`);
            } else if (hasIngredients) {
                showSuccess(`✅ Found "${dishName}" with ${result.recipe.ingredients.length} ingredients. Instructions may be limited.`);
            } else {
                showError(`⚠️ Recipe structure created for "${dishName}", but detailed ingredients couldn't be found. Try entering a recipe URL from a cooking website instead.`);
            }
        } else {
            throw new Error('Unable to fetch recipe. Please try again or use a recipe URL from a cooking website.');
        }
    } catch (error) {
        console.error('Dish search error:', error);
        
        if (typeof showError === 'function') {
            let errorMsg = error.message || 'Unable to fetch recipe details. ';
            
            // Provide helpful suggestions
            if (errorMsg.includes('Could not extract') || errorMsg.includes('Unable to')) {
                errorMsg += '\n\n💡 Suggestions:\n• Try a more specific dish name (e.g., "Chicken Biryani" instead of just "Biryani")\n• Or paste a recipe URL from a cooking website (AllRecipes, Food.com, etc.)';
            }
            
            showError(errorMsg);
        }
        
        if (typeof showRecipeHint === 'function') {
            showRecipeHint();
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}

/**
 * Handle recipe URL submission
 */
async function handleRecipeUrl(e) {
    e.preventDefault();
    
    // Ensure dishAPI is available
    if (typeof window.dishAPI === 'undefined' || !window.dishAPI) {
        console.error('dishAPI is not available. Make sure api.js is loaded.');
        showError('🔴 API not loaded. Please refresh the page.');
        return;
    }
    
    const dishAPI = window.dishAPI;
    const recipeUrl = document.getElementById('recipe-url').value.trim();
    
    if (!recipeUrl) {
        showError('Please enter a recipe URL');
        return;
    }
    
    // Basic URL validation
    try {
        new URL(recipeUrl);
    } catch (error) {
        showError('Please enter a valid URL (e.g., https://example.com/recipe)');
        return;
    }
    
    try {
        showLoading();
        const resultsContainer = document.getElementById('recipe-results');
        const placeholder = document.getElementById('recipe-hint');
        if (resultsContainer) resultsContainer.style.display = 'none';
        if (placeholder) placeholder.style.display = 'none';
        if (document.getElementById('error-message')) {
            document.getElementById('error-message').style.display = 'none';
        }
        
        const result = await dishAPI.extractFromUrl(recipeUrl);
        
        if (typeof displayRecipeResults === 'function') {
            displayRecipeResults(result);
        }
        if (typeof showSuccess === 'function') {
            showSuccess('✅ Recipe extracted successfully! Ingredients and instructions have been extracted. Review and save if you want to keep this recipe.');
        }
    } catch (error) {
        console.error('Recipe URL extraction error:', error);
        if (typeof showError === 'function') {
            let errorMsg = error.message || 'Could not extract recipe from URL. ';
            
            // Provide suggestions
            if (errorMsg.includes('Could not extract') || errorMsg.includes('timeout')) {
                errorMsg += '\n\n💡 Tips:\n• Make sure the URL is correct and accessible\n• Try URLs from popular cooking sites like AllRecipes, Food.com, or BBC Good Food\n• The website may block automated access - try a different recipe URL';
            }
            
            showError(errorMsg);
        }
        if (typeof showRecipeHint === 'function') {
            showRecipeHint();
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}

/**
 * Switch between search methods
 * Made global for onclick handlers
 */
window.switchSearchMethod = function(method) {
    const nameForm = document.getElementById('dish-search-form');
    const urlForm = document.getElementById('recipe-url-form');
    const tabs = document.querySelectorAll('.search-tabs .tab-btn');
    
    if (!nameForm || !urlForm) {
        console.error('Search forms not found');
        return;
    }
    
    if (method === 'name') {
        nameForm.style.display = 'block';
        urlForm.style.display = 'none';
        if (tabs.length >= 2) {
            tabs[0].classList.add('active');
            tabs[1].classList.remove('active');
        }
    } else {
        nameForm.style.display = 'none';
        urlForm.style.display = 'block';
        if (tabs.length >= 2) {
            tabs[0].classList.remove('active');
            tabs[1].classList.add('active');
        }
    }
};

/**
 * Download recipe PDF
 * Made global for onclick handlers
 */
window.downloadRecipePDF = async function() {
    if (!currentRecipeId) {
        showError('No recipe selected');
        return;
    }
    
    try {
        showLoading();
        const result = await dishAPI.downloadRecipePDF(currentRecipeId);
        if (result.pdf_url) {
            // Construct full URL if relative path
            const pdfUrl = result.pdf_url.startsWith('http') 
                ? result.pdf_url 
                : `http://localhost:5000${result.pdf_url}`;
            window.open(pdfUrl, '_blank');
            showSuccess('Recipe steps PDF downloaded!');
        } else {
            showError('PDF URL not received from server');
        }
    } catch (error) {
        showError(error.message || 'Failed to download recipe PDF');
    } finally {
        hideLoading();
    }
}

/**
 * Download ingredients PDF
 * Made global for onclick handlers
 */
window.downloadIngredientsPDF = async function() {
    if (!currentRecipeId) {
        showError('No recipe selected');
        return;
    }
    
    try {
        showLoading();
        const result = await dishAPI.downloadIngredientsPDF(currentRecipeId);
        if (result.pdf_url) {
            // Construct full URL if relative path
            const pdfUrl = result.pdf_url.startsWith('http') 
                ? result.pdf_url 
                : `http://localhost:5000${result.pdf_url}`;
            window.open(pdfUrl, '_blank');
            showSuccess('Ingredients PDF downloaded!');
        } else {
            showError('PDF URL not received from server');
        }
    } catch (error) {
        showError(error.message || 'Failed to download ingredients PDF');
    } finally {
        hideLoading();
    }
}

/**
 * Handle profile update
 */
async function handleProfileUpdate(e) {
    e.preventDefault();
    
    const householdSize = document.getElementById('profile-household').value;
    const dietary = document.getElementById('profile-dietary').value;
    const dietaryRestrictions = dietary ? dietary.split(',').map(d => d.trim()) : [];
    
    try {
        showLoading();
        await userAPI.updateProfile({
            household_size: householdSize,
            dietary_restrictions: dietaryRestrictions
        });
        
        // Update local user
        const user = getCurrentUser();
        if (user) {
            user.household_size = householdSize;
            user.dietary_restrictions = dietaryRestrictions;
            setCurrentUser(user);
        }
        
        showSuccess('Profile updated successfully!');
    } catch (error) {
        showError(error.message || 'Failed to update profile');
    } finally {
        hideLoading();
    }
}

/**
 * Logout
 * Made global for onclick handlers
 */
window.logout = function() {
    removeToken();
    removeCurrentUser();
    
    // Reset expiry popup counter for next session
    if (typeof sessionStorage !== 'undefined') {
        const today = new Date().toDateString();
        const key = 'expiryPopupCount_' + today;
        sessionStorage.removeItem(key);
        console.log('🔄 Expiry popup counter reset on logout');
    }
    
    const authSection = document.getElementById('auth-section');
    const landingShell = document.getElementById('landing-shell');
    const appSection = document.getElementById('app-section');
    if (landingShell) {
        if (appSection) {
            appSection.style.display = 'none';
        }
        showAuth();
        showSuccess('Logged out successfully');
        // Redirect to landing page after short delay
        setTimeout(() => {
            window.location.replace('index.html');
        }, 1500);
        return;
    }
    if (authSection) {
        showAuth();
        showSuccess('Logged out successfully');
    }
    // Redirect to landing page
    setTimeout(() => {
        window.location.replace('index.html');
    }, 1500);
}

// main.js (defer included in index.html)
document.addEventListener('DOMContentLoaded', () => {
  const ctaExplore = document.getElementById('ctaExplore');
  const videoSection = document.getElementById('video-section');
  const ctaToApp = document.getElementById('ctaToApp');

  if(ctaExplore){
    ctaExplore.addEventListener('click', () => {
      videoSection.scrollIntoView({behavior: 'smooth'});
    });
  }

  if(ctaToApp){
    ctaToApp.addEventListener('click', () => {
      // scroll to bottom anchor (app)
      document.getElementById('app-anchor').scrollIntoView({behavior:'smooth'});
    });
  }

  // Improve mobile autoplay behavior; ensure video starts muted & looped
  const v = document.getElementById('foodVideo');
  if(v){
    v.muted = true;
    v.loop = true;
    v.play().catch(()=>{ /* autoplay blocked - user will manually interact */ });
  }
});


// main.js - global bootstrap

document.addEventListener('DOMContentLoaded', () => {
  // Make sure dashboard nav gets initialized without touching landing links
  const firstNav = document.querySelector('.nav-btn[data-target]');
  if (firstNav) firstNav.classList.add('active');

  // keyboard shortcuts for quick testing
  document.addEventListener('keydown', (e) => {
    if (e.key === '1') document.querySelector('[data-target="search-section"]').click();
    if (e.key === '2') document.querySelector('[data-target="lists-section"]').click();
    if (e.key === '3') document.querySelector('[data-target="profile-section"]').click();
  });

  // make focus visible for keyboard users
  document.addEventListener('keyup', (e) => {
    if (e.key === 'Tab') document.body.classList.add('show-focus');
  });
});
