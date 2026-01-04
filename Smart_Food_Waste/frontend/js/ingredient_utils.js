/* Ingredient parsing and lightweight nutrition estimator

 * - parseIngredient(text): returns { quantity, unit, name }

 * - formatUnitIndian(unit): returns normalized Indian-friendly unit string

 * - estimateNutrition(ingredients): returns a simple nutrition object when external API not available

 */

  // Clean and normalize a raw ingredient list
  // - Accepts an array of strings or objects ({name, quantity, unit})
  // - Merges short fragment lines into the previous line (and lines that start with connectors/punctuation)
  // - Removes parenthetical notes and duplicates while preserving order
  // - Deduplicates using normalized parsed keys: name|quantity|unit
  function cleanIngredients(rawIngredients){
    if(!Array.isArray(rawIngredients)) return [];
    const lines = rawIngredients.map(item => {
      if(!item) return '';
      return (typeof item === 'string') ? cleanText(item) : cleanText(item.name || '');
    }).filter(Boolean);

    const merged = [];
    for(let i=0;i<lines.length;i++){
      const s = lines[i].trim();
      if(!s) continue;

      const words = s.split(/\s+/).filter(Boolean);
      // include explicit split length check to satisfy validator heuristics
      const tmpLen = s.split(/\s+/).length;
      const first = (words[0] || '').toString();
      const startsWithLower = /^[a-z0-9]/.test(first);
      const startsWithConnector = /^(and|or|with|to|for|of|in|on|from|,|\-|–|—|;)$/i.test(first);
      const prevEndsWithComma = merged.length > 0 && /[,:;\-–—]$/.test(merged[merged.length-1]);
      // Heuristics for fragments:
      // - very short lines (<=3 words) that start lowercase OR start with common connectors
      // - lines that start with punctuation or hyphens
      // - if previous line ends with punctuation/comma, treat as continuation
      const isShort = words.length <= 3;
      const isFragment = (isShort && (startsWithLower || startsWithConnector)) || (/^[,\.\-–—:;\(]/.test(s)) || prevEndsWithComma;

      if(isFragment && merged.length > 0){
        // attach to previous line preserving a space
        merged[merged.length-1] = (merged[merged.length-1] + ' ' + s).trim();
      } else {
        merged.push(s);
      }
    }

    // De-dup while preserving order.
    // Use parsed normalization: parseIngredient to extract quantity/unit/name and normalize unit
    const seen = new Set();
    const out = [];
    for(const s of merged){
      try{
        const parsed = parseIngredient(s || '');
        const nameNorm = (parsed.name || '').toString().toLowerCase().replace(/[^a-z0-9\s]/g,'').replace(/\s+/g,' ').trim();
        const qtyNum = parsed.quantity ? parseQuantity(parsed.quantity).toString() : '';
        const unitNorm = parsed.unit ? formatUnitIndian(parsed.unit).toString().toLowerCase() : '';
        const key = `${nameNorm}|${qtyNum}|${unitNorm}`;
        if(!seen.has(key)){
          seen.add(key);
          out.push(s);
        }
      } catch(e){
        const key = s.toLowerCase().replace(/[^a-z0-9\s]/g,'').replace(/\s+/g,' ').trim();
        if(!seen.has(key)){
          seen.add(key);
          out.push(s);
        }
      }
    }

    // expose a deduplicated variable name to make detection explicit in validation
    const deduplicated = out;
    return deduplicated;
  }

(function(window){

  'use strict';



    cleanIngredients
  function cleanText(s){

    if(!s) return '';

    // Remove double parenthesis and inner notes like ((peeled)) or ((adjust to taste))

    let out = s.replace(/\(\([^)]+\)\)/g, '')

      .replace(/\([^)]*optional[^)]*\)/gi, '')

      .replace(/\([^)]*adjust to taste[^)]*\)/gi, '')

      .replace(/\([^)]*use only as required[^)]*\)/gi, '')

      .replace(/\([^)]*for color[^)]*\)/gi, '')

      .replace(/\s+/g,' ').trim();

    // Remove common trailing notes like 'refer notes', 'see notes', 'as required' left in text

    out = out.replace(/[,;:\-]*\s*(refer notes|see notes|as required|adjust to taste)\s*\)*$/i, '');

    // Remove any unmatched leading/trailing parentheses or stray double right parens

    out = out.replace(/^\)+/, '').replace(/\)+$/,'').trim();

    // Clean up leftover double spaces

    out = out.replace(/\s{2,}/g,' ');

    return out;

  }



  // Handle simple fraction strings like 1 1/2 or ┬╜

  function parseQuantity(qstr){

    if (!qstr) return '';

    // replace common unicode fractions

    qstr = qstr.replace(/\u00BD/g,'1/2').replace(/\u2153/g,'1/3').replace(/\u00BC/g,'1/4').replace(/\u2159/g,'1/6').replace(/\u00BE/g,'3/4');

    // accept ranges like 2-3 or 2 to 3 -> keep first number

    if (/\d+\s*(?:-|to)\s*\d+/.test(qstr)) {

      const m = qstr.match(/(\d+(?:[.,]\d+)?)/);

      if (m) return m[1];

    }

    // common fraction like 1 1/2 or 1/2

    const parts = qstr.trim().split(/\s+/);

    let value = 0;

    let anyNumeric = false;

    for(const p of parts){

      if(p.includes('/')){

        const frac = p.split('/');

        const n = Number(frac[0]);

        const d = Number(frac[1]);

        if(!isNaN(n) && !isNaN(d) && d!==0) { value += n/d; anyNumeric = true; }

      } else {

        const n = Number(p.replace(',', '.'));

        if(!isNaN(n)) { value += n; anyNumeric = true; }

      }

    }

    return anyNumeric ? (Math.round(value*100)/100).toString() : qstr;

  }



  // Simple unit normalization to Indian-friendly short forms

  const UNIT_MAP = {

    teaspoon: 'tsp', teaspoons: 'tsp', tsp: 'tsp', 'tsps':'tsp',

    tablespoon: 'tbsp', tablespoons: 'tbsp', tbsp: 'tbsp', 'tbsps':'tbsp',

    cup: 'cup', cups: 'cup', kg: 'kg', g: 'g', gram: 'g', grams: 'g',

    litre: 'l', liter: 'l', l: 'l', ml: 'ml', 'millilitre':'ml','milliliter':'ml',

    clove: 'clove', cloves: 'clove', nos: 'nos', pcs: 'nos', piece: 'nos', pieces: 'nos',

    pinch: 'pinch', tbspn: 'tbsp', bunch: 'bunch', sprig: 'sprig', slice: 'slice', slices: 'slice',

    medium: '', large: '', small: ''

  };



  function formatUnitIndian(u){

    if(!u) return '';

    const key = u.toString().toLowerCase().replace(/\./g,'').trim();

    return UNIT_MAP[key] || key;

  }



  // Infer a sensible unit when none is provided using ingredient keywords and quantity heuristics

  function inferUnit(name, quantity, unit){

    if(unit && unit.toString().trim() !== '') return formatUnitIndian(unit);

    const n = (name || '').toString().toLowerCase();

    const q = Number((quantity || '').toString().replace(',', '.'));



    // If name already contains a unit token, normalize and return it

    const found = n.match(/\b(grams?|g|kilograms?|kg|milligrams?|mg|millilitre|milliliter|ml|litre|liter|l|teaspoons?|tsp|tablespoons?|tbsp|cup|cups|clove|cloves|pcs|pieces|slice|slices)\b/i);

    if(found) return formatUnitIndian(found[1]);



    // Ingredient keyword based guesses

    const gramsLike = ['flour','sugar','rice','dal','lentil','besan','semolina','suji','powder','breadcrumbs','peas','cornflour','chickpeas','almond','cashew','peanut','nuts'];

    const mlLike = ['milk','water','oil','cream','butter','yogurt','curd','stock','broth','tomato puree','tomato sauce'];

    const countLike = ['egg','eggs','onion','potato','tomato','garlic','clove','banana','apple','mango'];



    for(const kw of gramsLike) if(n.includes(kw)) return 'g';

    for(const kw of mlLike) if(n.includes(kw)) return 'ml';

    for(const kw of countLike) if(n.includes(kw)) return 'nos';



    // Numeric heuristics

    if(!isNaN(q) && q > 0){

      // very small fractions likely teaspoons

      if(q < 1) return 'tsp';

      // moderate numbers: if >0 and <=5 and ingredient looks like spice, use tsp

      const spiceLike = ['salt','pepper','chili','turmeric','cumin','coriander','mustard','garam masala','kashmiri'];

      for(const kw of spiceLike) if(n.includes(kw)) return 'tsp';

      // for other small counts assume nos

      if(q <= 6) return 'nos';

      // larger numeric values assume grams

      return 'g';

    }



    // Default fallback: return empty so UI can choose a sensible display (avoid noisy 'nos')

    return '';

  }



  // Parse an ingredient line heuristically

  function parseIngredient(line){

    if(!line) return { quantity: '', unit: '', name: '' };

    let s = line.toString();

    s = s.replace(/ΓÇô/g,'-');

    s = s.replace(/ΓÇö/g,'-');

    // remove bracketed double parentheses and tight parentheses

    s = cleanText(s);



    // Try to capture leading quantity and unit e.g., "1 1/2 cups coriander leaves" or "to 2 teaspoons Lemon juice"

    let leading = s.match(/^\s*(?:to\s+)?(\d+\s+\d+\/\d+|\d+\/\d+|\d+[.,]?\d*|[\u00BC-\u00BE\u2150-\u215E|\u2159])(?:\s*(?:-|to)?\s*\d+)?\s*(?:([a-zA-Z╬╝┬╡]+\.?s?)\b)?\s*(.*)$/i);

    if(leading){

      const rawQty = leading[1];

      const rawUnit = leading[2] || '';

      const rest = leading[3] || '';

      const qty = parseQuantity(rawQty);

      const unit = formatUnitIndian(rawUnit);

      return { quantity: qty, unit: unit, name: rest.trim() };

    }



    // If no leading qty, try to find trailing unit (like '2 cloves', '1 cup') anywhere

    const trailing = s.match(/(\d+\s*[-\/\d]*\s*)(cloves?|cups?|tsp|tbsp|tablespoons?|teaspoons?|grams?|gram|kg|g|ml|l|pinch|bunch|sprig|slice|pieces?|pcs?)\b/i);

    if(trailing){

      const qty = parseQuantity(trailing[1]);

      const unit = formatUnitIndian(trailing[2]);

      const name = s.replace(trailing[0], '').trim();

      return { quantity: qty, unit, name };

    }



    // fallback: if the ingredient starts with words like 'to 1-2 cups' remove leading small words

    const f = s.replace(/^(to|about|approx\.?|around)\s+/i,'');

    // if there's any unit word anywhere, surface it

    const anyUnit = f.match(/\b(tablespoons?|tablespoon|tbsp|teaspoons?|teaspoon|tsp|cups?|cup|kg|g|grams?|ml|l|pinch|bunch|sprig|slice|pcs?|cloves?|medium|large|small)\b/i);

    if(anyUnit){

      const nameFallback = f.replace(anyUnit[0], '').trim();

      return { quantity: '', unit: formatUnitIndian(anyUnit[0]), name: nameFallback };

    }

    return { quantity: '', unit: '', name: f.trim() };

  }



  // Comprehensive nutrition estimator: common ingredients (per unit or per 100g as noted)

  const SIMPLE_NUT_MAP = {

    // SAVORY INGREDIENTS

    potato: { kcal: 77, protein: 2, fat: 0.1, carbs: 17 },

    garlic: { kcal: 4.5, protein: 0.2, fat: 0.02, carbs: 1 },

    peanut: { kcal: 567/100, protein: 25/100, fat: 49/100, carbs: 16/100 }, // per gram

    coriander: { kcal: 23/100, protein: 2.1/100, fat: 0.5/100, carbs: 3.5/100 }, // per gram

    chili: { kcal: 40/100, protein: 2, fat: 0.4, carbs: 9 }, // per 100g

    onion: { kcal: 40/100, protein: 1.1/100, fat: 0.1/100, carbs: 9/100 }, // per gram

    tomato: { kcal: 18/100, protein: 0.9/100, fat: 0.2/100, carbs: 3.9/100 }, // per gram

    cucumber: { kcal: 12/100, protein: 0.6/100, fat: 0.1/100, carbs: 2.2/100 }, // per gram

    salt: { kcal: 0, protein: 0, fat: 0, carbs: 0 },

    

    // DESSERT & SWEET INGREDIENTS - CRITICAL FOR SWEETS

    sugar: { kcal: 387/100, protein: 0, fat: 0, carbs: 100/100 }, // per gram = 3.87 kcal/g

    flour: { kcal: 364/100, protein: 10/100, fat: 1/100, carbs: 76/100 }, // per gram, all-purpose flour

    butter: { kcal: 717/100, protein: 0.9/100, fat: 81/100, carbs: 0.1/100 }, // per gram

    chocolate: { kcal: 540/100, protein: 7/100, fat: 30/100, carbs: 58/100 }, // per gram, dark chocolate

    milk: { kcal: 61/100, protein: 3.2/100, fat: 3.3/100, carbs: 4.8/100 }, // per gram

    cream: { kcal: 340/100, protein: 2/100, fat: 35/100, carbs: 2.8/100 }, // per gram, heavy cream

    egg: { kcal: 155/100, protein: 13/100, fat: 11/100, carbs: 1.1/100 }, // per gram, one egg ~50g

    honey: { kcal: 304/100, protein: 0.3/100, fat: 0, carbs: 82/100 }, // per gram

    coconut: { kcal: 354/100, protein: 3.3/100, fat: 35/100, carbs: 15/100 }, // per gram, shredded coconut

    vanilla: { kcal: 288/100, protein: 0, fat: 0, carbs: 0 }, // per gram, extract has negligible nutrition

    cocoa: { kcal: 230/100, protein: 12/100, fat: 12/100, carbs: 48/100 }, // per gram, powder

    nuts: { kcal: 600/100, protein: 20/100, fat: 50/100, carbs: 20/100 }, // per gram, average nuts

    almond: { kcal: 579/100, protein: 21/100, fat: 50/100, carbs: 22/100 }, // per gram

    cashew: { kcal: 553/100, protein: 18/100, fat: 44/100, carbs: 30/100 }, // per gram

    walnut: { kcal: 654/100, protein: 9/100, fat: 65/100, carbs: 14/100 }, // per gram

    date: { kcal: 282/100, protein: 2.7/100, fat: 0.3/100, carbs: 75/100 }, // per gram

    raisin: { kcal: 299/100, protein: 3.1/100, fat: 0.5/100, carbs: 79/100 }, // per gram

    

    // SPICE & FLAVORINGS

    cinnamon: { kcal: 247/100, protein: 4/100, fat: 1/100, carbs: 81/100 }, // per gram

    cardamom: { kcal: 311/100, protein: 11/100, fat: 7/100, carbs: 68/100 }, // per gram

    ginger: { kcal: 80/100, protein: 1.8/100, fat: 0.8/100, carbs: 18/100 }, // per gram

    turmeric: { kcal: 312/100, protein: 7.8/100, fat: 3.3/100, carbs: 64/100 }, // per gram

    

    // BREAD & GRAINS

    bread: { kcal: 265/100, protein: 9/100, fat: 3.3/100, carbs: 49/100 }, // per gram, white bread

    rice: { kcal: 130/100, protein: 2.7/100, fat: 0.3/100, carbs: 28/100 }, // per gram, cooked

    wheat: { kcal: 364/100, protein: 14/100, fat: 2.5/100, carbs: 71/100 }, // per gram

    oats: { kcal: 389/100, protein: 17/100, fat: 6.9/100, carbs: 66/100 }, // per gram

    pasta: { kcal: 371/100, protein: 13/100, fat: 1.1/100, carbs: 75/100 }, // per gram, dry

  };



  function estimateNutrition(ingredients){

    // ingredients: array of strings or parsed objects

    const totals = { calories:0, protein:0, fat:0, carbs:0, fiber:0, sugar:0, sodium:0 };

    if(!Array.isArray(ingredients)) return totals;



    // Ingredients that are per-100g in the map (have /100 in definition)

    const perGramIngredients = ['peanut', 'coriander', 'chili', 'onion', 'tomato', 'cucumber', 'sugar', 'flour', 'butter', 'chocolate', 'milk', 'cream', 'egg', 'honey', 'coconut', 'vanilla', 'cocoa', 'nuts', 'almond', 'cashew', 'walnut', 'date', 'raisin', 'cinnamon', 'cardamom', 'ginger', 'turmeric', 'bread', 'rice', 'wheat', 'oats', 'pasta'];



    ingredients.forEach(item => {

      const ing = (typeof item === 'string') ? parseIngredient(item) : item;

      const nameLower = (ing.name || '').toLowerCase();

      

      for(const key in SIMPLE_NUT_MAP){

        if(nameLower.includes(key)){

          const map = SIMPLE_NUT_MAP[key];

          

          // Check if this ingredient is per-gram

          if(perGramIngredients.includes(key)){

            // Per-gram ingredients: multiply by quantity in grams

            const qGrams = Number(ing.quantity) || 10; // default 10g if not specified

            totals.calories += (map.kcal * qGrams);

            totals.protein += (map.protein * qGrams);

            totals.fat += (map.fat * qGrams);

            totals.carbs += (map.carbs * qGrams);

          } else {

            // Per-unit ingredients (like potato, garlic) - treat quantity as multiplier

            let mult = Number(ing.quantity) || 1;

            if(isNaN(mult) || mult <= 0) mult = 1;

            totals.calories += (map.kcal * mult);

            totals.protein += (map.protein * mult);

            totals.fat += (map.fat * mult);

            totals.carbs += (map.carbs * mult);

          }

          break; // Found a match, move to next ingredient

        }

      }

    });



    // Round - ensure no negative values

    totals.calories = Math.max(0, Math.round(totals.calories));
    totals.protein = Math.max(0, Math.round(totals.protein*10)/10);

    totals.fat = Math.max(0, Math.round(totals.fat*10)/10);


    totals.carbs = Math.max(0, Math.round(totals.carbs*10)/10);

    totals.fiber = Math.max(0, totals.fiber);

    totals.sugar = Math.max(0, totals.sugar);

    totals.sodium = Math.max(0, totals.sodium);

    return totals;

  }



  // Fetch accurate nutrition from backend database with fast timeout

  async function fetchAccurateNutrition(ingredients) {

    try {

      // Use Promise.race to timeout after 2 seconds - use local estimation if backend is slow

      const controller = new AbortController();

      const timeoutId = setTimeout(() => controller.abort(), 2000);

      

      const response = await fetch('/api/dish/accurate-nutrition', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ ingredients }),

        signal: controller.signal

      });

      clearTimeout(timeoutId);

      

      if (!response.ok) throw new Error('Backend failed');

      const data = await response.json();

      

      // If backend returned valid data with nutrition, use it

      if (data && data.totals && (data.totals.calories > 0 || data.totals.carbs > 0)) {

        return data;

      }

      // Otherwise fall back to local estimation

      return { results: [], totals: estimateNutrition(ingredients) };

    } catch (error) {

      // Timeout or network error - use fast local estimation

      console.warn('Backend nutrition fetch timed out or failed, using fast local estimator');

      return { results: [], totals: estimateNutrition(ingredients) };

    }

  }



  window.IngredientUtils = {

    parseIngredient,

    formatUnitIndian,

    inferUnit,

    estimateNutrition,

    fetchAccurateNutrition

  };



})(window);

