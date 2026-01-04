/**
 * UI interaction functions
 */

let currentRecipe = null;
let currentRecipeId = null;

/**
 * Show login form
 */
function showLogin() {
    document.getElementById('login-form').classList.add('active');
    document.getElementById('register-form').classList.remove('active');
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.querySelectorAll('.tab-btn')[1].classList.remove('active');
}

/**
 * Show register form
 */
function showRegister() {
    document.getElementById('register-form').classList.add('active');
    document.getElementById('login-form').classList.remove('active');
    document.querySelectorAll('.tab-btn')[0].classList.remove('active');
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
}

/**
 * Show section
 * Made global for onclick handlers
 */
window.showSection = function(sectionName) {
  // Normalize section name - handle both "search" and "search-section" formats
  let normalizedName = sectionName;
  if (!normalizedName.includes('-section')) {
    normalizedName = `${sectionName}-section`;
  }
    
  // Hide all sections
  document.querySelectorAll('.section').forEach(section => {
    section.classList.remove('active');
  });
    
  // Show selected section
  const section = document.getElementById(normalizedName);
  if (section) {
    section.classList.add('active');
  }
    
  // Update nav buttons - match by data-target attribute
  document.querySelectorAll('.nav-btn[data-target]').forEach(btn => {
    const target = btn.getAttribute('data-target');
    // Match if target equals sectionName or normalizedName
    if (target === sectionName || target === normalizedName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
    
  // Load data if needed
  const baseName = normalizedName.replace('-section', '');
  if (baseName === 'lists') {
    if (typeof loadGroceryLists === 'function') {
      loadGroceryLists();
    }
  } else if (baseName === 'profile') {
    if (typeof loadProfile === 'function') {
      loadProfile();
    }
  }

  // When dashboard/search becomes active, show the expiring-items popup
  try {
    if (baseName === 'search' || baseName === 'dashboard') {
      // Use new expiry-alert-popup.js instead of old showExpiringPopup
      if (typeof checkAndShowExpiryPopup === 'function') checkAndShowExpiryPopup();
    }
  } catch (e) {
    console.warn('checkAndShowExpiryPopup error', e);
  }
};

/**
 * Display recipe results
 */
// Legacy template-based renderer removed to avoid duplicate/contradictory UI.
// The modern `displayRecipeResults(payload)` implementation later in this file
// is used for rendering recipe details and handles ingredients, instructions,
// nutrition and actions. Keeping a single renderer prevents duplicated sections
// and avoids UI text that implies automatic saving of extracted data.

/**
 * Generate grocery list
 * Made global for onclick handlers
 */
window.generateGroceryList = async function() {
    if (!currentRecipe) {
        showError('Please search for a recipe first');
        return;
    }
    
    const dishName = currentRecipe.dish_name;
    const householdSize = document.getElementById('household-size').value;
    
    if (!householdSize || householdSize < 1) {
        showError('Please enter a valid household size');
        return;
    }
    
    try {
        showLoading();
        const result = await groceryAPI.generate(dishName, householdSize, currentRecipeId);
        showSuccess('Grocery list generated successfully!');
        
        // Show the list
        showSection('lists');
        const listsNav = document.querySelector('.nav-btn[data-target="lists-section"]');
        if (listsNav) {
            document.querySelectorAll('.nav-btn[data-target], .nav-btn[data-action]').forEach(btn => btn.classList.remove('active'));
            listsNav.classList.add('active');
        }
        loadGroceryLists();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Add dish to favorites
 * Made global for onclick handlers
 */
window.addToFavorites = async function() {
    if (!currentRecipe) {
        showError('No recipe selected');
        return;
    }
    
    try {
        await dishAPI.addFavorite(currentRecipe.dish_name);
        showSuccess('Dish added to favorites!');
        loadProfile(); // Refresh profile to show updated favorites
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Load grocery lists
 */
async function loadGroceryLists() {
    const listsDiv = document.getElementById('grocery-lists');
    if (!listsDiv) return;
    
    try {
        showLoading('Pulling your saved grocery lists…');
        const result = await groceryAPI.getLists();
        const lists = result.grocery_lists || [];
        
        if (lists.length === 0) {
            listsDiv.innerHTML = '<p class="empty-state">No grocery lists yet. Search for a dish to get started!</p>';
            return;
        }
        
        let html = '';
        lists.forEach(list => {
            html += `
                <div class="grocery-list-card">
                    <h3>${list.dish_name}</h3>
                    <div class="meta">
                        Household Size: ${list.household_size} | Created: ${formatDate(list.created_at)}
                    </div>
                    <p><strong>Items:</strong> ${list.items.length}</p>
                    <div class="grocery-list-actions">
                        <button class="btn btn-primary" onclick="viewGroceryList('${list.id}')">View</button>
                        <button class="btn btn-success" onclick="downloadPDF('${list.id}')">Download PDF</button>
                        <button class="btn btn-secondary" onclick="downloadCSV('${list.id}')">Download CSV</button>
                        <button class="btn btn-secondary" onclick="deleteGroceryList('${list.id}')">Delete</button>
                    </div>
                </div>
            `;
        });
        
        listsDiv.innerHTML = html;
    } catch (error) {
        showError(error.message);
        listsDiv.innerHTML = '<p class="empty-state">Error loading grocery lists</p>';
    } finally {
        hideLoading();
    }
}

/**
 * View grocery list details
 */
async function viewGroceryList(listId) {
    try {
        showLoading('Opening grocery list…');
        const result = await groceryAPI.getList(listId);
        const list = result;
        
        // Display list in a modal or new section
        alert(`Grocery List: ${list.dish_name}\nItems: ${list.items.length}\nHousehold Size: ${list.household_size}`);
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Download PDF
 */
async function downloadPDF(listId) {
    try {
        showLoading('Preparing PDF download…');
        const result = await groceryAPI.downloadPDF(listId);
        if (result.pdf_url) {
            // Construct full URL if relative path
            const pdfUrl = result.pdf_url.startsWith('http') 
                ? result.pdf_url 
                : `http://localhost:5000${result.pdf_url}`;
            // Open in new tab for download
            window.open(pdfUrl, '_blank');
            showSuccess('PDF download started!');
        } else {
            showError('PDF URL not received from server');
        }
    } catch (error) {
        console.error('PDF download error:', error);
        showError(error.message || 'Failed to download PDF');
    } finally {
        hideLoading();
    }
}

/**
 * Download CSV
 */
async function downloadCSV(listId) {
    try {
        showLoading('Preparing CSV download…');
        const result = await groceryAPI.downloadCSV(listId);
        const csvData = result.csv_data;
        const dishName = result.dish_name;
        
        // Convert to CSV format
        let csv = 'Ingredient,Quantity,Unit,Category\n';
        csvData.forEach(item => {
            csv += `${item.ingredient},${item.quantity},${item.unit},${item.category}\n`;
        });
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${dishName}_grocery_list.csv`;
        a.click();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Delete grocery list
 */
async function deleteGroceryList(listId) {
    if (!confirm('Are you sure you want to delete this grocery list?')) {
        return;
    }
    
    try {
        showLoading('Deleting grocery list…');
        await groceryAPI.deleteList(listId);
        showSuccess('Grocery list deleted');
        loadGroceryLists();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Load user profile
 */
async function loadProfile() {
    try {
        showLoading('Loading your profile…');
        const result = await userAPI.getProfile();
        const user = result;
        
        // Update form fields
        document.getElementById('profile-household').value = user.household_size || '1';
        document.getElementById('profile-dietary').value = user.dietary_restrictions ? user.dietary_restrictions.join(', ') : '';
        
        // Load favorite dishes
        const favoritesDiv = document.getElementById('favorite-dishes');
        if (favoritesDiv && user.favorite_dishes) {
            let html = '';
            user.favorite_dishes.forEach(dish => {
                html += `<span class="favorite-dish-tag" onclick="searchDishFromFavorite('${dish}')">${dish}</span>`;
            });
            favoritesDiv.innerHTML = html || '<p>No favorite dishes yet</p>';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Search dish from favorite
 */
function searchDishFromFavorite(dishName) {
    document.getElementById('dish-name').value = dishName;
    showSection('search');
    document.getElementById('dish-search-form').dispatchEvent(new Event('submit'));
}

// Expiring-items popup: DISABLED - using new expiry-alert-popup.js instead
// async function showExpiringPopup() {
//   // avoid duplicates
//   if (document.querySelector('.expiring-popup')) return;
//   let resp;
//   try {
//     resp = await fetch('/api/tracker/alerts/expiring-soon');
//   } catch (e) {
//     return; // network issues - no popup
//   }
//   if (!resp || !resp.ok) return;
//   let data;
//   try { data = await resp.json(); } catch(e) { return; }
//
//   // Determine how many items to show in popup; prefer items for current user
//   let total = data.total || 0;
//   let userCount = 0;
//   try {
//     const user = window.currentUser || (typeof getCurrentUser === 'function' && getCurrentUser());
//     const email = user && (user.email || user.userEmail || user.username || user.emailAddress);
//     if (email && data.userAlerts && data.userAlerts[email]) userCount = data.userAlerts[email].length;
//   } catch(e) { /* ignore */ }
//
//   const count = userCount || total;
//   if (!count || count <= 0) return;
//
//   const popup = document.createElement('div');
//   popup.className = 'expiring-popup';
//   popup.innerHTML = `
//     <div class="emoji">⚠️</div>
//     <div class="meta">
//       <h4>Uh-oh — items expiring soon</h4>
//       <p>We found <span class="count">${count}</span> item${count>1 ? 's' : ''} nearing expiry.</p>
//     </div>
//     <div class="actions">
//       <button class="btn btn-view">View items</button>
//       <button class="btn btn-dismiss">Dismiss</button>
//     </div>
//   `;
//   document.body.appendChild(popup);
//   popup.querySelector('.btn-dismiss').addEventListener('click', () => popup.remove());
//   popup.querySelector('.btn-view').addEventListener('click', () => {
//     try { window.showSection && window.showSection('food-tracker'); } catch(e) {}
//     popup.remove();
//   });
//   setTimeout(() => { if (document.body.contains(popup)) popup.remove(); }, 14000);
// }

// CHANGES
// apply reveal class to elements that we want to animate in
document.addEventListener('DOMContentLoaded', () => {
  // mark elements
  document.querySelectorAll('.grocery-list-card, .recipe-results, .welcome-message, .ingredient-item, .favorite-dish-tag').forEach(el => {
    el.classList.add('reveal');
  });

  // ensure recipe-info items get reveal behavior
  const recipeInfo = document.getElementById('recipe-info');
  if (recipeInfo) {
    recipeInfo.classList.add('reveal');
  }

  // PDF upload wiring handled in pdfUpload.js, but let's ensure the button exists
  const pdfBtn = document.getElementById('pdf-upload-btn');
  if (pdfBtn) {
    pdfBtn.addEventListener('mouseover', ()=> pdfBtn.classList.add('hovering'));
    pdfBtn.addEventListener('mouseout', ()=> pdfBtn.classList.remove('hovering'));
  }
});


// ui.js - UI wiring and helpers

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupSearchForms();
  document.querySelectorAll('.nav-btn[data-target], .nav-btn[data-action]').forEach(btn => btn.addEventListener('click', navClick));
  showRecipeHint();
});

function navClick(e) {
  const t = e.currentTarget;
  document.querySelectorAll('.nav-btn[data-target], .nav-btn[data-action]').forEach(b=>b.classList.remove('active'));
  t.classList.add('active');
  const action = t.dataset.action;
  if (action && typeof window[action] === 'function') {
    window[action]();
    return;
  }
  const dest = t.dataset.target;
  if (dest) {
    // Use the global showSection function
    if (typeof window.showSection === 'function') {
      window.showSection(dest);
    } else {
      showSectionLocal(dest);
    }
  }
}

// Local showSection helper - use the global one instead
function showSectionLocal(id) {
  // If id already includes '-section', use it directly; otherwise add it
  const sectionId = id.includes('-section') ? id : `${id}-section`;
  document.querySelectorAll('[data-section]').forEach(s => {
    if (s.id === sectionId) s.classList.add('active');
    else s.classList.remove('active');
  });
  // Also update nav buttons
  document.querySelectorAll('.nav-btn[data-target]').forEach(btn => {
    const target = btn.getAttribute('data-target');
    btn.classList.toggle('active', target === id || target === sectionId);
  });
}

function setupTabs() {
  document.querySelectorAll('.search-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.search-tabs .tab-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.mode || 'name';
      switchSearchMethod(mode);
    });
  });
}

function switchSearchMethod(mode) {
  const nameForm = document.querySelector('[data-method="name"]');
  const urlForm = document.querySelector('[data-method="url"]');
  if (mode === 'name') {
    nameForm.style.display = '';
    urlForm.style.display = 'none';
  } else {
    nameForm.style.display = 'none';
    urlForm.style.display = '';
  }
}

// search forms
function setupSearchForms() {
  const dishForm = document.getElementById('dish-search-form');
  if (dishForm) {
    dishForm.dataset.enhanced = 'true';
    dishForm.addEventListener('input', () => {
      const hint = document.getElementById('recipe-hint');
      if (hint) hint.style.display = 'block';
    });
  }
  const recipeUrlForm = document.getElementById('recipe-url-form');
  if (recipeUrlForm) {
    recipeUrlForm.dataset.enhanced = 'true';
  }
}

// UI helpers
let __loadingCounter = 0;
function showLoading(text = 'Loading…') {
  const overlay = document.getElementById('loading');
  if (!overlay) return;
  const caption = overlay.querySelector('.loading-text');
  if (caption) caption.textContent = text;
  __loadingCounter = Math.max(__loadingCounter, 0) + 1;
  overlay.style.display = 'flex';
}
function hideLoading() {
  const overlay = document.getElementById('loading');
  if (!overlay) return;
  __loadingCounter = Math.max(0, __loadingCounter - 1);
  if (__loadingCounter === 0) {
    overlay.style.display = 'none';
  }
}
function showError(msg) {
  const em = document.getElementById('error-message');
  if (!em) return;
  em.textContent = msg;
  em.style.display = 'block';
  setTimeout(()=> em.style.display = 'none', 6000);
}
function showSuccess(msg) {
  const em = document.getElementById('error-message');
  if (!em) return;
  em.textContent = msg;
  em.style.display = 'block';
  em.style.background = 'rgba(40,200,120,0.06)';
  em.style.color = 'rgba(180,255,210,0.98)';
  setTimeout(()=> em.style.display = 'none', 4500);
}

// Helper: Show recipe sections progressively with auto-scroll
function showRecipeSections() {
  // Show section 2 (Recipe Details)
  const section2 = document.getElementById('recipe-section-2');
  if (section2) {
    section2.style.display = 'block';
    setTimeout(() => {
      section2.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }
  
  // Show section 3 (Instructions) after delay
  const section3 = document.getElementById('recipe-section-3');
  if (section3) {
    setTimeout(() => {
      section3.style.display = 'block';
      section3.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 800);
  }

  // Show section 3B (Actions) after instructions
  const section3b = document.getElementById('recipe-section-3b');
  if (section3b) {
    setTimeout(() => {
      section3b.style.display = 'block';
      section3b.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 1200);
  }
  
  // Show section 4 (Nutrition) after additional delay
  const section4 = document.getElementById('recipe-section-4');
  if (section4) {
    setTimeout(() => {
      section4.style.display = 'block';
      section4.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 1800);
  }
}

// Helper: Hide all recipe sections except section 1
function hideRecipeSections() {
  ['recipe-section-2', 'recipe-section-3', 'recipe-section-3b', 'recipe-section-4'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

// Display recipe results expected shape: { recipe: {...}, dish: { name }}
function displayRecipeResults(payload) {
  // Get all output containers for 4-section layout
  const container = document.getElementById('recipe-results');  // Section 2: Ingredients & Actions
  const instructionsContainer = document.getElementById('recipe-instructions'); // Section 3: Instructions
  const nutritionContainer = document.getElementById('recipe-nutrition'); // Section 4: Nutrition
  const actionsContainer = document.getElementById('recipe-actions'); // Actions container
  
  if (!container) return;
  const hint = document.getElementById('recipe-hint');
  if (hint) hint.style.display = 'none';

  currentRecipe = (payload && payload.recipe) || null;
  currentRecipeId = currentRecipe && (currentRecipe.id || currentRecipe._id) ? (currentRecipe.id || currentRecipe._id) : null;

  const dishMeta = (payload && payload.dish) || {};
  const user = (typeof getCurrentUser === 'function') ? getCurrentUser() : null;
  const dishName = dishMeta.name || (currentRecipe && (currentRecipe.title || currentRecipe.dish_name)) || 'Recipe';
  const servings = (currentRecipe && currentRecipe.servings) || dishMeta.servings || '';
  const sourceUrl = (currentRecipe && currentRecipe.source_url) || (currentRecipe && currentRecipe.raw_data && currentRecipe.raw_data.url);

  // Clear all output containers
  container.style.display = 'grid';
  container.innerHTML = '';
  if (instructionsContainer) instructionsContainer.innerHTML = '';
  if (nutritionContainer) nutritionContainer.innerHTML = '';
  if (actionsContainer) actionsContainer.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'recipe-header';

  const titleEl = document.createElement('h3');
  titleEl.textContent = dishName;
  header.appendChild(titleEl);

  if (servings) {
    const servingsEl = document.createElement('p');
    servingsEl.className = 'recipe-servings';
    servingsEl.innerHTML = `<strong>Servings:</strong> ${servings}`;
    header.appendChild(servingsEl);
  }

  if (sourceUrl) {
    const sourceEl = document.createElement('p');
    sourceEl.className = 'recipe-source';
    const link = document.createElement('a');
    link.href = sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'View original recipe';
    sourceEl.appendChild(link);
    header.appendChild(sourceEl);
  }

  container.appendChild(header);
  // Ingredients block - render aligned table (Quantity | Unit | Ingredient | Nutrition)
  const ingredientsWrap = document.createElement('div');
  ingredientsWrap.className = 'ingredients card';
  const ingredientsHeader = document.createElement('h4');
  ingredientsHeader.textContent = 'Ingredients';
  ingredientsWrap.appendChild(ingredientsHeader);

  const ingredients = (currentRecipe && currentRecipe.ingredients) || [];

  if (ingredients.length === 0) {
    const empty = document.createElement('p');
    empty.textContent = 'No ingredients detected for this recipe.';
    ingredientsWrap.appendChild(empty);
  } else {
    // Create table
    const table = document.createElement('table');
    table.className = 'ingredient-table';
    const thead = document.createElement('thead');
    const hrow = document.createElement('tr');
    ['Quantity', 'Measurement', 'Ingredient'].forEach(h => {
      const th = document.createElement('th');
      th.textContent = h;
      hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');

    // First pass: render ingredients with empty nutrition placeholders
  ingredients.forEach((rawItem, idx) => {
      // Accept either an object {name, quantity, unit} or string
      let parsed = { quantity: '', unit: '', name: '' };
      try {
        if (typeof rawItem === 'string' || typeof rawItem === 'number') {
          parsed = (window.IngredientUtils && window.IngredientUtils.parseIngredient) ? window.IngredientUtils.parseIngredient(String(rawItem)) : { quantity:'', unit:'', name:String(rawItem) };
        } else if (rawItem && typeof rawItem === 'object') {
          // Try to parse the name to ensure unit/quantity are filled in Indian style
          const p = (window.IngredientUtils && typeof window.IngredientUtils.parseIngredient === 'function') ? window.IngredientUtils.parseIngredient(rawItem.name || '') : { quantity:'', unit:'', name: rawItem.name || '' };
          // Prefer explicit values from the object but fill missing ones from parser
          parsed = Object.assign({}, { quantity: '', unit: '', name: '' }, p, rawItem);
          // ensure name stays readable
          parsed.name = (parsed.name || rawItem.name || '').trim();
          // If unit still missing, infer a sensible unit
          try {
            if ((!parsed.unit || parsed.unit.toString().trim() === '') && window.IngredientUtils && typeof window.IngredientUtils.inferUnit === 'function'){
              parsed.unit = window.IngredientUtils.inferUnit(parsed.name || '', parsed.quantity || '', parsed.unit || '');
            }
          } catch(e){ /* ignore */ }
        }
      } catch (err){
        parsed = rawItem || { quantity:'', unit:'', name: '' };
      }

      // Clean up obvious mis-mappings: don't show 'servings' as an ingredient unit
      try {
        if (parsed && parsed.unit) {
          const lu = parsed.unit.toString().toLowerCase();
          if (lu.includes('serv')) {
            parsed.unit = '';
          }
        }

        // If the parsed quantity equals the recipe servings value, it's likely the servings metadata was placed here by mistake
        const qtyNum = Number(parsed.quantity);
        if (!isNaN(qtyNum) && servings && Number(servings) === qtyNum) {
          parsed.quantity = '';
          parsed.unit = '';
        }
      } catch(e){ /* ignore cleanup errors */ }

      const tr = document.createElement('tr');
      tr.dataset.ingredientIndex = idx;
      tr.dataset.ingredientName = parsed.name;
  const tdQty = document.createElement('td');
  // If quantity missing but unit implies a count, show 1 by default
  let qtyDisplay = parsed.quantity || '';
      tdQty.style.width = '100px';
      const tdUnit = document.createElement('td');
      // Ensure measurement column is never empty: infer unit if missing
      let displayUnit = parsed.unit || '';
      try {
        if ((!displayUnit || displayUnit.toString().trim() === '') && window.IngredientUtils && typeof window.IngredientUtils.inferUnit === 'function'){
          displayUnit = window.IngredientUtils.inferUnit(parsed.name || '', parsed.quantity || '', parsed.unit || '');
        }
      } catch(e){ /* ignore */ }
      // Avoid showing 'nos' as a noisy measurement; show blank and default quantity to 1 instead
      if (displayUnit && displayUnit.toString().toLowerCase() === 'nos') {
        displayUnit = '';
        if (!qtyDisplay) qtyDisplay = '1';
      }
      tdUnit.textContent = displayUnit || '';
      tdQty.textContent = qtyDisplay || '';
      tdUnit.style.width = '120px';
      const tdName = document.createElement('td');
      tdName.className = 'ingredient-cell-name';
      tdName.textContent = parsed.name || '';

      tr.appendChild(tdQty);
      tr.appendChild(tdUnit);
      tr.appendChild(tdName);
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    ingredientsWrap.appendChild(table);
  }

  container.appendChild(ingredientsWrap);

  // Instructions block
  const instructionWrap = document.createElement('div');
  instructionWrap.className = 'instructions card';
  const instructionHeader = document.createElement('h4');
  const steps = (currentRecipe && currentRecipe.instructions) || [];
  instructionHeader.textContent = `Instructions (${steps.length} steps)`;
  instructionWrap.appendChild(instructionHeader);

  if (steps.length === 0) {
    const summary = (currentRecipe && currentRecipe.summary) || 'No instructions were provided for this recipe.';
    const empty = document.createElement('p');
    empty.textContent = summary;
    instructionWrap.appendChild(empty);
  } else {
    const list = document.createElement('ol');
    steps.forEach(step => {
      const li = document.createElement('li');
      li.textContent = step;
      list.appendChild(li);
    });
    instructionWrap.appendChild(list);
   
    // Log recipe stats for debugging
    console.log(`[Recipe] Loaded: ${steps.length} steps, ${(currentRecipe && currentRecipe.ingredients ? currentRecipe.ingredients.length : 0)} ingredients`);
  }

  // Append instructions to Section 3 (not Section 2)
  if (instructionsContainer) {
    instructionsContainer.appendChild(instructionWrap);
  } else {
    container.appendChild(instructionWrap);  // Fallback if container missing
  }

  // Action block for household size & buttons
  const actions = document.createElement('div');
  actions.className = 'recipe-actions';

  const householdField = document.createElement('div');
  householdField.className = 'household-field';

  const label = document.createElement('label');
  label.setAttribute('for', 'household-size');
  label.textContent = 'Number of people to cook for';
  householdField.appendChild(label);

  const input = document.createElement('input');
  input.type = 'number';
  input.id = 'household-size';
  input.min = '1';
  const defaultHousehold = (user && user.household_size) || servings || 1;
  input.value = defaultHousehold;
  householdField.appendChild(input);

  const helper = document.createElement('small');
  helper.className = 'household-helper';
  helper.textContent = servings ? `Default recipe serves ${servings}. Adjust to match your household.` : 'Adjust to match your household.';
  householdField.appendChild(helper);

  actions.appendChild(householdField);

  const buttonRow = document.createElement('div');
  buttonRow.className = 'action-buttons';

  const generateButton = document.createElement('button');
  generateButton.type = 'button';
  generateButton.className = 'btn btn-primary';
  generateButton.id = 'generate-grocery-btn';
  generateButton.textContent = 'Generate Grocery List';
  generateButton.addEventListener('click', () => {
    if (typeof generateGroceryList === 'function') {
      generateGroceryList();
    }
  });
  buttonRow.appendChild(generateButton);

  // Export / Copy buttons for ingredients
  const exportBtn = document.createElement('button');
  exportBtn.type = 'button';
  exportBtn.className = 'btn btn-secondary';
  exportBtn.textContent = 'Export Ingredients (CSV)';
  exportBtn.addEventListener('click', () => {
    if (typeof window.exportIngredientsCSV === 'function') window.exportIngredientsCSV();
  });
  buttonRow.appendChild(exportBtn);

  const copyBtn = document.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'btn btn-secondary';
  copyBtn.textContent = 'Copy Ingredients';
  copyBtn.addEventListener('click', () => {
    if (typeof window.copyIngredientsToClipboard === 'function') window.copyIngredientsToClipboard();
  });
  buttonRow.appendChild(copyBtn);

  if (typeof downloadIngredientsPDF === 'function' && currentRecipeId) {
    const pdfBtn = document.createElement('button');
    pdfBtn.type = 'button';
    pdfBtn.className = 'btn btn-secondary';
    pdfBtn.textContent = 'Download Ingredients PDF';
    pdfBtn.addEventListener('click', () => downloadIngredientsPDF(currentRecipeId));
    buttonRow.appendChild(pdfBtn);
  }

  if (typeof downloadRecipePDF === 'function' && currentRecipeId) {
    const stepsBtn = document.createElement('button');
    stepsBtn.type = 'button';
    stepsBtn.className = 'btn btn-secondary';
    stepsBtn.textContent = 'Download Steps PDF';
    stepsBtn.addEventListener('click', () => downloadRecipePDF(currentRecipeId));
    buttonRow.appendChild(stepsBtn);
  }

  actions.appendChild(buttonRow);
  
  // Append actions to Section 3B (after instructions, before nutrition)
  if (actionsContainer) {
    actionsContainer.appendChild(actions);
  } else {
    container.appendChild(actions);  // Fallback if container missing
  }

  // Nutrition block (after instructions) - ALWAYS show; estimate if missing
  const nutritionWrap = document.createElement('div');
  nutritionWrap.className = 'nutrition card';

  const nutritionTitle = document.createElement('h4');
  nutritionTitle.textContent = 'Nutrition Information';
  nutritionTitle.style.marginTop = '32px';
  nutritionWrap.appendChild(nutritionTitle);

  // 4x4 grid with icons
  const grid = document.createElement('div');
  grid.className = 'nutrition-4x4';

  // nutrient slots we want to show (fill to 12/16 slots gracefully)
  const desired = [
    { key: 'calories', label: 'Calories', unit: 'kcal', icon: '🔥' },
    { key: 'protein', label: 'Protein', unit: 'g', icon: '💪' },
    { key: 'fat', label: 'Fat', unit: 'g', icon: '🥑' },
    { key: 'carbs', label: 'Carbs', unit: 'g', icon: '🍞' },
    { key: 'fiber', label: 'Fiber', unit: 'g', icon: '🌾' },
    { key: 'sugar', label: 'Sugar', unit: 'g', icon: '🍬' },
    { key: 'sodium', label: 'Sodium', unit: 'mg', icon: '🧂' },
    { key: 'cholesterol', label: 'Cholesterol', unit: 'mg', icon: '🫙' },
    { key: 'vitaminC', label: 'Vitamin C', unit: 'mg', icon: '🍊' },
    { key: 'iron', label: 'Iron', unit: 'mg', icon: '🔩' },
    { key: 'calcium', label: 'Calcium', unit: 'mg', icon: '🦴' },
    { key: 'potassium', label: 'Potassium', unit: 'mg', icon: '🍌' },
    { key: 'saturatedFat', label: 'Sat. Fat', unit: 'g', icon: '🥓' },
    { key: 'transFat', label: 'Trans Fat', unit: 'g', icon: '⚠️' },
    { key: 'vitaminA', label: 'Vit. A', unit: 'µg', icon: '👁️' },
    { key: 'vitaminB12', label: 'Vit. B12', unit: 'µg', icon: '🧪' }
  ];

  // Source nutrition (if present) or estimate
  const sourceNutrition = (currentRecipe && currentRecipe.nutrition) ? currentRecipe.nutrition : null;
  let nutritionValues = {};

  if (sourceNutrition) {
    nutritionValues = sourceNutrition;
  } else {
    // Estimate using IngredientUtils if available (guarantees non-empty)
    try {
      if (window.IngredientUtils && typeof window.IngredientUtils.estimateNutrition === 'function') {
        const est = window.IngredientUtils.estimateNutrition(ingredients);
        nutritionValues = Object.assign({}, est);
        // ensure a calories property exists
        if (!nutritionValues.calories) nutritionValues.calories = est.calories || 0;
      }
    } catch (err) {
      nutritionValues = {};
    }

    // Asynchronously fetch authoritative nutrition from backend - ALWAYS display data
    async function fetchBackendNutrition(rawIngredients, servingsOverride) {
      try {
        // Build structured ingredient objects using frontend parser so backend gets quantity/unit/name
        const structured = rawIngredients.map(it => {
          let parsed = { quantity: '', unit: '', name: '' };
          try {
            if (typeof it === 'string' || typeof it === 'number') {
              parsed = (window.IngredientUtils && window.IngredientUtils.parseIngredient) ? window.IngredientUtils.parseIngredient(String(it)) : { quantity:'', unit:'', name:String(it) };
            } else if (it && typeof it === 'object') {
              parsed = (window.IngredientUtils && window.IngredientUtils.parseIngredient) ? window.IngredientUtils.parseIngredient(it.name || '') : { quantity:'', unit:'', name: it.name || '' };
              // prefer explicit fields if present
              parsed = Object.assign({}, parsed, { quantity: it.quantity || parsed.quantity, unit: it.unit || parsed.unit, name: (parseInt(it.quantity) ? parsed.name : (it.name || parsed.name)) });
            }
          } catch (e){ /* ignore parsing errors */ }
          // ensure unit is present when possible
          try {
            if ((!parsed.unit || parsed.unit.toString().trim()==='') && window.IngredientUtils && typeof window.IngredientUtils.inferUnit === 'function'){
              parsed.unit = window.IngredientUtils.inferUnit(parsed.name || '', parsed.quantity || '', parsed.unit || '');
            }
          } catch(e){}
          // final clean name
          parsed.name = (parsed.name || '').replace(/\s{2,}/g,' ').trim();
          return parsed;
        });

        const payload = { ingredients: structured, dish_name: (currentRecipe && currentRecipe.dish_name) ? currentRecipe.dish_name : '' };
        // Include requested servings if provided so backend can return per-serving totals
        if (typeof servingsOverride !== 'undefined' && servingsOverride !== null) payload.servings = Number(servingsOverride) || 1;
        console.log('[Nutrition] Sending to /api/dish/accurate-nutrition:', payload);
        const resp = await fetch('/api/dish/accurate-nutrition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          timeout: 30000
        });
        if (!resp || !resp.ok) {
          console.warn('[Nutrition] Backend endpoint failed:', resp ? resp.status : 'no response');
          return;
        }
        const json = await resp.json();
        console.log('[Nutrition] Backend response:', json);
        if (!json) return;

        // Always use totals returned by backend (from Google APIs/Spoonacular/USDA)
        const totals = (json.totals || json.nutrition || {});
        const results = json.results || [];
        console.log('[Nutrition] Totals from backend:', totals);

        // Merge totals into nutritionValues - ALWAYS update
        nutritionValues = Object.assign({}, nutritionValues, totals || {});
        console.log('[Nutrition] Updated nutritionValues:', nutritionValues);

        // Update DOM cards or rebuild grid to ALWAYS display
        const cards = grid.querySelectorAll('.nutrient-card');
        if (cards && cards.length > 0) {
          // Update existing cards with new values
          desired.forEach((slot, idx) => {
            const card = cards[idx];
            if (!card) return;
            const valEl = card.querySelector('.nutrient-value');
            const v = nutritionValues[slot.key] || nutritionValues[slot.key.toLowerCase()] || 0;
            if (valEl) valEl.textContent = (v || 0) + (slot.unit ? ` ${slot.unit}` : '');
          });
        } else {
          // Rebuild grid from scratch - ALWAYS show data
          const existingBadge = grid.querySelector('.nutrition-estimate-badge');
          if (existingBadge) existingBadge.remove();
          grid.innerHTML = '';
          
          // Show slots with actual data
          const presentSlots = desired.filter(slot => {
            const v = nutritionValues[slot.key] || nutritionValues[slot.key.toLowerCase()];
            return v !== undefined && v !== null && Number(v) > 0;
          });

          // ALWAYS show at least main macros (calories, protein, fat, carbs)
          const slotsToDisplay = presentSlots.length > 0 ? presentSlots : 
            desired.filter(slot => ['calories', 'protein', 'fat', 'carbs'].includes(slot.key));

          slotsToDisplay.forEach(slot => {
            let rawVal = nutritionValues[slot.key] || nutritionValues[slot.key.toLowerCase()] || 0;
            let val = rawVal;
            let unit = slot.unit || '';
            if (slot.key === 'calories') {
              val = Math.round(Number(val) || 0);
              unit = 'kcal';
            } else if (['sodium','cholesterol','iron','calcium','potassium','vitaminC','vitaminA','vitaminB12'].includes(slot.key)) {
              const num = Number(val) || 0;
              if (num >= 1) {
                val = Math.round(num);
                unit = unit || 'mg';
              } else {
                val = Math.round(num * 1000);
                unit = unit || 'µg';
              }
            } else {
              val = Math.round((Number(val) || 0) * 10) / 10;
              unit = unit || 'g';
            }

            const card = document.createElement('div');
            card.className = 'nutrient-card';

            const icon = document.createElement('div');
            icon.className = 'nutrient-icon';
            icon.textContent = slot.icon || '🍽️';

            const meta = document.createElement('div');
            const label = document.createElement('div');
            label.className = 'nutrient-label';
            label.textContent = slot.label;
            const value = document.createElement('div');
            value.className = 'nutrient-value';
            value.textContent = (val || 0) + (unit ? ` ${unit}` : '');

            meta.appendChild(label);
            meta.appendChild(value);

            card.appendChild(icon);
            card.appendChild(meta);
            grid.appendChild(card);
          });
        }

        // Show source badge if available
        try {
          if (json.source) {
            const src = document.createElement('div');
            src.style.marginTop = '12px';
            src.style.fontSize = '12px';
            src.style.color = '#888';
            src.textContent = `✓ Data from: ${json.source}`;
            nutritionWrap.appendChild(src);
          }
        } catch(e) { /* ignore */ }
      } catch (e) {
        console.warn('Backend nutrition fetch failed', e);
      }
    }

    // Expose the fetch function for reuse (e.g. when household size changes)
    try { container._fetchBackendNutrition = fetchBackendNutrition; } catch(e) { /* ignore */ }

    // Kick off backend fetch immediately using parsed ingredients
    fetchBackendNutrition(ingredients);

    // Recalculate nutrition when user changes household size
    try {
      input.addEventListener('change', () => {
        const val = Number(input.value) || 1;
        // Re-run authoritative backend nutrition fetch with desired servings
        if (typeof container._fetchBackendNutrition === 'function') {
          container._fetchBackendNutrition(ingredients, val);
        }
      });
    } catch(e) { /* ignore */ }
  }

  // Render grid cells - ALWAYS show nutrients (never empty)
  const presentSlots = desired.filter(slot => {
    const v = nutritionValues[slot.key] || nutritionValues[slot.key.toLowerCase()];
    return v !== undefined && v !== null && Number(v) > 0;
  });

  // If no slots with data, show the main macros anyway
  const slotsToDisplay = presentSlots.length > 0 ? presentSlots :
    desired.filter(slot => ['calories', 'protein', 'fat', 'carbs'].includes(slot.key));

  if (slotsToDisplay.length === 0) {
    // Absolute fallback - show a default set with estimator values
    const badge = document.createElement('div');
    badge.className = 'nutrition-estimate-badge';
    badge.style.padding = '8px 12px';
    badge.style.background = 'rgba(255,200,150,0.15)';
    badge.style.border = '1px solid rgba(255,150,100,0.2)';
    badge.style.borderRadius = '8px';
    badge.style.color = '#daa';
    badge.textContent = 'Nutrition shown is an estimate. Trying authoritative sources...';
    grid.appendChild(badge);
  } else {
    slotsToDisplay.forEach(slot => {
      const rawVal = nutritionValues[slot.key] || nutritionValues[slot.key.toLowerCase()] || 0;
      let val = rawVal;
      // formatting: calories integer, mg as integer, grams to 1 decimal
      let unit = slot.unit || '';
      if (slot.key === 'calories') {
        val = Math.round(Number(val) || 0);
        unit = 'kcal';
      } else if (['sodium','cholesterol','iron','calcium','potassium','vitaminC','vitaminA','vitaminB12'].includes(slot.key)) {
        // prefer mg or µg depending on magnitude
        const num = Number(val) || 0;
        if (num >= 1) {
          val = Math.round(num);
          unit = unit || 'mg';
        } else {
          val = Math.round(num * 1000);
          unit = unit || 'µg';
        }
      } else {
        // grams-like
        val = Math.round((Number(val) || 0) * 10) / 10;
        unit = unit || 'g';
      }

  const card = document.createElement('div');
      card.className = 'nutrient-card';

      const icon = document.createElement('div');
      icon.className = 'nutrient-icon';
      icon.textContent = slot.icon || '🍽️';

      const meta = document.createElement('div');
      const label = document.createElement('div');
      label.className = 'nutrient-label';
      label.textContent = slot.label;
      const value = document.createElement('div');
      value.className = 'nutrient-value';
      value.textContent = (val || 0) + (unit ? ` ${unit}` : '');

      meta.appendChild(label);
      meta.appendChild(value);

      card.appendChild(icon);
      card.appendChild(meta);
      grid.appendChild(card);
    });
  }

  // Show source badge if backend supplied a source (Spoonacular / Edamam)
  try {
    const provider = (currentRecipe && currentRecipe.nutrition && currentRecipe.nutrition.source) || null;
    if (!provider && typeof window._lastNutritionSource !== 'undefined') {
      // try global last fetched source
      provider = window._lastNutritionSource;
    }
    if (provider) {
      const src = document.createElement('div');
      src.className = 'nutrition-source-badge';
      src.style.marginTop = '8px';
      src.style.fontSize = '13px';
      src.style.color = '#bbb';
      src.textContent = `Source: ${provider}`;
      nutritionWrap.appendChild(src);
    }
  } catch(e) {
    /* ignore */
  }

  nutritionWrap.appendChild(grid);
  
  // Append nutrition to Section 4 (not Section 2)
  if (nutritionContainer) {
    nutritionContainer.appendChild(nutritionWrap);
  } else {
    container.appendChild(nutritionWrap);  // Fallback if container missing
  }

  // Attach helpers for export/copy so buttons work
  window.exportIngredientsCSV = function() {
    try {
      const table = container.querySelector('.ingredient-table');
      if (!table) return showError('No ingredients table found to export');
      let csv = 'Quantity,Measurement,Ingredient\n';
      Array.from(table.querySelectorAll('tbody tr')).forEach(tr => {
        const cols = tr.querySelectorAll('td');
        const q = (cols[0] && cols[0].textContent.trim()) || '';
        const u = (cols[1] && cols[1].textContent.trim()) || '';
        const n = (cols[2] && cols[2].textContent.trim()) || '';
        // Escape commas in ingredient name
        const nameEsc = '"' + n.replace(/"/g,'""') + '"';
        csv += `${q},${u},${nameEsc}\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dishName.replace(/\s+/g,'_')}_ingredients.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showSuccess('Ingredients exported as CSV');
    } catch (err) {
      console.error('Export error', err);
      showError('Failed to export ingredients');
    }
  };

  window.copyIngredientsToClipboard = function() {
    try {
      const table = container.querySelector('.ingredient-table');
      if (!table) return showError('No ingredients table found to copy');
      let text = '';
      Array.from(table.querySelectorAll('tbody tr')).forEach(tr => {
        const cols = tr.querySelectorAll('td');
        const q = (cols[0] && cols[0].textContent.trim()) || '';
        const u = (cols[1] && cols[1].textContent.trim()) || '';
        const n = (cols[2] && cols[2].textContent.trim()) || '';
        text += `${q} ${u} ${n}\n`;
      });
      navigator.clipboard.writeText(text).then(()=> showSuccess('Ingredients copied to clipboard'), ()=> showError('Clipboard write failed'));
    } catch (err) {
      console.error('Copy error', err);
      showError('Failed to copy ingredients');
    }
  };

  container.classList.add('reveal');
  setTimeout(() => container.classList.add('in-view'), 80);
  
  // Show recipe sections progressively with animations and auto-scroll
  showRecipeSections();
}

function showRecipeHint() {
  const hint = document.getElementById('recipe-hint');
  const container = document.getElementById('recipe-results');
  if (hint) hint.style.display = 'block';
  if (container) {
    container.innerHTML = '';
    container.style.display = 'none';
  }
  // Hide sections when showing hint
  hideRecipeSections();
}
