/**
 * recipeAI.js
 * - Provides AI normalization for raw recipe text or Spoonacular output.
 * - Implements strict unit normalization and fraction parsing.
 * - Provides a small local nutrition estimator fallback when Spoonacular is unavailable.
 *
 * Notes:
 * - This module uses an LLM (OpenAI by default) when `processWithLLM` is called and
 *   `OPENAI_API_KEY` is set. If missing, a heuristic parser + local estimator is used.
 */

const axios = require('axios');
const fraction = require('fraction.js');

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || process.env.LLM_API_KEY || null;

const unitAliases = {
  tbsp: 'tablespoon',
  tbs: 'tablespoon',
  'tbsp.': 'tablespoon',
  tbsps: 'tablespoon',
  tsp: 'teaspoon',
  'tsp.': 'teaspoon',
  g: 'g',
  gram: 'g',
  grams: 'g',
  kg: 'kg',
  litre: 'l',
  liter: 'l',
  l: 'l',
  ml: 'ml',
  cup: 'cup',
  cups: 'cup',
  ounce: 'oz',
  ounces: 'oz',
  oz: 'oz',
  pound: 'lb',
  lbs: 'lb',
  lb: 'lb',
  pinch: 'pinch',
  clove: 'clove',
  cloves: 'clove'
};

function normalizeUnit(u) {
  if (!u) return '';
  u = String(u).trim().toLowerCase();
  // replace common punctuation
  u = u.replace(/\.$/, '');
  if (unitAliases[u]) return unitAliases[u];
  // plural -> singular naive
  if (u.endsWith('s') && unitAliases[u.slice(0, -1)]) return unitAliases[u.slice(0, -1)];
  return u;
}

function parseQuantity(q) {
  if (q === null || q === undefined || q === '') return null;
  try {
    const s = String(q).trim();
    // Handle forms like "1 1/2", "1-1/2", "1½"
    if (/\d+\s+\d+\/\d+/.test(s) || /\d+\-\d+\/\d+/.test(s)) {
      const cleaned = s.replace('-', ' ').split(/\s+/).slice(0,2).join(' ');
      const parts = cleaned.split(' ');
      if (parts.length === 2) {
        const whole = parseInt(parts[0], 10);
        const frac = new fraction(parts[1]);
        return whole + frac.valueOf();
      }
    }
    // unicode fractions like ½ ¼
    const unicodeMap = { '½': 0.5, '¼': 0.25, '¾': 0.75 };
    if (s.length === 1 && unicodeMap[s]) return unicodeMap[s];
    // plain fraction
    if (/^\d+\/\d+$/.test(s)) return new fraction(s).valueOf();
    // mixed fuzzy numbers
    const n = parseFloat(s.replace(',', '.'));
    if (!isNaN(n)) return n;
  } catch (e) {
    // fallthrough
  }
  return null;
}

// Local nutrition map per 100g (very small fallback set). These are approximate values and
// used only when Spoonacular/remote nutrition isn't available. This is intentionally small.
const LOCAL_NUTR_MAP = {
  'onion': { calories: 40, protein: 1.1, fat: 0.1, carbs: 9.3 },
  'tomato': { calories: 18, protein: 0.9, fat: 0.2, carbs: 3.9 },
  'chicken': { calories: 239, protein: 27, fat: 14, carbs: 0 },
  'rice': { calories: 130, protein: 2.7, fat: 0.3, carbs: 28 },
  'flour': { calories: 364, protein: 10, fat: 1, carbs: 76 },
  'sugar': { calories: 387, protein: 0, fat: 0, carbs: 100 },
  'butter': { calories: 717, protein: 0.9, fat: 81, carbs: 0.1 },
  'salt': { calories: 0, protein: 0, fat: 0, carbs: 0 }
};

function ingredientBaseForName(name) {
  if (!name) return null;
  const key = String(name).toLowerCase().split(',')[0].split(' or ')[0].trim();
  // simple stem match
  for (const k of Object.keys(LOCAL_NUTR_MAP)) {
    if (key.includes(k)) return LOCAL_NUTR_MAP[k];
  }
  return null;
}

function toGrams(quantity, unit) {
  // Very rough conversions for fallback estimator. Units should be normalized before calling.
  if (!quantity) return null;
  unit = normalizeUnit(unit);
  if (unit === 'g') return quantity;
  if (unit === 'kg') return quantity * 1000;
  if (unit === 'mg') return quantity / 1000;
  if (unit === 'l' || unit === 'ml') {
    // assume water-like density ~1g/ml
    if (unit === 'l') return quantity * 1000;
    return quantity;
  }
  if (unit === 'cup') return quantity * 240; // ml ~= grams for many foods approx
  if (unit === 'tablespoon') return quantity * 15;
  if (unit === 'teaspoon') return quantity * 5;
  if (unit === 'oz') return quantity * 28.35;
  if (unit === 'lb') return quantity * 453.592;
  if (unit === 'clove') return quantity * 5; // small
  if (unit === 'pinch') return 0.36;
  // if unknown, return null
  return null;
}

function estimateNutritionFallback(ingredient) {
  // ingredient: { name, quantity, unit }
  const base = ingredientBaseForName(ingredient.name || '');
  const qty = parseQuantity(ingredient.quantity) || 0;
  const grams = toGrams(qty, ingredient.unit || '') || 0;
  if (!base || grams === 0) return { calories: 0, protein: 0, fat: 0, carbs: 0 };
  const factor = grams / 100.0;
  return {
    calories: Math.round((base.calories || 0) * factor),
    protein: +( (base.protein || 0) * factor ).toFixed(2),
    fat: +( (base.fat || 0) * factor ).toFixed(2),
    carbs: +( (base.carbs || 0) * factor ).toFixed(2)
  };
}

async function callLLM(prompt) {
  if (!OPENAI_API_KEY) throw new Error('OPENAI_API_KEY not set');
  // Use OpenAI REST API via axios to avoid dev dependency on SDK here.
  try {
    const resp = await axios.post('https://api.openai.com/v1/chat/completions', {
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.1,
      max_tokens: 1500
    }, {
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` }
    });
    const choice = (resp.data.choices || [])[0];
    return choice?.message?.content || null;
  } catch (e) {
    throw new Error('LLM call failed: ' + (e.response?.data?.error?.message || e.message));
  }
}

function buildAIPrompt(rawText, desiredServings) {
  return `You are a recipe normalization assistant. Input raw recipe text or structured JSON from a site. Return strict JSON with keys: title, servings (number), ingredients (array of {name, quantity, unit}), steps (array of step strings), nutrition (object calories, protein, fat, carbs). Rules:\n- Normalize units: convert tbsp/tbs->tablespoon, tsp->teaspoon, grams->g, kilograms->kg, ml/l->ml/l, oz->oz, lb->lb.\n- Always output numeric quantities as decimals (e.g. 1.5). Convert mixed fractions ("1 1/2") to decimals.\n- Normalize unit spellings to singular lower-case: e.g., "tablespoon", "teaspoon", "g", "kg", "ml", "l", "cup", "oz", "lb".\n- Remove duplicate ingredients and merge quantities where appropriate.\n- Clean ingredient names (lowercase, remove parenthetical notes unless necessary).\n- If nutrition values are missing or suspect, estimate nutrition per serving using ingredient quantities. Use approximate but defensible calculations and include a "nutrition._confidence" score (0-1).\n- Return JSON only (no explanatory text).\n\nRawText:\n${rawText}\n\nReturn JSON now.`;
}

async function processWithLLM(rawText, servings = 1) {
  const prompt = buildAIPrompt(rawText, servings);
  const response = await callLLM(prompt);
  if (!response) throw new Error('Empty LLM response');
  try {
    // Try to find JSON in the response
    const jsonStart = response.indexOf('{');
    const jsonStr = response.slice(jsonStart);
    return JSON.parse(jsonStr);
  } catch (e) {
    throw new Error('Failed to parse LLM JSON: ' + e.message);
  }
}

/**
 * Main exported method: process raw text (from Spoonacular or scraped page)
 * - Attempts LLM normalization if API key exists
 * - Otherwise falls back to heuristic parsing and nutrition estimation
 */
async function processRawRecipe(raw, servings = 1) {
  // raw may be object or string
  const rawText = (typeof raw === 'string') ? raw : JSON.stringify(raw);

  if (OPENAI_API_KEY) {
    try {
      const normalized = await processWithLLM(rawText, servings);
      // Post-process normalized: ensure unit normalization and numeric quantities
      if (Array.isArray(normalized.ingredients)) {
        normalized.ingredients = normalized.ingredients.map(ing => {
          return {
            name: (ing.name || '').trim(),
            quantity: (() => {
              const q = parseQuantity(ing.quantity);
              return q === null ? null : +(+q).toFixed(3);
            })(),
            unit: normalizeUnit(ing.unit || ''),
            nutrition: ing.nutrition || null
          };
        });
      }
      normalized.servings = Number(normalized.servings || servings || 1);

      // If nutrition missing, enrich using fallback estimator per ingredient
      if (!normalized.nutrition || Object.keys(normalized.nutrition).length === 0) {
        let totals = { calories: 0, protein: 0, fat: 0, carbs: 0 };
        for (const ing of (normalized.ingredients || [])) {
          const est = estimateNutritionFallback(ing);
          totals.calories += est.calories || 0;
          totals.protein += est.protein || 0;
          totals.fat += est.fat || 0;
          totals.carbs += est.carbs || 0;
        }
        normalized.nutrition = totals;
        normalized.nutrition._confidence = 0.3; // LLM estimated
      }

      return normalized;
    } catch (e) {
      // fallback to heuristic below
      console.warn('LLM normalization failed, falling back:', e.message);
    }
  }

  // Heuristic fallback parser: try to extract lines with "-" or numbered lists
  const lines = rawText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const title = lines[0] || 'Recipe';
  const ingredients = [];
  const steps = [];
  for (const line of lines.slice(1)) {
    if (/^[-*]\s*/.test(line) || /\d+\./.test(line)) {
      // naive split
      if (/ingredient/i.test(line) || /\d+\s*(g|kg|cup|tablespoon|tsp|tbsp|oz|lb)/i) {
        // ingredient-like
        const parts = line.replace(/^[-*\d\.\s]*/, '').split(',');
        const name = parts[0];
        const qtyMatch = name.match(/^(\d+\/?\d*\s*\d*\/?\d*)\s*(.*)/);
        let qty = null, unit = '';
        if (qtyMatch) {
          qty = parseQuantity(qtyMatch[1]);
          unit = normalizeUnit(qtyMatch[2] || '');
        }
        ingredients.push({ name: (name || '').replace(/^[\d\-\.\s]*/, ''), quantity: qty, unit });
      } else {
        steps.push(line.replace(/^[-*\d\.\s]*/, ''));
      }
    }
  }

  // Build nutrition totals from fallback estimator
  let totals = { calories: 0, protein: 0, fat: 0, carbs: 0 };
  for (const ing of ingredients) {
    const est = estimateNutritionFallback(ing);
    totals.calories += est.calories || 0;
    totals.protein += est.protein || 0;
    totals.fat += est.fat || 0;
    totals.carbs += est.carbs || 0;
  }

  return {
    title,
    servings: servings || 1,
    ingredients,
    steps,
    nutrition: { ...totals, _confidence: 0.15 }
  };
}

module.exports = {
  processRawRecipe,
  normalizeUnit,
  parseQuantity,
  estimateNutritionFallback,
  // Parse a calorie chart (text extracted from uploaded PDF/image OCR or raw text)
  // Returns an object like { caloriesPerServing: 200, totalCalories: 800, macros: { protein: X, fat: Y, carbs: Z }, confidence: 0.0 }
  parseCalorieChart: async function(rawChartText) {
    if (!rawChartText) return null;
    // Prefer LLM if available
    if (OPENAI_API_KEY) {
      try {
        const prompt = `You are a nutrition parser. Given raw text extracted from a calorie chart or menu, return strict JSON with keys: total_calories, calories_per_serving (if available), servings (if available), macros {protein, fat, carbs} (numbers). If values are estimates, include a confidence score 0-1. Return JSON only.` + "\n\nText:\n" + rawChartText;
        const resp = await callLLM(prompt);
        const start = resp.indexOf('{');
        const json = JSON.parse(resp.slice(start));
        return { ...json, confidence: json.confidence || 0.7 };
      } catch (e) {
        console.warn('LLM parseCalorieChart failed:', e.message);
      }
    }

    // Fallback heuristic parsing: look for lines like "Calories: 200" or table rows
    const lines = String(rawChartText).split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const out = { total_calories: null, calories_per_serving: null, servings: null, macros: {}, confidence: 0.2 };
    for (const line of lines) {
      const kcal = /calories?[:\s]*([0-9]{2,5})/i.exec(line);
      if (kcal && !out.total_calories) out.total_calories = Number(kcal[1]);
      const perServing = /per\s*serving[:\s]*([0-9]{2,5})/i.exec(line);
      if (perServing && !out.calories_per_serving) out.calories_per_serving = Number(perServing[1]);
      const servings = /servings?[:\s]*([0-9]+)/i.exec(line);
      if (servings && !out.servings) out.servings = Number(servings[1]);
      const protein = /protein[:\s]*([0-9]{1,3}(?:\.[0-9]+)?)/i.exec(line);
      if (protein && !out.macros.protein) out.macros.protein = Number(protein[1]);
      const fat = /fat[:\s]*([0-9]{1,3}(?:\.[0-9]+)?)/i.exec(line);
      if (fat && !out.macros.fat) out.macros.fat = Number(fat[1]);
      const carbs = /carb(?:s)?[:\s]*([0-9]{1,3}(?:\.[0-9]+)?)/i.exec(line);
      if (carbs && !out.macros.carbs) out.macros.carbs = Number(carbs[1]);
    }
    // If we have total calories and servings, compute per-serving
    if (!out.calories_per_serving && out.total_calories && out.servings) {
      out.calories_per_serving = Math.round(out.total_calories / out.servings);
    }
    return out;
  }
};
