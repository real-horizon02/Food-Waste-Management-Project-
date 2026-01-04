(function(window){
  const state = { lastRenderedId: null };

  function clearContainer(container) {
    while (container.firstChild) container.removeChild(container.firstChild);
  }

  function createDownloadButton(onClick){
    const btn = document.createElement('button');
    btn.id = 'download-pdf-btn';
    btn.className = 'btn primary';
    btn.textContent = 'Download PDF';
    btn.addEventListener('click', onClick);
    return btn;
  }

  async function renderRecipe(containerSelector, recipe, options = {}){
    const container = typeof containerSelector === 'string' ? document.querySelector(containerSelector) : containerSelector;
    if (!container) return;

    // Prevent duplicate renders for the same recipe object id/title
    const recipeId = (recipe && (recipe.title || recipe.searchQuery)) || '__unknown__';
    if (state.lastRenderedId === recipeId) {
      // still update servings if needed
      if (options.servings && options.fetchScaled) await fetchAndRenderScaled(options.fetchScaled, recipe.searchQuery || recipe.title, options.servings, container, options);
      return;
    }
    state.lastRenderedId = recipeId;

    clearContainer(container);

    const title = document.createElement('h2');
    title.textContent = recipe.title || recipe.searchQuery || 'Recipe';
    container.appendChild(title);

    // Servings control
    const sRow = document.createElement('div');
    sRow.className = 'servings-row';
    sRow.innerHTML = `<label>Servings: <input id="servings-input" type="number" min="1" value="${recipe.servings || 1}"/></label>`;
    container.appendChild(sRow);
    const servingsInput = sRow.querySelector('#servings-input');
    servingsInput.addEventListener('change', async (e)=>{
      const newServ = Number(e.target.value) || 1;
      if (options.fetchScaled) {
        await fetchAndRenderScaled(options.fetchScaled, recipe.searchQuery || recipe.title, newServ, container, options);
      } else {
        // local scale: scale ingredient quantities and adjust displayed nutrition if present
        scaleDisplayedRecipe(container, newServ);
      }
    });

    // Ingredients
    const ingHeader = document.createElement('h3');
    ingHeader.textContent = 'Ingredients';
    container.appendChild(ingHeader);

    const ul = document.createElement('ul');
    ul.id = 'recipe-ingredients';
    (recipe.ingredients || []).forEach(ing => {
      const li = document.createElement('li');
      const qty = (ing.quantity === null || ing.quantity === undefined) ? '' : (ing.quantity + ' ' + (ing.unit || ''));
      li.textContent = `${qty} ${ing.name || ''}`.trim();
      ul.appendChild(li);
    });
    container.appendChild(ul);

    // Instructions
    const instrHeader = document.createElement('h3');
    instrHeader.textContent = 'Instructions';
    container.appendChild(instrHeader);

    const ol = document.createElement('ol');
    ol.id = 'recipe-instructions';
    (recipe.steps || []).forEach((step, idx) => {
      const li = document.createElement('li');
      li.textContent = `Step ${idx+1}: ${step}`;
      ol.appendChild(li);
    });
    container.appendChild(ol);

    // Nutrition
    const nutHeader = document.createElement('h3');
    nutHeader.textContent = 'Nutrition (per serving)';
    container.appendChild(nutHeader);

    const nutDiv = document.createElement('div');
    nutDiv.id = 'recipe-nutrition';
    nutDiv.className = 'nutrition-grid';
    const nut = recipe.nutrition || {};
    ['calories','protein','fat','carbs'].forEach(k => {
      const p = document.createElement('div');
      p.className = 'nut-item';
      p.innerHTML = `<strong>${k[0].toUpperCase()+k.slice(1)}:</strong> ${nut[k] ?? 'N/A'}`;
      nutDiv.appendChild(p);
    });
    container.appendChild(nutDiv);

    // Download PDF button (ensure only one)
    let existingBtn = document.getElementById('download-pdf-btn');
    if (existingBtn) existingBtn.remove();
    const btn = createDownloadButton(()=>{ if (options.onDownload) options.onDownload(recipe); else window.open(options.pdfUrl || '/api/recipe/generate_pdf', '_blank'); });
    container.appendChild(btn);
  }

  async function fetchAndRenderScaled(fetchUrl, query, servings, container, options) {
    try {
      const payload = { dish_name: query, servings, save: false };
      const resp = await fetch(fetchUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await resp.json();
      if (data && data.recipe) {
        renderRecipe(container, data.recipe, Object.assign({}, options, { fetchScaled: fetchUrl }));
      } else {
        console.warn('No recipe returned from scaled fetch', data);
      }
    } catch (e) { console.warn('Failed to fetch scaled recipe', e); }
  }

  function scaleDisplayedRecipe(container, newServings) {
    const currentServ = Number(container.querySelector('#servings-input')?.value || 1);
    if (!currentServ || currentServ === newServings) return;
    const scale = newServings / currentServ;
    // Update ingredient quantities displayed (best-effort: assumes format "<qty> <unit> name")
    const ul = container.querySelector('#recipe-ingredients');
    if (ul) {
      Array.from(ul.children).forEach(li => {
        const parts = li.textContent.split(' ');
        const num = parseFloat(parts[0]);
        if (!isNaN(num)) {
          const newNum = +(num * scale).toFixed(3);
          parts[0] = newNum;
          li.textContent = parts.join(' ');
        }
      });
    }
    // Update servings input
    const sin = container.querySelector('#servings-input'); if (sin) sin.value = newServings;
  }

  window.RecipeRenderer = { renderRecipe, fetchAndRenderScaled };
})(window);
