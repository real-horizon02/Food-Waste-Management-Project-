// pdfUpload.js - handles file input, server upload fallback to client extraction via pdf.js

document.addEventListener('DOMContentLoaded', () => {
  const uploadBtn = document.getElementById('pdf-upload-btn');
  const fileInput = document.getElementById('pdf-upload-input');
  if (!uploadBtn || !fileInput) return;

  uploadBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', handlePdfFile);
});

async function handlePdfFile(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  showLoading('Simmering the PDF…');

  try {
    // try server upload first
    try {
      const res = await dishAPI.extractFromPdf(file);
      if (res && res.recipe) {
        displayRecipeResults(res);
        showSuccess('Recipe extracted from PDF (server).');
        hideLoading();
        return;
      }
    } catch (err) {
      console.warn('server extraction failed, falling back to client parser', err);
    }

    // client-side extraction using PDF.js
    if (window.pdfjsLib) {
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let fullText = '';
      for (let i=1;i<=Math.min(pdf.numPages, 12); i++) {
        const page = await pdf.getPage(i);
        const txt = await page.getTextContent();
        fullText += '\n' + txt.items.map(it => it.str).join(' ');
      }

      // try server text endpoint
      try {
        const res = await dishAPI.extractFromText(fullText);
        if (res && res.recipe) {
          displayRecipeResults(res);
          showSuccess('Recipe extracted from PDF (text upload).');
          hideLoading();
          return;
        }
      } catch (err) {
        console.warn('text endpoint failed', err);
      }

      // fallback: local heuristic parser
      const recipe = parseRecipeFromText(fullText);
      if (recipe) {
        displayRecipeResults({ recipe, dish: { name: recipe.title || 'Extracted Recipe' } });
        showSuccess('Recipe extracted from PDF (client).');
      } else {
        showError('Could not parse recipe from PDF. Try a cleaner recipe PDF or paste a URL.');
      }
    } else {
      showError('pdf.js not available for client extraction.');
    }
  } catch (err) {
    console.error(err);
    showError(err.message || 'PDF processing error');
  } finally {
    hideLoading();
  }
}

// naive text parser
function parseRecipeFromText(text) {
  if (!text || text.length < 30) return null;
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const title = lines.find(l => l.length > 6 && l.length < 80) || 'Untitled';
  const ingIdx = lines.findIndex(l => /ingredient/i.test(l));
  let ingredients = [];
  if (ingIdx >= 0) {
    for (let i = ingIdx+1; i < Math.min(lines.length, ingIdx + 80); i++) {
      const ln = lines[i];
      if (/instruction|method|direction|step/i.test(ln)) break;
      if (/^\d+[\).\s]|^[-•*]/.test(ln) || /\b(tsp|tbsp|cup|g|kg|ml|oz)\b/i.test(ln)) {
        ingredients.push({ name: ln.replace(/^[\d\-\.\)\s]*/, ''), quantity: '', unit: '' });
      }
    }
  }
  const instIdx = lines.findIndex(l => /instruction|method|direction|step/i.test(l));
  const instructions = [];
  if (instIdx >= 0) {
    for (let i = instIdx+1; i < Math.min(lines.length, instIdx + 200); i++) {
      const ln = lines[i];
      if (/^ingredient/i.test(ln)) break;
      if (ln.length > 10) instructions.push(ln);
    }
  }
  if (!ingredients.length && !instructions.length) return null;
  return { title, servings: 1, ingredients, instructions };
}
