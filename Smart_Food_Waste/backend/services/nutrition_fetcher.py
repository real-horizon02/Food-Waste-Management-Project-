"""
Comprehensive nutrition data fetcher - ensures EVERY recipe has nutrition data
Tries multiple sources: Spoonacular API, Internal Database, Ingredient-based estimation
"""

import requests
import json
import re
import os
from functools import lru_cache

# Try to import nutrition database
try:
    from nutrition_db import get_ingredient_nutrition, INGREDIENT_DB
except ImportError:
    try:
        from backend.nutrition_db import get_ingredient_nutrition, INGREDIENT_DB
    except ImportError:
        get_ingredient_nutrition = None
        INGREDIENT_DB = {}


class NutritionFetcher:
    """Fetches nutrition data from multiple sources"""
    
    def __init__(self):
        # Get Spoonacular API key
        try:
            from config import Config
            self.spoonacular_key = Config.SPOONACULAR_API_KEY
            # Edamam API credentials (optional)
            self.edamam_id = getattr(Config, 'EDAMAM_APP_ID', '')
            self.edamam_key = getattr(Config, 'EDAMAM_APP_KEY', '')
            # Google Custom Search (optional) - prefer API over scraping
            self.google_api_key = getattr(Config, 'GOOGLE_SEARCH_API_KEY', '')
            self.google_cx = getattr(Config, 'GOOGLE_SEARCH_ENGINE_ID', '')
        except:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            self.spoonacular_key = os.getenv('SPOONACULAR_API_KEY', '')
            self.edamam_id = os.getenv('EDAMAM_APP_ID', '')
            self.edamam_key = os.getenv('EDAMAM_APP_KEY', '')
            self.google_api_key = os.getenv('GOOGLE_SEARCH_API_KEY', '')
            self.google_cx = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')
        
        # Cache for nutrition data
        self._nutrition_cache = {}
    
    def _is_zero_nutrition(self, nutrition: dict) -> bool:
        """Check if nutrition data is all zeros (should not be cached)"""
        if not nutrition:
            return True
        return all(v == 0 for v in nutrition.values())
    
    def get_nutrition(self, dish_name, ingredients=None, servings=1):
        """
        Get nutrition data for a dish from best available source - OPTIMIZED FOR SPEED
        
        Args:
            dish_name: Name of the dish
            ingredients: List of ingredient dicts with 'name', 'quantity', 'unit'
            servings: Number of servings (default 1)
        
        Returns:
            Dict with nutrition data {calories, protein, fat, carbs, fiber, sugar, sodium}
            NEVER returns None - always has data
        """
        
        # 1. Check cache first (FASTEST)
        cache_key = f"{dish_name.lower()}_{servings}"
        if cache_key in self._nutrition_cache:
            return self._nutrition_cache[cache_key]
        
        nutrition = None
        attempts = []
        
        # 2. Try internal database lookup FIRST (fastest, most reliable for common dishes)
        attempts.append('database')
        nutrition = self._lookup_in_database(dish_name)
        if nutrition and not self._is_zero_nutrition(nutrition):
            nutrition = self._adjust_for_servings(nutrition, servings)
            try:
                nutrition['source'] = 'database'
                nutrition['_attempts'] = attempts
            except Exception:
                pass
            self._nutrition_cache[cache_key] = nutrition
            return nutrition
        
        # 3. Estimate from ingredients immediately (fast & accurate for any combo)
        if ingredients:
            attempts.append('ingredient_estimate')
            nutrition = self._estimate_from_ingredients(ingredients)
            if not self._is_zero_nutrition(nutrition):
                nutrition = self._adjust_for_servings(nutrition, servings)
                try:
                    nutrition['source'] = 'ingredient_estimate'
                    nutrition['_attempts'] = attempts
                except Exception:
                    pass
                self._nutrition_cache[cache_key] = nutrition
                return nutrition
        
        # 4. Try Spoonacular API (searches web for real recipes) - with timeout
        if self.spoonacular_key:
            attempts.append('spoonacular')
            try:
                sp = self._fetch_from_spoonacular_nutrition(dish_name, servings)
                if sp and not self._is_zero_nutrition(sp):
                    sp = self._adjust_for_servings(sp, servings)
                    try:
                        sp['source'] = 'spoonacular'
                        sp['_attempts'] = attempts
                    except Exception:
                        pass
                    self._nutrition_cache[cache_key] = sp
                    return sp
            except Exception:
                pass
        # 5. Try Edamam (if credentials available)
        if ingredients and getattr(self, 'edamam_id', '') and getattr(self, 'edamam_key', ''):
            attempts.append('edamam')
            try:
                ed_nut = self._fetch_from_edamam_nutrition(ingredients, servings)
                if ed_nut and not self._is_zero_nutrition(ed_nut):
                    try:
                        ed_nut['source'] = 'edamam'
                        ed_nut['_attempts'] = attempts
                    except Exception:
                        pass
                    self._nutrition_cache[cache_key] = ed_nut
                    return ed_nut
            except Exception:
                pass

        # 6. FALLBACK: Return default reasonable estimates for any dish
        attempts.append('default')
        nutrition = self._get_default_nutrition(dish_name)
        nutrition = self._adjust_for_servings(nutrition, servings)
        try:
            nutrition['source'] = 'default_estimate'
            nutrition['_attempts'] = attempts
        except Exception:
            pass
        self._nutrition_cache[cache_key] = nutrition
        
        return nutrition
    
    def _fetch_from_spoonacular_nutrition(self, dish_name, servings=1):
        """Fetch nutrition data from Spoonacular API - with fast timeout"""
        try:
            # First search for recipe ID - 3 second timeout
            search_url = "https://api.spoonacular.com/recipes/complexSearch"
            search_params = {
                'query': dish_name,
                'number': 1,
                'apiKey': self.spoonacular_key
            }
            
            response = requests.get(search_url, params=search_params, timeout=3)
            if response.status_code != 200:
                return None
            
            data = response.json()
            results = data.get('results', [])
            if not results:
                return None
            
            recipe_id = results[0]['id']
            
            # Now get nutrition information for that recipe - 3 second timeout
            nutrition_url = f"https://api.spoonacular.com/recipes/{recipe_id}/nutritionWidget.json"
            nutrition_params = {'apiKey': self.spoonacular_key}
            
            response = requests.get(nutrition_url, params=nutrition_params, timeout=3)
            if response.status_code != 200:
                return None
            
            nutrition_data = response.json()
            
            # Extract nutrition per serving
            nutrients = nutrition_data.get('nutrients', [])
            nutrition = {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbs': 0,
                'fiber': 0,
                'sugar': 0,
                'sodium': 0
            }

            return nutrition if nutrition['calories'] > 0 else None
            
        except Exception as e:
            print(f"[NutritionFetcher] Error fetching from Spoonacular: {e}")
            return None
    
    def _extract_nutrition_from_web(self, dish_name):
        """Extract nutrition data from web search using multiple patterns"""
        try:
            # Build query
            search_query = f"{dish_name} nutrition facts per serving"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # If Google Custom Search API credentials are present, use API to get reliable result URLs
            search_results_html = None
            candidate_urls = []
            if getattr(self, 'google_api_key', '') and getattr(self, 'google_cx', ''):
                try:
                    api_url = 'https://www.googleapis.com/customsearch/v1'
                    params = {
                        'q': search_query,
                        'key': self.google_api_key,
                        'cx': self.google_cx,
                        'num': 5
                    }
                    resp = requests.get(api_url, params=params, timeout=6)
                    if resp.status_code == 200:
                        j = resp.json()
                        items = j.get('items', [])
                        for it in items:
                            link = it.get('link')
                            if link:
                                candidate_urls.append(link)
                except Exception:
                    # fall back to simple scraping approach below
                    candidate_urls = []
            else:
                candidate_urls = []

            # If API didn't give URLs, fall back to hitting google.com search page (best-effort)
            if not candidate_urls:
                search_url = "https://www.google.com/search"
                params = {'q': search_query}
                response = requests.get(search_url, params=params, headers=headers, timeout=5)
                if response.status_code != 200:
                    return None
                search_results_html = response.text
            
            # If we got the search results page HTML, try to parse it first
            if search_results_html:
                nutrition = self._parse_nutrition_from_html(search_results_html, dish_name)
                if nutrition:
                    return nutrition
                # extract some candidate urls from HTML if not using API
                if not candidate_urls:
                    candidate_urls = re.findall(r"https?://[^\"'>\s]+", search_results_html)
            
            # If not found directly on search page, try candidate URLs (from API or extracted from HTML)
            if candidate_urls:
                seen = set()
                candidates = []
                for u in candidate_urls:
                    if not u or 'google.' in u or 'youtube.com' in u:
                        continue
                    if u in seen:
                        continue
                    seen.add(u)
                    candidates.append(u)
                    if len(candidates) >= 8:
                        break

                for target in candidates:
                    try:
                        r2 = requests.get(target, headers=headers, timeout=6)
                        if r2.status_code == 200:
                            nut = self._parse_nutrition_from_html(r2.text, dish_name)
                            if nut:
                                return nut
                    except Exception:
                        continue
            
            return None
            
        except Exception as e:
            print(f"[NutritionFetcher] Error extracting nutrition from web: {e}")
            return None

    def _fetch_from_edamam_nutrition(self, ingredients, servings=1):
        """Fetch nutrition using Edamam Nutrition Analysis API

        ingredients: list of ingredient strings or dicts (will be normalized)
        """
        try:
            # Normalize ingredients to strings
            ingr_list = []
            for ing in ingredients:
                if isinstance(ing, str):
                    ingr_list.append(ing)
                elif isinstance(ing, dict):
                    name = ing.get('name') or ''
                    qty = ing.get('quantity') or ''
                    unit = ing.get('unit') or ''
                    if name:
                        if qty:
                            ingr_list.append(f"{qty} {unit} {name}".strip())
                        else:
                            ingr_list.append(name)
            if not ingr_list:
                return None

            ed_url = f'https://api.edamam.com/api/nutrition-details?app_id={self.edamam_id}&app_key={self.edamam_key}'
            payload = {'title': 'Recipe nutrition analysis', 'ingr': ingr_list}
            resp = requests.post(ed_url, json=payload, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            # Parse totalNutrients similarly to the route implementation
            nutrition = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0}
            try:
                tn = data.get('totalNutrients', {})
                def grab(k):
                    v = tn.get(k, {})
                    return v.get('quantity') if isinstance(v, dict) else None

                nutrition['calories'] = data.get('calories') or nutrition['calories']
                nutrition['protein'] = grab('PROCNT') or grab('protein') or nutrition['protein']
                nutrition['fat'] = grab('FAT') or nutrition['fat']
                nutrition['carbs'] = grab('CHOCDF') or grab('carbs') or nutrition['carbs']
                nutrition['fiber'] = grab('FIBTG') or nutrition['fiber']
                nutrition['sodium'] = grab('NA') or nutrition['sodium']
            except Exception:
                pass

            # Round values
            for k in ['calories','protein','fat','carbs','fiber']:
                try:
                    nutrition[k] = round(float(nutrition.get(k, 0) or 0), 1)
                except Exception:
                    nutrition[k] = nutrition.get(k, 0)
            try:
                nutrition['sodium'] = int(round(float(nutrition.get('sodium', 0) or 0)) )
            except Exception:
                nutrition['sodium'] = int(nutrition.get('sodium', 0) or 0)

            return nutrition if nutrition['calories'] and nutrition['calories'] > 0 else None
        except Exception as e:
            print(f"[NutritionFetcher] Error fetching from Edamam: {e}")
            return None
    
    def _parse_nutrition_from_html(self, html, dish_name):
        """Parse nutrition facts from HTML content"""
        try:
            # First, try to extract JSON-LD (schema.org) NutritionInformation or Recipe blocks
            try:
                ld_json_blocks = re.findall(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL)
                for block in ld_json_blocks:
                    try:
                        data = json.loads(block.strip())
                    except Exception:
                        # sometimes multiple JSON objects are concatenated; try to recover
                        try:
                            data = json.loads(block.strip().split('\n',1)[-1])
                        except Exception:
                            continue

                    # Normalize to list for easier traversal
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        # If it's a Recipe with a nutrition property
                        if isinstance(item, dict):
                            # direct NutritionInformation
                            if item.get('@type', '').lower() == 'nutritioninformation' or item.get('type', '').lower() == 'nutritioninformation':
                                nut = item
                            else:
                                nut = item.get('nutrition') if isinstance(item.get('nutrition'), dict) else None

                            if nut and isinstance(nut, dict):
                                # parse values if present
                                def _num(v):
                                    try:
                                        if isinstance(v, str):
                                            m = re.search(r"(\d+(?:\.\d+)?)", v)
                                            return float(m.group(1)) if m else None
                                        return float(v)
                                    except Exception:
                                        return None

                                nutrition = {
                                    'calories': 0,
                                    'protein': 0,
                                    'fat': 0,
                                    'carbs': 0,
                                    'fiber': 0,
                                    'sugar': 0,
                                    'sodium': 0
                                }

                                # Common JSON-LD property names
                                cal = nut.get('calories') or nut.get('caloriesContent') or nut.get('caloriesPerServing')
                                prot = nut.get('proteinContent') or nut.get('protein')
                                fatv = nut.get('fatContent') or nut.get('fat')
                                carbsv = nut.get('carbohydrateContent') or nut.get('carbohydrates') or nut.get('carbs')
                                fib = nut.get('fiberContent') or nut.get('dietaryFiber')
                                sug = nut.get('sugarContent') or nut.get('sugars')
                                sod = nut.get('sodiumContent') or nut.get('sodium')

                                if cal:
                                    n = _num(cal)
                                    if n is not None:
                                        nutrition['calories'] = round(n,1)
                                if prot:
                                    n = _num(prot)
                                    if n is not None:
                                        nutrition['protein'] = round(n,1)
                                if fatv:
                                    n = _num(fatv)
                                    if n is not None:
                                        nutrition['fat'] = round(n,1)
                                if carbsv:
                                    n = _num(carbsv)
                                    if n is not None:
                                        nutrition['carbs'] = round(n,1)
                                if fib:
                                    n = _num(fib)
                                    if n is not None:
                                        nutrition['fiber'] = round(n,1)
                                if sug:
                                    n = _num(sug)
                                    if n is not None:
                                        nutrition['sugar'] = round(n,1)
                                if sod:
                                    n = _num(sod)
                                    if n is not None:
                                        nutrition['sodium'] = int(round(n))

                                if nutrition['calories'] > 0:
                                    return nutrition
            except Exception:
                # Don't let JSON-LD parsing break regex fallback
                pass

            # Regex patterns to find nutrition data
            calorie_pattern = r'(?:calories?|energy)[\s:]*(\d+(?:\.\d+)?)\s*(?:kcal|cal|kilocalories?)?'
            protein_pattern = r'protein[\s:]*(\d+(?:\.\d+)?)\s*(?:g|gram|grams)?'
            fat_pattern = r'(?:total\s+)?fat[\s:]*(\d+(?:\.\d+)?)\s*(?:g|gram|grams)?'
            carbs_pattern = r'(?:carbohydrate|carbs?)[\s:]*(\d+(?:\.\d+)?)\s*(?:g|gram|grams)?'
            fiber_pattern = r'(?:dietary\s+)?fiber[\s:]*(\d+(?:\.\d+)?)\s*(?:g|gram|grams)?'
            sugar_pattern = r'(?:sugars?|sugar content)[\s:]*(\d+(?:\.\d+)?)\s*(?:g|gram|grams)?'
            sodium_pattern = r'sodium[\s:]*(\d+(?:\.\d+)?)\s*(?:mg|milligram)?'
            
            nutrition = {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbs': 0,
                'fiber': 0,
                'sugar': 0,
                'sodium': 0
            }
            
            # Try to find each nutrient
            cal_match = re.search(calorie_pattern, html, re.IGNORECASE)
            if cal_match:
                nutrition['calories'] = round(float(cal_match.group(1)), 1)
            
            protein_match = re.search(protein_pattern, html, re.IGNORECASE)
            if protein_match:
                nutrition['protein'] = round(float(protein_match.group(1)), 1)
            
            fat_match = re.search(fat_pattern, html, re.IGNORECASE)
            if fat_match:
                nutrition['fat'] = round(float(fat_match.group(1)), 1)
            
            carbs_match = re.search(carbs_pattern, html, re.IGNORECASE)
            if carbs_match:
                nutrition['carbs'] = round(float(carbs_match.group(1)), 1)
            
            fiber_match = re.search(fiber_pattern, html, re.IGNORECASE)
            if fiber_match:
                nutrition['fiber'] = round(float(fiber_match.group(1)), 1)
            
            sugar_match = re.search(sugar_pattern, html, re.IGNORECASE)
            if sugar_match:
                nutrition['sugar'] = round(float(sugar_match.group(1)), 1)
            
            sodium_match = re.search(sodium_pattern, html, re.IGNORECASE)
            if sodium_match:
                nutrition['sodium'] = int(round(float(sodium_match.group(1))))
            
            # Return only if we found at least calories
            if nutrition['calories'] > 0:
                return nutrition
            
            return None
            
        except Exception as e:
            print(f"[NutritionFetcher] Error parsing HTML for nutrition: {e}")
            return None
    
    def _lookup_in_database(self, dish_name):
        """Look up dish in our internal nutrition database"""
        # Comprehensive dish database with typical nutrition per serving
        dish_db = {
            # CURRIES & INDIAN DISHES
            'biryani': {'calories': 450, 'protein': 15, 'fat': 18, 'carbs': 55, 'fiber': 1, 'sugar': 2, 'sodium': 780},
            'butter chicken': {'calories': 420, 'protein': 30, 'fat': 22, 'carbs': 18, 'fiber': 1, 'sugar': 3, 'sodium': 850},
            'paneer tikka': {'calories': 280, 'protein': 18, 'fat': 16, 'carbs': 8, 'fiber': 1, 'sugar': 1, 'sodium': 650},
            'dal makhani': {'calories': 320, 'protein': 12, 'fat': 14, 'carbs': 35, 'fiber': 6, 'sugar': 2, 'sodium': 720},
            'tandoori chicken': {'calories': 200, 'protein': 28, 'fat': 8, 'carbs': 3, 'fiber': 0, 'sugar': 1, 'sodium': 520},
            'samosa': {'calories': 310, 'protein': 6, 'fat': 16, 'carbs': 36, 'fiber': 2, 'sugar': 1, 'sodium': 380},
            'naan': {'calories': 262, 'protein': 9, 'fat': 5.5, 'carbs': 43, 'fiber': 1.4, 'sugar': 1, 'sodium': 500},
            'roti': {'calories': 264, 'protein': 9, 'fat': 1.5, 'carbs': 48, 'fiber': 7, 'sugar': 0.5, 'sodium': 400},
            'dal': {'calories': 230, 'protein': 16, 'fat': 2, 'carbs': 40, 'fiber': 12, 'sugar': 1, 'sodium': 450},
            'chole bhature': {'calories': 450, 'protein': 14, 'fat': 18, 'carbs': 58, 'fiber': 8, 'sugar': 2, 'sodium': 680},
            'aloo gobi': {'calories': 180, 'protein': 5, 'fat': 8, 'carbs': 24, 'fiber': 4, 'sugar': 3, 'sodium': 420},
            'chana masala': {'calories': 280, 'protein': 11, 'fat': 10, 'carbs': 38, 'fiber': 10, 'sugar': 4, 'sodium': 650},
            'dal tadka': {'calories': 240, 'protein': 17, 'fat': 3, 'carbs': 38, 'fiber': 10, 'sugar': 2, 'sodium': 480},
            'pulao': {'calories': 380, 'protein': 8, 'fat': 12, 'carbs': 58, 'fiber': 2, 'sugar': 1, 'sodium': 620},
            
            # DESSERTS & SWEETS
            'kheer': {'calories': 320, 'protein': 8, 'fat': 12, 'carbs': 48, 'fiber': 0, 'sugar': 38, 'sodium': 180},
            'gulab jamun': {'calories': 180, 'protein': 2, 'fat': 8, 'carbs': 26, 'fiber': 0, 'sugar': 22, 'sodium': 80},
            'jalebi': {'calories': 150, 'protein': 1, 'fat': 5, 'carbs': 26, 'fiber': 0, 'sugar': 24, 'sodium': 60},
            'barfi': {'calories': 200, 'protein': 4, 'fat': 10, 'carbs': 26, 'fiber': 1, 'sugar': 20, 'sodium': 120},
            'rasgulla': {'calories': 130, 'protein': 3, 'fat': 0.5, 'carbs': 28, 'fiber': 0, 'sugar': 26, 'sodium': 100},
            'halwa': {'calories': 350, 'protein': 5, 'fat': 18, 'carbs': 44, 'fiber': 2, 'sugar': 35, 'sodium': 150},
            'laddu': {'calories': 220, 'protein': 4, 'fat': 12, 'carbs': 28, 'fiber': 1, 'sugar': 22, 'sodium': 100},
            'payasam': {'calories': 280, 'protein': 4, 'fat': 10, 'carbs': 42, 'fiber': 1, 'sugar': 36, 'sodium': 140},
            'pudding': {'calories': 250, 'protein': 6, 'fat': 8, 'carbs': 38, 'fiber': 0, 'sugar': 32, 'sodium': 120},
            'brownie': {'calories': 240, 'protein': 3, 'fat': 12, 'carbs': 32, 'fiber': 1, 'sugar': 26, 'sodium': 180},
            'cheesecake': {'calories': 350, 'protein': 6, 'fat': 20, 'carbs': 38, 'fiber': 0, 'sugar': 30, 'sodium': 220},
            'ice cream': {'calories': 200, 'protein': 4, 'fat': 10, 'carbs': 24, 'fiber': 0, 'sugar': 22, 'sodium': 80},
            'cake': {'calories': 280, 'protein': 3, 'fat': 12, 'carbs': 40, 'fiber': 1, 'sugar': 32, 'sodium': 280},
            'cookie': {'calories': 150, 'protein': 2, 'fat': 7, 'carbs': 20, 'fiber': 0, 'sugar': 12, 'sodium': 120},
            'chocolate': {'calories': 240, 'protein': 3, 'fat': 14, 'carbs': 26, 'fiber': 2, 'sugar': 23, 'sodium': 15},
            
            # PASTA & RICE DISHES
            'pasta': {'calories': 320, 'protein': 12, 'fat': 10, 'carbs': 48, 'fiber': 2, 'sugar': 2, 'sodium': 350},
            'carbonara': {'calories': 420, 'protein': 18, 'fat': 22, 'carbs': 40, 'fiber': 1, 'sugar': 1, 'sodium': 680},
            'lasagna': {'calories': 380, 'protein': 20, 'fat': 15, 'carbs': 42, 'fiber': 2, 'sugar': 3, 'sodium': 720},
            'pizza': {'calories': 300, 'protein': 12, 'fat': 12, 'carbs': 36, 'fiber': 2, 'sugar': 2, 'sodium': 580},
            'risotto': {'calories': 350, 'protein': 10, 'fat': 12, 'carbs': 48, 'fiber': 1, 'sugar': 2, 'sodium': 620},
            'fried rice': {'calories': 280, 'protein': 9, 'fat': 10, 'carbs': 40, 'fiber': 1, 'sugar': 1, 'sodium': 580},
            
            # SOUPS & BROTHS
            'soup': {'calories': 120, 'protein': 6, 'fat': 4, 'carbs': 14, 'fiber': 2, 'sugar': 2, 'sodium': 480},
            'tomato soup': {'calories': 100, 'protein': 3, 'fat': 3, 'carbs': 16, 'fiber': 2, 'sugar': 4, 'sodium': 520},
            'chicken soup': {'calories': 140, 'protein': 14, 'fat': 5, 'carbs': 8, 'fiber': 1, 'sugar': 1, 'sodium': 620},
            'broth': {'calories': 30, 'protein': 4, 'fat': 1, 'carbs': 1, 'fiber': 0, 'sugar': 0, 'sodium': 820},
            
            # SALADS
            'salad': {'calories': 150, 'protein': 6, 'fat': 10, 'carbs': 12, 'fiber': 3, 'sugar': 3, 'sodium': 280},
            'caesar salad': {'calories': 240, 'protein': 10, 'fat': 16, 'carbs': 14, 'fiber': 2, 'sugar': 1, 'sodium': 520},
            'greek salad': {'calories': 180, 'protein': 8, 'fat': 12, 'carbs': 12, 'fiber': 3, 'sugar': 4, 'sodium': 480},
            
            # SANDWICHES & WRAPS
            'sandwich': {'calories': 350, 'protein': 15, 'fat': 12, 'carbs': 42, 'fiber': 2, 'sugar': 3, 'sodium': 680},
            'burger': {'calories': 450, 'protein': 22, 'fat': 20, 'carbs': 42, 'fiber': 2, 'sugar': 6, 'sodium': 820},
            'wrap': {'calories': 320, 'protein': 12, 'fat': 10, 'carbs': 42, 'fiber': 3, 'sugar': 2, 'sodium': 580},
            
            # BREAKFAST ITEMS
            'omelet': {'calories': 200, 'protein': 16, 'fat': 12, 'carbs': 2, 'fiber': 0, 'sugar': 0, 'sodium': 280},
            'pancake': {'calories': 280, 'protein': 8, 'fat': 10, 'carbs': 40, 'fiber': 1, 'sugar': 12, 'sodium': 480},
            'waffle': {'calories': 300, 'protein': 7, 'fat': 12, 'carbs': 42, 'fiber': 1, 'sugar': 14, 'sodium': 520},
            'toast': {'calories': 200, 'protein': 8, 'fat': 8, 'carbs': 24, 'fiber': 3, 'sugar': 2, 'sodium': 320},
            'cereal': {'calories': 180, 'protein': 4, 'fat': 2, 'carbs': 36, 'fiber': 2, 'sugar': 8, 'sodium': 260},
            
            # MEAT & SEAFOOD
            'steak': {'calories': 350, 'protein': 45, 'fat': 18, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 75},
            'fish': {'calories': 280, 'protein': 32, 'fat': 14, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 80},
            'shrimp': {'calories': 100, 'protein': 20, 'fat': 2, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 180},
            'salmon': {'calories': 300, 'protein': 32, 'fat': 16, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 75},
        }
        
        # Try exact match first
        dish_lower = dish_name.lower().strip()
        if dish_lower in dish_db:
            return dict(dish_db[dish_lower])
        
        # Try partial match
        for db_dish, nutrition in dish_db.items():
            if db_dish in dish_lower or dish_lower in db_dish:
                return dict(nutrition)
        
        return None
    
    def _estimate_from_ingredients(self, ingredients):
        """Estimate nutrition from ingredient list"""
        nutrition = {
            'calories': 0,
            'protein': 0,
            'fat': 0,
            'carbs': 0,
            'fiber': 0,
            'sugar': 0,
            'sodium': 0
        }
        
        if not ingredients:
            return nutrition
        
        for ing in ingredients:
            try:
                if not get_ingredient_nutrition:
                    continue
                
                ing_name = ing.get('name', '')
                quantity = ing.get('quantity', 1)
                unit = ing.get('unit', 'g')
                
                ing_nutrition = get_ingredient_nutrition(ing_name, quantity, unit)
                
                for key in nutrition.keys():
                    nutrition[key] += ing_nutrition.get(key, 0)
            except Exception as e:
                print(f"[NutritionFetcher] Error estimating ingredient {ing}: {e}")
                continue
        
        # Round values
        for key in nutrition.keys():
            if key == 'sodium':
                nutrition[key] = int(round(nutrition[key]))
            else:
                nutrition[key] = round(nutrition[key], 1)
        
        return nutrition
    
    def _adjust_for_servings(self, nutrition, servings):
        """Adjust nutrition data for number of servings"""
        if servings <= 1:
            return nutrition
        
        adjusted = {}
        for key, value in nutrition.items():
            adjusted[key] = round(value / servings, 1) if key != 'sodium' else int(round(value / servings))
        
        return adjusted
    
    def _get_default_nutrition(self, dish_name):
        """Return reasonable default nutrition for any unknown dish"""
        # Categorize by dish name patterns
        dish_lower = dish_name.lower()
        
        # Desserts/sweet items have more sugar and calories
        if any(x in dish_lower for x in ['cake', 'cake', 'dessert', 'sweet', 'candy', 'chocolate', 'brownie', 'pudding', 'ice cream', 'cheesecake', 'cookie', 'biscuit', 'tart', 'pie']):
            return {
                'calories': 280,
                'protein': 3,
                'fat': 12,
                'carbs': 40,
                'fiber': 1,
                'sugar': 32,
                'sodium': 200
            }
        
        # Salads are lighter
        elif any(x in dish_lower for x in ['salad']):
            return {
                'calories': 150,
                'protein': 6,
                'fat': 8,
                'carbs': 14,
                'fiber': 3,
                'sugar': 3,
                'sodium': 300
            }
        
        # Meat/protein dishes
        elif any(x in dish_lower for x in ['steak', 'beef', 'chicken', 'fish', 'salmon', 'shrimp', 'pork', 'lamb', 'meat']):
            return {
                'calories': 320,
                'protein': 35,
                'fat': 14,
                'carbs': 8,
                'fiber': 0,
                'sugar': 1,
                'sodium': 400
            }
        
        # Soups are lighter
        elif any(x in dish_lower for x in ['soup', 'broth', 'stew', 'curry']):
            return {
                'calories': 200,
                'protein': 10,
                'fat': 7,
                'carbs': 22,
                'fiber': 2,
                'sugar': 3,
                'sodium': 500
            }
        
        # Default: balanced meal estimate
        else:
            return {
                'calories': 250,
                'protein': 12,
                'fat': 9,
                'carbs': 32,
                'fiber': 2,
                'sugar': 5,
                'sodium': 400
            }


# Create singleton instance
nutrition_fetcher = NutritionFetcher()
