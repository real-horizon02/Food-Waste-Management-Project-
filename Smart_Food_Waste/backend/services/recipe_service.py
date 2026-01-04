"""
Recipe service for fetching recipes from external APIs
"""
import requests
import json
import sys
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import Config
try:
    from config import Config
except ImportError:
    try:
        from backend.config import Config
    except ImportError:
        Config = None

# Try to import IngredientExtractor
_ingredient_extractor_class = None
try:
    from services.ingredient_extractor import IngredientExtractor
    _ingredient_extractor_class = IngredientExtractor
except ImportError:
    try:
        from backend.services.ingredient_extractor import IngredientExtractor
        _ingredient_extractor_class = IngredientExtractor
    except ImportError:
        _ingredient_extractor_class = None

# Try to import NLPProcessor
_nlp_processor_class = None
try:
    # Add project root for ai_module
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from ai_module.nlp_processor import NLPProcessor
    _nlp_processor_class = NLPProcessor
except ImportError:
    _nlp_processor_class = None

# Try to import InstructionProcessor
_instruction_processor_class = None
try:
    from services.instruction_processor import InstructionProcessor
    _instruction_processor_class = InstructionProcessor
except ImportError:
    try:
        from backend.services.instruction_processor import InstructionProcessor
        _instruction_processor_class = InstructionProcessor
    except ImportError:
        _instruction_processor_class = None

# Try to import NutritionFetcher
_nutrition_fetcher_class = None
try:
    from services.nutrition_fetcher import NutritionFetcher
    _nutrition_fetcher_class = NutritionFetcher
except ImportError:
    try:
        from backend.services.nutrition_fetcher import NutritionFetcher
        _nutrition_fetcher_class = NutritionFetcher
    except ImportError:
        _nutrition_fetcher_class = None

# Try to import India Localizer
_india_localizer_class = None
try:
    from services.india_localizer import IndiaCentricLocalizer
    _india_localizer_class = IndiaCentricLocalizer
except ImportError:
    try:
        from backend.services.india_localizer import IndiaCentricLocalizer
        _india_localizer_class = IndiaCentricLocalizer
    except ImportError:
        _india_localizer_class = None


class RecipeService:
    """Service for fetching and parsing recipes"""
    
    def __init__(self):
        # Get API keys
        if Config:
            self.api_key = Config.GOOGLE_SEARCH_API_KEY
            self.search_engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
        else:
            from dotenv import load_dotenv
            load_dotenv()
            self.api_key = os.getenv('GOOGLE_SEARCH_API_KEY', '')
            self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')
        
        # Initialize MongoDB Recipe model for caching
        try:
            from models.recipe import Recipe
            self.Recipe = Recipe
            self.use_cache = True
        except Exception as e:
            print(f"Warning: Could not initialize Recipe model for caching: {e}")
            self.Recipe = None
            self.use_cache = False
        
        # Cache TTL in hours (recipes expire after this duration)
        self.cache_ttl_hours = 24
        
    # Initialize ingredient extractor
        if _ingredient_extractor_class:
            try:
                self.ingredient_extractor = _ingredient_extractor_class()
            except Exception as e:
                print(f"Warning: Could not initialize IngredientExtractor: {e}")
                self.ingredient_extractor = None
        else:
            print("Warning: IngredientExtractor not available - recipe parsing may be limited")
            self.ingredient_extractor = None
        
        # Initialize NLP processor
        if _nlp_processor_class:
            try:
                self.nlp_processor = _nlp_processor_class()
            except Exception as e:
                print(f"Warning: Could not initialize NLPProcessor: {e}")
                self.nlp_processor = None
        else:
            print("Warning: NLPProcessor not available - NLP processing will be skipped")
            self.nlp_processor = None
        
        # Initialize Instruction Processor
        if _instruction_processor_class:
            try:
                self.instruction_processor = _instruction_processor_class()
            except Exception as e:
                print(f"Warning: Could not initialize InstructionProcessor: {e}")
                self.instruction_processor = None
        else:
            print("Warning: InstructionProcessor not available - instructions will not be enhanced")
            self.instruction_processor = None
        
        # Initialize Nutrition Fetcher (CRITICAL - should never fail)
        if _nutrition_fetcher_class:
            try:
                self.nutrition_fetcher = _nutrition_fetcher_class()
            except Exception as e:
                print(f"Warning: Could not initialize NutritionFetcher: {e}")
                self.nutrition_fetcher = None
        else:
            print("Warning: NutritionFetcher not available")
            self.nutrition_fetcher = None
        
        # Initialize India Localizer (for India-centric localization)
        if _india_localizer_class:
            try:
                self.india_localizer = _india_localizer_class()
            except Exception as e:
                print(f"Warning: Could not initialize IndiaCentricLocalizer: {e}")
                self.india_localizer = None
        else:
            print("Warning: IndiaCentricLocalizer not available")
            self.india_localizer = None
        
        # Ensure Spoonacular key is available on the instance for debug/usage
        try:
            if Config:
                self.spoonacular_key = Config.SPOONACULAR_API_KEY
            else:
                from dotenv import load_dotenv
                load_dotenv()
                import os as _os
                self.spoonacular_key = _os.getenv('SPOONACULAR_API_KEY', '')
        except Exception:
            self.spoonacular_key = ''
        
        # Debugging flag - set RECIPE_DEBUG=true in env to include debug info in responses
        try:
            import os as _os2
            self.debug = _os2.getenv('RECIPE_DEBUG', 'false').lower() in ('1', 'true', 'yes')
        except Exception:
            self.debug = False
        # Debugging flag - set RECIPE_DEBUG=true in env to include debug info in responses
        try:
            self.debug = os.getenv('RECIPE_DEBUG', 'false').lower() in ('1', 'true', 'yes')
        except Exception:
            self.debug = False
    
    def fetch_recipe(self, dish_name):
        """
        Fetch recipe using multiple strategies with caching:
        1. Check for misspellings and suggest corrections
        2. Check MongoDB cache first (if available and not expired)
        3. Try Spoonacular API first (most reliable structured data)
        4. Try Google Custom Search API (if configured)
        5. Fallback to direct web scraping from popular recipe sites
        6. Works with ANY dish name (no cuisine filtering that might fail)
        
        Args:
            dish_name: Name of the dish to search for
        
        Returns:
            Dictionary containing recipe data (never None)
        """
        if not dish_name or not dish_name.strip():
            return self._create_fallback_recipe(dish_name or 'Unknown Dish')
        
        dish_name = dish_name.strip()
        
        # Try to detect and correct common misspellings
        suggested_name = self._suggest_spelling_correction(dish_name)
        if suggested_name and suggested_name.lower() != dish_name.lower():
            print(f"[INFO] Suggested correction: '{dish_name}' -> '{suggested_name}'")
            # Try with corrected spelling first
            result = self._fetch_recipe_internal(suggested_name)
            if result.get('source_type') != 'manual':  # If not fallback, return it
                return result
            # Otherwise fall through to original spelling
        
        # Use original or suggested name
        return self._fetch_recipe_internal(dish_name)
    
    def _fetch_recipe_internal(self, dish_name):
        """Internal method that does the actual fetching (NO HARDCODED DATA)"""
        # Check cache (MongoDB) first
        cached_recipe = self._get_cached_recipe(dish_name)
        if cached_recipe:
            print(f"[OK] Found recipe in cache for: {dish_name}")
            if self.debug:
                cached_recipe['debug'] = {'source': 'cache'}
            return cached_recipe

        # Try Spoonacular API
        print(f"Trying Spoonacular for: {dish_name}")
        spoonacular_data = self._fetch_from_spoonacular(dish_name)
        if spoonacular_data and spoonacular_data.get('ingredients') and len(spoonacular_data.get('ingredients', [])) > 0:
            print(f"[OK] Found recipe via Spoonacular API for: {dish_name}")
            if self.debug:
                spoonacular_data['debug'] = {'source': 'spoonacular', 'ingredient_count': len(spoonacular_data.get('ingredients', []))}
            return self._apply_india_localization(spoonacular_data)

        # Try Google Custom Search API (if configured)
        print(f"[INFO] Trying Google Custom Search for: {dish_name}")
        try:
            google_recipe = self._try_google_search(dish_name)
            if google_recipe and google_recipe.get('ingredients') and len(google_recipe.get('ingredients', [])) > 0:
                print(f"[OK] Found recipe via Google Search for: {dish_name}")
                if self.debug:
                    google_recipe['debug'] = {'source': 'google_search', 'ingredient_count': len(google_recipe.get('ingredients', []))}
                return self._apply_india_localization(google_recipe)
        except Exception as e:
            print(f"[WARN] Google Search attempt failed: {e}")

        # Fallback: Use direct web scraping
        print(f"[INFO] Spoonacular unavailable, trying web scraping for: {dish_name}")
        web_recipe = self._scrape_recipe_from_web(dish_name)
        if web_recipe and web_recipe.get('ingredients') and len(web_recipe.get('ingredients', [])) > 0:
            print(f"[OK] Found recipe via web scraping for: {dish_name}")
            if not web_recipe.get('nutrition'):
                try:
                    if self.nutrition_fetcher:
                        web_recipe['nutrition'] = self.nutrition_fetcher.get_nutrition(
                            dish_name,
                            web_recipe.get('ingredients', []),
                            web_recipe.get('servings', 1)
                        )
                    else:
                        web_recipe['nutrition'] = self._estimate_nutrition(web_recipe.get('ingredients', []))
                except Exception as e:
                    print(f"Warning: Could not get nutrition: {e}")
                    web_recipe['nutrition'] = self._estimate_nutrition(web_recipe.get('ingredients', []))
            if self.debug:
                web_recipe['debug'] = {'source': 'web_scraping', 'ingredient_count': len(web_recipe.get('ingredients', []))}
            return self._apply_india_localization(web_recipe)

        # No recipe found from any source
        print(f"[WARN] No recipe found from any source for: {dish_name}")
        return {
            'dish_name': dish_name,
            'ingredients': [],
            'instructions': [],
            'servings': 0,
            'source_url': '',
            'source_type': 'not_found',
            'nutrition': {},
            'summary': 'No recipe data found from Spoonacular, Google, or web scraping.'
        }
    
    def _scrape_recipe_from_web(self, dish_name):
        """
        Scrape recipe from popular recipe websites without needing Google CSE API.
        Uses direct search strategies and structured data extraction.
        """
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        
        # Strategy 1: Try recipe sites with direct recipe URLs
        recipe_attempts = [
            # AllRecipes direct recipe search
            lambda name: f"https://www.allrecipes.com/search/results/?wt={urllib.parse.quote(name)}",
            # Food.com recipe search  
            lambda name: f"https://www.food.com/search/{urllib.parse.quote(name)}",
            # BBC Good Food
            lambda name: f"https://www.bbcgoodfood.com/search?q={urllib.parse.quote(name)}",
        ]

        # Always include some Indian-focused recipe sites to improve coverage
        # (helps with misspellings and variations like 'Briyani' vs 'Biryani')
        recipe_attempts.extend([
            lambda name: f"https://www.vegrecipesofindia.com/search/?q={urllib.parse.quote(name)}",
            lambda name: f"https://www.archanaskitchen.com/?s={urllib.parse.quote(name)}",
        ])
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        for attempt in recipe_attempts:
            try:
                search_url = attempt(dish_name)
                domain = search_url.split('/')[2]
                print(f"  Trying {domain}...")
                
                response = requests.get(search_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for structured recipe data (JSON-LD) on search page
                structured = self._extract_structured_recipe(soup)
                if structured and structured.get('recipeIngredient'):
                    print(f"    [OK] Found structured recipe data")
                    # Parse the structured data directly
                    ingredients = self._ingredients_from_structured(structured)
                    instructions = self._instructions_from_structured(structured)
                    if ingredients and len(ingredients) >= 3:
                        return {
                            'dish_name': structured.get('name', dish_name),
                            'ingredients': ingredients,
                            'instructions': instructions,
                            'servings': self._extract_servings_from_structured(structured) or 4,
                            'source_url': search_url,
                            'source_type': 'web_scraping'
                        }
                
                # Look for recipe links in search results
                recipe_links = self._extract_recipe_links(soup, search_url)
                
                # Try each recipe link
                for recipe_url in recipe_links:
                    try:
                        recipe_data = self._parse_recipe_page(recipe_url, dish_name)
                        if recipe_data and recipe_data.get('ingredients') and len(recipe_data['ingredients']) >= 3:
                            # Quick heuristic: ensure ingredients contain at least one likely food-related keyword
                            food_keywords = ['rice', 'chicken', 'onion', 'tomato', 'garlic', 'potato', 'masala', 'coriander', 'cilantro', 'cumin', 'turmeric', 'dal', 'lentil', 'paneer', 'egg', 'yogurt', 'milk', 'butter', 'ghee']
                            found_food_kw = False
                            for ing in recipe_data.get('ingredients', []):
                                name = (ing.get('name') or '').lower()
                                for kw in food_keywords:
                                    if kw in name:
                                        found_food_kw = True
                                        break
                                if found_food_kw:
                                    break

                            if not found_food_kw:
                                # Likely parsed UI/menu text; skip this candidate
                                print(f"      Candidate at {recipe_url} lacks food keywords, skipping")
                                continue

                            print(f"    [OK] Found {len(recipe_data['ingredients'])} ingredients")
                            return recipe_data
                    except Exception as e:
                        print(f"      Parse error: {str(e)[:40]}")
                        continue
            
            except Exception as e:
                print(f"  Error: {str(e)[:60]}")
                continue
        
        return None
    
    def _extract_recipe_links(self, soup, base_url):
        """Extract links that look like recipe pages from search results"""
        recipe_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            
            # Skip obvious navigation links (avoid over-filtering so recipe links are not dropped)
            if any(skip in link_text for skip in ['search', 'browse', 'submit', 'log in', 'home', 'about', 'privacy', 'terms']):
                continue
            
            # Link should contain 'recipe' or look like a recipe page
            is_recipe_link = (
                'recipe' in href.lower() or 
                'recipe' in link_text or
                'ingredient' in link_text
            )
            
            if not is_recipe_link:
                continue
            
            # Convert relative URLs to absolute
            if href.startswith('http'):
                recipe_links.append(href)
            elif href.startswith('/'):
                from urllib.parse import urljoin
                recipe_links.append(urljoin(base_url, href))
            
            if len(recipe_links) >= 5:  # Get up to 5 recipe links
                break
        
        return recipe_links
    
    def fetch_recipe_old(self, dish_name):
        """DISABLED - Old parallel API strategy. Kept for reference."""
        if not dish_name or not dish_name.strip():
            # Return minimal structure
            return self._create_fallback_recipe(dish_name or 'Unknown Dish')
        
        dish_name = dish_name.strip()
        spoonacular_data = None
        google_data = None
        
        # BEST CASE: Both APIs returned data - merge them
        if False and spoonacular_data and google_data:
            merged_data = {
                'dish_name': google_data.get('dish_name') or spoonacular_data.get('dish_name', dish_name),
                'ingredients': spoonacular_data.get('ingredients') or google_data.get('ingredients', []),  # Prefer Spoonacular ingredients
                'instructions': google_data.get('instructions') or spoonacular_data.get('instructions', []),  # Prefer Google instructions (more detailed)
                'servings': google_data.get('servings') or spoonacular_data.get('servings', 4),
                'source_url': google_data.get('source_url', ''),
                'source_type': 'spoonacular',  # Mark as spoonacular when both available
                'title': google_data.get('title') or spoonacular_data.get('title'),
                'summary': spoonacular_data.get('summary') or google_data.get('summary'),
                'prep_time': spoonacular_data.get('prep_time') or google_data.get('prep_time'),
                'cook_time': spoonacular_data.get('cook_time') or google_data.get('cook_time'),
                'total_time': spoonacular_data.get('total_time') or google_data.get('total_time'),
                'nutrition': spoonacular_data.get('nutrition') or google_data.get('nutrition')  # Prefer Spoonacular nutrition
            }
            # attach debug info when enabled
            if self.debug:
                merged_data['debug'] = {
                    'spoonacular_has_ingredients': True,
                    'google_has_ingredients': True,
                    'spoonacular_ingredient_count': len(spoonacular_data.get('ingredients', [])) if spoonacular_data else 0,
                    'google_ingredient_count': len(google_data.get('ingredients', [])) if google_data else 0,
                    'spoonacular_key_present': bool(getattr(self, 'spoonacular_key', None) or os.getenv('SPOONACULAR_API_KEY')),
                    'google_key_present': bool(self.api_key and self.search_engine_id)
                }
            print(f"[OK] Merged recipe data from BOTH APIs for: {dish_name}")
            return merged_data
        

    
    def _try_google_search(self, dish_name):
        """Try to fetch recipe via Google Search API + web scraping + NLP processing"""
        if not self.api_key or not self.search_engine_id:
            print(f"Warning: Google Search API credentials not configured")
            return None
        
        try:
            # Search for recipe using Google Custom Search API
            # Try multiple search queries for better results (especially for Indian dishes)
            search_queries = [
                f"{dish_name} recipe",
                f"{dish_name} indian recipe",
                f"how to make {dish_name}",
                f"{dish_name} ingredients and method"
            ]
            
            url = f"https://www.googleapis.com/customsearch/v1"
            
            for search_query in search_queries:
                params = {
                    'key': self.api_key,
                    'cx': self.search_engine_id,
                    'q': search_query,
                    'num': 10  # Get more results for better coverage
                }
                
                try:
                    response = requests.get(url, params=params, timeout=25)
                    
                    if response.status_code == 200:
                        search_results = response.json()
                        
                        if 'items' in search_results and len(search_results['items']) > 0:
                            # Try to parse each result until we get valid recipe data
                            for item in search_results['items']:
                                recipe_url = item.get('link', '')
                                if recipe_url:
                                    try:
                                        print(f"  Trying to parse recipe from: {recipe_url}")
                                        recipe_data = self._parse_recipe_page(recipe_url, dish_name)
                                        
                                        # Check if we got valid recipe data with ingredients
                                        if recipe_data and recipe_data.get('ingredients') and len(recipe_data.get('ingredients', [])) > 0:
                                            # Ensure we have at least 3 ingredients (not just placeholder)
                                            ingredients = recipe_data.get('ingredients', [])
                                            valid_ingredients = [ing for ing in ingredients if ing.get('name') and len(ing.get('name', '').strip()) > 3]
                                            
                                            if len(valid_ingredients) >= 3:
                                                recipe_data['source_url'] = recipe_url
                                                recipe_data['source_type'] = 'google_search'
                                                print(f"[OK] Found valid recipe via Google Search API for: {dish_name} ({len(valid_ingredients)} ingredients)")
                                                return recipe_data
                                            else:
                                                print(f"  Recipe from {recipe_url} has too few valid ingredients ({len(valid_ingredients)}), trying next...")
                                    except Exception as e:
                                        print(f"  Error parsing recipe from {recipe_url}: {e}")
                                        continue
                    
                    # If we found results but none were valid, try next search query
                    if 'items' in search_results and len(search_results['items']) > 0:
                        continue
                    else:
                        break  # No results for this query, try next
                        
                except requests.exceptions.Timeout:
                    print(f"  Timeout for search query: {search_query}")
                    continue
                except Exception as e:
                    print(f"  Error with search query '{search_query}': {e}")
                    continue
                    
        except Exception as e:
            print(f"Error with Google Search API: {str(e)}")
        
        return None
    
    # Hardcoded recipe logic removed. No static recipes allowed.
        if lookup_name in hardcoded_recipes:
            return hardcoded_recipes[lookup_name].copy()
        
        # Check for variations/aliases
        aliases = {
            'gol gappa': 'gol gappe',
            'goleappa': 'gol gappe',
            'puchka': 'gol gappe',
            'phuska': 'gol gappe',
            'phuchka': 'gol gappe',
            'panipuri': 'pani puri',
            'pani-puri': 'pani puri',
            'spicy puri': 'pani puri',
        }
        
        if lookup_name in aliases:
            canonical_name = aliases[lookup_name]
            if canonical_name in hardcoded_recipes:
                return hardcoded_recipes[canonical_name].copy()
        
        return None
    
    def _create_fallback_recipe(self, dish_name):
        """Create a basic recipe structure when no recipe is found"""
        # Get nutrition data from fetcher
        nutrition = None
        if self.nutrition_fetcher:
            try:
                nutrition = self.nutrition_fetcher.get_nutrition(dish_name)
            except Exception as e:
                print(f"Warning: Could not get nutrition for fallback: {e}")
        
        # Fallback nutrition if fetcher is unavailable
        if not nutrition:
            nutrition = {'calories': 250, 'protein': 12, 'fat': 9, 'carbs': 32, 'fiber': 2, 'sugar': 5, 'sodium': 400}
        
        return {
            'dish_name': dish_name,
            'title': dish_name,
            'ingredients': [
                {
                    'name': f'Ingredients for {dish_name}',
                    'quantity': '1',
                    'unit': '',
                    'category': 'other'
                }
            ],
            'instructions': [
                f'Search online for "{dish_name} recipe" to find detailed instructions.',
                'Common ingredients and steps will be available once a recipe source is found.'
            ],
            'servings': 4,
            'source_url': '',
            'source_type': 'manual',  # Use 'manual' for fallback recipes
            'summary': f'Recipe information for {dish_name}. Please try searching with a recipe URL or different dish name for detailed ingredients and instructions.',
            'nutrition': nutrition,
            'prep_time': None,
            'cook_time': None,
            'total_time': None
        }
    
    def _parse_recipe_page(self, url, dish_name):
        """
        Parse recipe from a webpage
        
        Args:
            url: URL of the recipe page
            dish_name: Name of the dish
        
        Returns:
            Dictionary containing recipe data or None
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
                'Accept-Charset': 'UTF-8'
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            # Ensure proper UTF-8 encoding for Hindi/English content
            response.encoding = response.apparent_encoding or 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try site-specific parsers first (more accurate and faster)
            if 'bbcgoodfood.com' in url.lower():
                result = self._parse_bbc_good_food(soup, url, dish_name)
                if result:
                    return result
            elif 'vegrecipesofindia.com' in url.lower():
                result = self._parse_veg_recipes_of_india(soup, url, dish_name)
                if result:
                    return result

            # Attempt to extract structured recipe data first (most reliable)
            structured_recipe = self._extract_structured_recipe(soup)
            structured_servings = None
            structured_ingredients = []
            structured_instructions = []
            structured_title = None

            if structured_recipe:
                structured_title = structured_recipe.get('name')
                structured_servings = self._extract_servings_from_structured(structured_recipe)
                structured_ingredients = self._ingredients_from_structured(structured_recipe)
                structured_instructions = self._instructions_from_structured(structured_recipe)
            
            # Get raw HTML content for NLP processing
            raw_html_content = str(soup)
            raw_text_content = soup.get_text(separator='\n', strip=True)
            
            # Process with NLP model if available
            nlp_processed = None
            if self.nlp_processor:
                try:
                    # Use HTML content for better structure extraction
                    nlp_processed = self.nlp_processor.process_recipe_text(raw_html_content)
                except Exception as e:
                    print(f"Warning: NLP processing failed: {e}")
                    # Fallback to text content
                    try:
                        nlp_processed = self.nlp_processor.process_recipe_text(raw_text_content)
                    except Exception as e2:
                        print(f"Warning: NLP processing with text also failed: {e2}")
            
            # Extract ingredients - prioritize structured data, then NLP processed, then extractor
            ingredients = []
            if structured_ingredients:
                ingredients = structured_ingredients
                # Convert units to Indian units for structured ingredients
                for ing in ingredients:
                    if ing.get('unit'):
                        unit = ing['unit']
                        indian_unit, _ = self._convert_to_indian_units(1, unit)
                        ing['unit'] = indian_unit
            elif nlp_processed and nlp_processed.get('ingredients'):
                ingredients = nlp_processed['ingredients']
                # Convert units to Indian units
                for ing in ingredients:
                    if ing.get('unit'):
                        unit = ing['unit']
                        indian_unit, _ = self._convert_to_indian_units(1, unit)
                        ing['unit'] = indian_unit
            elif self.ingredient_extractor:
                ingredients = self.ingredient_extractor.extract_from_html(soup)
                # Units are already converted in ingredient_extractor
            else:
                # Fallback: basic ingredient extraction
                ingredients = self._basic_ingredient_extraction(soup)
                # Try to extract and convert units from basic extraction
                for ing in ingredients:
                    if ing.get('name') and not ing.get('unit'):
                        # Try to parse unit from name
                        name_parts = ing['name'].split()
                        if name_parts:
                            first_word = name_parts[0].lower()
                            # Check if first word is a unit
                            if first_word in ['cup', 'cups', 'tbsp', 'tsp', 'g', 'kg', 'ml', 'l', 'gram', 'grams']:
                                indian_unit, _ = self._convert_to_indian_units(1, first_word)
                                ing['unit'] = indian_unit
                                ing['name'] = ' '.join(name_parts[1:])
                            elif first_word in ['कप', 'चम्मच', 'ग्राम', 'किलो']:
                                # Hindi unit
                                if first_word in ['कप', 'कप्स']:
                                    ing['unit'] = 'cup'
                                elif first_word in ['चम्मच', 'चमच']:
                                    ing['unit'] = 'tsp'
                                elif first_word in ['ग्राम', 'ग्राम्स']:
                                    ing['unit'] = 'g'
                                elif first_word in ['किलो', 'किलोग्राम']:
                                    ing['unit'] = 'kg'
                                ing['name'] = ' '.join(name_parts[1:])

            # Extract instructions - prioritize structured data, then NLP, then fallback
            if structured_instructions:
                instructions = structured_instructions
            elif nlp_processed and nlp_processed.get('steps'):
                instructions = nlp_processed['steps']
            else:
                instructions = self._extract_instructions(soup)

            # Extract serving size
            if structured_servings is not None:
                servings = structured_servings
            else:
                servings = self._extract_servings(soup)

            # Determine title preference: structured -> NLP -> fallback
            recipe_title = (
                structured_title
                or (nlp_processed.get('title') if nlp_processed else None)
                or dish_name
            )
            
            # IMPORTANT: Validate that we actually got real recipe data
            # Filter out navigation/category links by checking ingredient quality
            if not ingredients:
                return None
            
            # Check if ingredients look like real recipe ingredients (not navigation)
            real_ingredients = []
            # Generic UI/text noise to ignore (e.g., 'More', 'Trending', 'See more')
            noise_blacklist = set([
                'more', 'see more', 'trending', 'click here', 'read more', 'watch', 'share', 'related', 'subscribe',
                # menu/category words commonly picked up as 'ingredients'
                'recipes', 'recipe', 'breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'brunch', 'cocktail', 'drink',
                'appetizers', 'side', 'bbq', 'grilling', 'menus', 'menu'
            ])
            for ing in ingredients:
                name = ing.get('name', '').strip().lower()
                # Filter out navigation-like entries
                if any(skip in name for skip in ['search', 'browse', 'submit', 'log in', 'home', 'about']):
                    continue
                # Remove common non-ingredient UI words
                if any(noise in name for noise in noise_blacklist):
                    continue
                # Ensure it's a reasonable ingredient name (not too short, not navigation)
                # Also ignore entries that are mostly non-alphabetic
                alpha_chars = sum(1 for c in name if c.isalpha())
                if len(name) > 2 and len(name) < 100 and alpha_chars >= 2:
                    real_ingredients.append(ing)
            
            # If we filtered out too many, this isn't a real recipe page
            if len(real_ingredients) < 3:
                print(f"      Not a recipe page - insufficient valid ingredients")
                return None
            
            ingredients = real_ingredients
            
            result = {
                'dish_name': recipe_title or dish_name,
                'ingredients': ingredients,
                'instructions': instructions,
                'servings': servings,
                'raw_data': {
                    'url': url,
                    'html_preview': soup.get_text()[:500],  # First 500 chars
                    'nlp_processed': nlp_processed,  # Store NLP processed data
                    'structured_recipe': structured_recipe
                }
            }
            # Add source metadata for web-scraped results
            result['source_type'] = 'web_scraping'
            result['source_url'] = url
            
            # Add summary if available from NLP
            if nlp_processed and nlp_processed.get('summary'):
                result['summary'] = nlp_processed['summary']
            
            # Process and enhance instructions to professional format
            if self.instruction_processor and instructions:
                try:
                    processed_instructions = self.instruction_processor.process_instructions(instructions)
                    result['instructions_enhanced'] = {
                        'professional_steps': processed_instructions.get('professional_steps', []),
                        'tips': processed_instructions.get('tips', []),
                        'warnings': processed_instructions.get('warnings', []),
                        'timeline': processed_instructions.get('timeline', {})
                    }
                    # Replace instructions with professional version for display
                    result['instructions'] = processed_instructions.get('professional_steps', instructions)
                except Exception as e:
                    print(f"Warning: Could not enhance instructions: {e}")
                    result['instructions_enhanced'] = None
            
            # Add nutrition estimation based on ingredients
            try:
                if self.nutrition_fetcher:
                    result['nutrition'] = self.nutrition_fetcher.get_nutrition(
                        url.split('/')[-1] or result.get('title') or dish_name,
                        ingredients,
                        result.get('servings', 1)
                    )
                else:
                    result['nutrition'] = self._estimate_nutrition(ingredients)
                    
                # If nutrition is still somehow None, use fallback
                if not result['nutrition']:
                    result['nutrition'] = {'calories': 250, 'protein': 12, 'fat': 9, 'carbs': 32, 'fiber': 2, 'sugar': 5, 'sodium': 400}
            except Exception as e:
                print(f"Warning: Could not estimate nutrition: {e}")
                # NEVER return None - use fallback
                result['nutrition'] = {'calories': 250, 'protein': 12, 'fat': 9, 'carbs': 32, 'fiber': 2, 'sugar': 5, 'sodium': 400}
            
            return result
        
        except Exception as e:
            print(f"Error parsing recipe page: {str(e)}")
            return None
    
    def _extract_instructions(self, soup):
        """Extract cooking instructions from HTML"""
        instructions = []
        
        # Try common recipe instruction patterns
        instruction_selectors = [
            {'itemprop': 'recipeInstructions'},
            {'class': 'recipe-instructions'},
            {'class': 'instructions'},
            {'id': 'instructions'},
            {'class': 'recipe-steps'}
        ]
        
        for selector in instruction_selectors:
            elements = soup.find_all(attrs=selector)
            if elements:
                for elem in elements:
                    # Try to get ordered list items or paragraphs
                    steps = elem.find_all(['li', 'p', 'div'])
                    for step in steps:
                        text = step.get_text().strip()
                        if text and len(text) > 10:  # Filter out very short text
                            instructions.append(text)
                if instructions:
                    break
        
        # If no structured instructions found, try to extract from paragraphs
        if not instructions:
            paragraphs = soup.find_all('p')
            for p in paragraphs:  # Process all paragraphs (no limit)
                text = p.get_text().strip()
                if text and len(text) > 10:  # Lower threshold to catch more steps
                    instructions.append(text)
        
        return instructions  # Return all instructions without limit
    
    def _extract_servings(self, soup):
        """Extract serving size from HTML (handles Hindi/English)"""
        # Try to find serving information
        serving_selectors = [
            {'itemprop': 'recipeYield'},
            {'class': 'servings'},
            {'class': 'recipe-servings'},
            {'id': 'servings'},
            {'class': re.compile(r'serv', re.I)},
            {'class': re.compile(r'yield', re.I)}
        ]
        
        for selector in serving_selectors:
            elem = soup.find(attrs=selector)
            if elem:
                text = elem.get_text().strip()
                # Try to extract number (handles "4 servings", "4 लोगों के लिए", etc.)
                numbers = re.findall(r'\d+', text)
                if numbers:
                    try:
                        return int(numbers[0])
                    except:
                        pass
        
        # Try to find in text content (Hindi: "लोगों के लिए", English: "servings", "people")
        text_content = soup.get_text()
        serving_patterns = [
            r'(\d+)\s*(?:servings?|people|persons|लोगों?|सर्विंग)',
            r'(?:servings?|people|persons|लोगों?|सर्विंग)[\s:]*(\d+)',
            r'(\d+)\s*(?:के\s*लिए|for)'
        ]
        
        for pattern in serving_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE | re.UNICODE)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        
        # Default servings
        return 4

    def _extract_structured_recipe(self, soup):
        """
        Try to extract structured recipe data (JSON-LD) from the page.
        Returns the first recipe node found or None.
        """
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                raw_content = script.string or script.text
                if not raw_content:
                    continue
                raw_content = raw_content.strip()
                # Remove HTML comments/wrappers that break JSON parsing
                raw_content = re.sub(r'<!--(.*?)-->', '', raw_content, flags=re.DOTALL)
                data = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError):
                # Some sites concatenate multiple JSON objects without wrapping
                try:
                    data = json.loads(raw_content.replace('\n', ''))
                except Exception:
                    continue

            recipe_node = self._find_recipe_node(data)
            if recipe_node:
                return recipe_node
        return None

    def _find_recipe_node(self, data):
        """Recursively search for a node with @type Recipe."""
        if isinstance(data, list):
            for item in data:
                found = self._find_recipe_node(item)
                if found:
                    return found
        elif isinstance(data, dict):
            node_type = data.get('@type') or data.get('type')
            if node_type:
                types = node_type if isinstance(node_type, list) else [node_type]
                types_normalized = {str(t).lower() for t in types}
                if 'recipe' in types_normalized:
                    return data
            # Look within @graph or itemListElement for nested nodes
            for key in ('@graph', 'graph', 'itemListElement'):
                if key in data and isinstance(data[key], (list, dict)):
                    found = self._find_recipe_node(data[key])
                    if found:
                        return found
        return None

    def _ingredients_from_structured(self, structured_recipe):
        """Convert structured recipeIngredient data to standardized format (handles Hindi/English)."""
        raw_ingredients = structured_recipe.get('recipeIngredient') or structured_recipe.get('ingredients')
        if not raw_ingredients:
            return []

        if isinstance(raw_ingredients, str):
            raw_ingredients = [raw_ingredients]

        raw_lines = []
        for item in raw_ingredients:
            if isinstance(item, str):
                # Ensure UTF-8 encoding for Hindi text
                try:
                    cleaned = item.encode('utf-8', errors='ignore').decode('utf-8').strip()
                except:
                    cleaned = item.strip()
                if cleaned:
                    raw_lines.append(cleaned)

        if not raw_lines:
            return []

        if self.ingredient_extractor and hasattr(self.ingredient_extractor, 'extract_from_lines'):
            ingredients = self.ingredient_extractor.extract_from_lines(raw_lines)
            # Convert units to Indian units
            for ing in ingredients:
                if ing.get('unit'):
                    unit = ing['unit']
                    indian_unit, _ = self._convert_to_indian_units(1, unit)  # Just get unit conversion
                    ing['unit'] = indian_unit
            return ingredients

        # Basic fallback - still try to parse
        result = []
        for line in raw_lines:
            # Try basic parsing
            parsed = self._parse_basic_ingredient_line(line)
            if parsed:
                result.append(parsed)
            else:
                result.append({
                    'name': line,
                    'quantity': '1',
                    'unit': '',
                    'category': self._categorize_ingredient(line)
                })
        return result
    
    def _parse_basic_ingredient_line(self, line):
        """Basic ingredient line parser for fallback"""
        import re
        # Try to extract quantity and unit
        match = re.match(r'(\d+(?:\.\d+)?(?:/\d+)?)\s*([a-zA-Z\u0900-\u097F]+)?\s*(.+)', line, re.UNICODE)
        if match:
            quantity = match.group(1)
            unit = match.group(2) or ''
            name = match.group(3).strip()
            
            # Convert unit to Indian units
            if unit:
                unit, _ = self._convert_to_indian_units(1, unit)
            
            return {
                'name': name,
                'quantity': quantity,
                'unit': unit,
                'category': self._categorize_ingredient(name)
            }
        return None

    def _instructions_from_structured(self, structured_recipe):
        """Normalize structured instructions to a list of strings."""
        instructions = structured_recipe.get('recipeInstructions')
        steps = []

        if not instructions:
            return steps

        def handle_instruction_node(node):
            if isinstance(node, str):
                text = node.strip()
                if text:
                    steps.append(text)
            elif isinstance(node, dict):
                # Handle HowToSection containing list of steps
                if node.get('@type') in ('HowToSection', 'ItemList'):
                    items = node.get('itemListElement', [])
                    for item in items:
                        handle_instruction_node(item)
                else:
                    text = node.get('text') or node.get('name')
                    if text:
                        text = text.strip()
                        if text:
                            steps.append(text)
            elif isinstance(node, list):
                for child in node:
                    handle_instruction_node(child)

        handle_instruction_node(instructions)

        # Deduplicate while preserving order
        seen = set()
        normalized_steps = []
        for step in steps:
            key = step.strip()
            if key and key not in seen:
                seen.add(key)
                normalized_steps.append(key)
        return normalized_steps  # Return all steps without limit

    def _extract_servings_from_structured(self, structured_recipe):
        """Extract servings information from structured data."""
        raw_yield = structured_recipe.get('recipeYield') or structured_recipe.get('yield')
        if not raw_yield:
            return None

        if isinstance(raw_yield, list):
            raw_yield = ' '.join(str(item) for item in raw_yield if item)

        if isinstance(raw_yield, str):
            matches = re.findall(r'\d+', raw_yield)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    return None
        elif isinstance(raw_yield, (int, float)):
            try:
                return int(raw_yield)
            except ValueError:
                return None

        return None
    
    def _fetch_from_spoonacular(self, dish_name):
        """Fetch recipe from Spoonacular API (primary method)"""
        # Use the instance-level spoonacular_key (set in __init__)
        spoonacular_key = getattr(self, 'spoonacular_key', '')
        if not spoonacular_key:
            print("Warning: SPOONACULAR_API_KEY not set. Please add it to your .env file.")
            return None
        
        try:
            # Search for recipes (optimized for Indian dishes)
            url = "https://api.spoonacular.com/recipes/complexSearch"
            
            # First try with Indian cuisine filter
            params = {
                'apiKey': spoonacular_key,
                'query': dish_name,
                'number': 1,
                'addRecipeInformation': 'true',  # Get basic info in search
                'cuisine': 'indian'  # Prioritize Indian cuisine
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            # If no results with Indian filter, try without filter
            if response.status_code == 200:
                data = response.json()
                if 'results' not in data or len(data.get('results', [])) == 0:
                    # Retry without cuisine filter for broader search
                    params.pop('cuisine', None)
                    response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    recipe_id = data['results'][0]['id']
                    
                    # Get detailed recipe information with nutrition data
                    detail_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
                    detail_params = {
                        'apiKey': spoonacular_key,
                        'includeNutrition': 'true'  # Enable nutrition data for Indian dishes
                    }
                    detail_response = requests.get(detail_url, params=detail_params, timeout=15)
                    
                    if detail_response.status_code == 200:
                        recipe_detail = detail_response.json()
                        
                        # Extract ingredients (structured data from API) with Indian unit conversion
                        ingredients = []
                        for ing in recipe_detail.get('extendedIngredients', []):
                            # Convert to Indian units
                            amount = ing.get('amount', 1)
                            unit = ing.get('unit', '').strip()
                            indian_unit, indian_amount = self._convert_to_indian_units(amount, unit)
                            
                            ingredients.append({
                                'name': ing.get('name', '').strip(),
                                'quantity': str(indian_amount),
                                'unit': indian_unit,
                                'category': self._categorize_ingredient(ing.get('name', ''))
                            })
                        
                        # Extract instructions (structured steps)
                        instructions = []
                        if 'analyzedInstructions' in recipe_detail and recipe_detail['analyzedInstructions']:
                            for instruction_group in recipe_detail['analyzedInstructions']:
                                for step in instruction_group.get('steps', []):
                                    step_text = step.get('step', '').strip()
                                    if step_text:
                                        instructions.append(step_text)
                        
                        # If no analyzed instructions, try summary
                        if not instructions and recipe_detail.get('instructions'):
                            # Parse HTML instructions if available
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(recipe_detail.get('instructions', ''), 'html.parser')
                            for p in soup.find_all(['p', 'li']):
                                text = p.get_text().strip()
                                if text and len(text) > 10:
                                    instructions.append(text)
                        
                        # Get title
                        title = recipe_detail.get('title', dish_name)
                        
                        # Generate summary
                        summary = recipe_detail.get('summary', '')
                        if summary:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(summary, 'html.parser')
                            summary = soup.get_text().strip()  # Keep full summary, not truncated
                        
                        # Extract nutrition data from Spoonacular API
                        nutrition = None
                        if 'nutrition' in recipe_detail:
                            nutrition_data = recipe_detail['nutrition']
                            
                            # Spoonacular returns nutrients as a list, need to extract by name
                            nutrients_list = nutrition_data.get('nutrients', [])
                            
                            # Helper function to find nutrient by name
                            def find_nutrient(name_keywords):
                                for nutrient in nutrients_list:
                                    nutrient_name = nutrient.get('name', '').lower()
                                    if any(keyword in nutrient_name for keyword in name_keywords):
                                        return nutrient.get('amount', 0)
                                return 0
                            
                            nutrition = {
                                'calories': find_nutrient(['calories', 'energy']),
                                'protein': find_nutrient(['protein']),
                                'fat': find_nutrient(['fat', 'total fat']),
                                'carbs': find_nutrient(['carbohydrates', 'carbs', 'net carbohydrates']),
                                'fiber': find_nutrient(['fiber', 'dietary fiber']),
                                'sugar': find_nutrient(['sugar', 'sugars']),
                                'sodium': find_nutrient(['sodium'])
                            }
                        
                        return {
                            'dish_name': title or dish_name,
                            'ingredients': ingredients,
                            'instructions': instructions,
                            'servings': recipe_detail.get('servings', 4),
                            'prep_time': recipe_detail.get('preparationMinutes'),
                            'cook_time': recipe_detail.get('cookingMinutes'),
                            'total_time': recipe_detail.get('readyInMinutes'),
                            'summary': summary,
                            'title': title,
                            'nutrition': nutrition,  # Add nutrition data
                            'source_type': 'spoonacular',
                            'source_url': recipe_detail.get('sourceUrl', recipe_detail.get('spoonacularSourceUrl', ''))
                        }
            elif response.status_code == 402:
                print("Warning: Spoonacular API quota exceeded. Please check your API key or upgrade plan.")
            else:
                print(f"Warning: Spoonacular API returned status {response.status_code}")
        
        except requests.exceptions.Timeout:
            print("Error: Spoonacular API request timed out")
        except Exception as e:
            print(f"Error fetching from Spoonacular: {str(e)}")
        
        return None
    
    def _convert_to_indian_units(self, amount, unit):
        """
        Convert units to Indian cooking units
        
        Common Indian units:
        - Weight: grams (g), kilograms (kg)
        - Volume: milliliters (ml), liters (l), cups, tablespoons (tbsp), teaspoons (tsp)
        - Small quantities: pinch, handful
        """
        if not unit:
            return '', amount
        
        unit_lower = unit.lower()
        
        # Weight conversions (to grams/kg)
        if unit_lower in ['oz', 'ounce', 'ounces']:
            # 1 oz = 28.35 grams
            grams = amount * 28.35
            if grams >= 1000:
                return 'kg', round(grams / 1000, 2)
            return 'g', round(grams, 1)
        elif unit_lower in ['lb', 'pound', 'pounds']:
            # 1 lb = 453.59 grams
            grams = amount * 453.59
            if grams >= 1000:
                return 'kg', round(grams / 1000, 2)
            return 'g', round(grams, 1)
        
        # Volume conversions
        elif unit_lower in ['fl oz', 'fluid ounce', 'fluid ounces']:
            # 1 fl oz = 29.57 ml
            ml = amount * 29.57
            if ml >= 1000:
                return 'l', round(ml / 1000, 2)
            return 'ml', round(ml, 1)
        elif unit_lower in ['cup', 'cups']:
            # Keep cups as is (common in Indian cooking)
            return 'cup', round(amount, 2)
        elif unit_lower in ['tbsp', 'tablespoon', 'tablespoons']:
            # Keep tbsp as is
            return 'tbsp', round(amount, 1)
        elif unit_lower in ['tsp', 'teaspoon', 'teaspoons']:
            # Keep tsp as is
            return 'tsp', round(amount, 1)
        elif unit_lower in ['ml', 'milliliter', 'milliliters']:
            if amount >= 1000:
                return 'l', round(amount / 1000, 2)
            return 'ml', round(amount, 1)
        elif unit_lower in ['l', 'liter', 'liters', 'litre', 'litres']:
            return 'l', round(amount, 2)
        
        # Weight units (already in metric)
        elif unit_lower in ['g', 'gram', 'grams', 'gm']:
            if amount >= 1000:
                return 'kg', round(amount / 1000, 2)
            return 'g', round(amount, 1)
        elif unit_lower in ['kg', 'kilogram', 'kilograms']:
            return 'kg', round(amount, 2)
        
        # Keep as is for common Indian units
        elif unit_lower in ['piece', 'pieces', 'pcs', 'pc', 'pinch', 'handful', 'handfuls']:
            return unit_lower, round(amount, 1)
        
        # Default: return as is
        return unit, round(amount, 2)
    
    def _categorize_ingredient(self, ingredient_name):
        """Categorize ingredient based on name (including Indian ingredients)"""
        if not ingredient_name:
            return 'other'
        
        name_lower = ingredient_name.lower()
        
        # Indian spices and seasonings
        if any(kw in name_lower for kw in ['turmeric', 'haldi', 'cumin', 'jeera', 'coriander', 'dhania', 
                                            'cardamom', 'elaichi', 'cinnamon', 'dalchini', 'clove', 'laung',
                                            'pepper', 'kali mirch', 'red chili', 'lal mirch', 'garam masala',
                                            'curry powder', 'masala', 'spice', 'spices']):
            return 'spices'
        
        # Produce (including Indian vegetables)
        if any(kw in name_lower for kw in ['tomato', 'tamatar', 'onion', 'pyaz', 'garlic', 'lehsun', 
                                            'potato', 'aloo', 'carrot', 'gajar', 'pepper', 'mirch',
                                            'cucumber', 'kheera', 'spinach', 'palak', 'cauliflower', 'gobi',
                                            'broccoli', 'brinjal', 'baingan', 'okra', 'bhindi', 'cabbage',
                                            'patta gobi', 'lettuce', 'celery', 'mushroom']):
            return 'produce'
        
        # Dairy (including Indian dairy products)
        if any(kw in name_lower for kw in ['milk', 'doodh', 'cheese', 'paneer', 'butter', 'makhan',
                                           'cream', 'malai', 'yogurt', 'curd', 'dahi', 'yoghurt', 'ghee']):
            return 'dairy'
        
        # Meat
        if any(kw in name_lower for kw in ['beef', 'pork', 'lamb', 'mutton', 'steak', 'ground beef', 'ground pork']):
            return 'meat'
        
        # Poultry
        if any(kw in name_lower for kw in ['chicken', 'murg', 'turkey', 'duck']):
            return 'poultry'
        
        # Seafood
        if any(kw in name_lower for kw in ['fish', 'machli', 'salmon', 'shrimp', 'prawn', 'jhinga',
                                           'crab', 'lobster', 'tuna', 'cod']):
            return 'seafood'
        
        # Grains and pulses (important for Indian cooking)
        if any(kw in name_lower for kw in ['rice', 'chawal', 'pasta', 'noodles', 'flour', 'atta', 'maida',
                                            'bread', 'roti', 'chapati', 'wheat', 'gehun', 'quinoa',
                                            'dal', 'lentil', 'chana', 'rajma', 'moong', 'urad', 'toor']):
            return 'grains'
        
        return 'other'

    def _estimate_nutrition(self, ingredients):
        """
        Estimate basic nutrition totals from a list of ingredient dicts.
        This is a lightweight fallback when structured nutrition isn't available.
        It uses simple per-ingredient heuristics and categories to estimate calories, protein, fat, carbs, fiber, sugar, sodium.
        Returns a dict with the nutrient keys or None if estimation fails.
        """
        # Simple nutrition lookup per common ingredient (per typical unit)
        # Values roughly per typical quantity used in recipes (calories, protein(g), fat(g), carbs(g), fiber(g), sugar(g), sodium(mg))
        lookup = {
            'rice': (130, 2.7, 0.3, 28, 0.4, 0.1, 1),
            'chicken': (239, 27, 14, 0, 0, 0, 82),
            'onion': (40, 1.1, 0.1, 9, 1.7, 4.2, 4),
            'tomato': (18, 0.9, 0.2, 3.9, 1.2, 2.6, 5),
            'garlic': (149, 6.4, 0.5, 33, 2.1, 1, 17),
            'potato': (77, 2, 0.1, 17, 2.2, 0.8, 6),
            'lentil': (116, 9, 0.4, 20, 8, 1.8, 6),
            'dal': (116, 9, 0.4, 20, 8, 1.8, 6),
            'paneer': (265, 18, 20, 6, 0, 0, 20),
            'butter': (717, 0.9, 81, 0.1, 0, 0.1, 11),
            'ghee': (900, 0, 100, 0, 0, 0, 0),
            'oil': (884, 0, 100, 0, 0, 0, 0),
            'yogurt': (59, 10, 0.4, 3.6, 0, 3.2, 36),
            'egg': (155, 13, 11, 1.1, 0, 1.1, 124),
            'salt': (0, 0, 0, 0, 0, 0, 38758),
            'sugar': (387, 0, 0, 100, 0, 100, 1)
        }

        totals = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0}

        def parse_quantity(q):
            try:
                if isinstance(q, (int, float)):
                    return float(q)
                q = str(q).strip()
                # fraction like 1/2
                if '/' in q and not q.replace('/', '').replace('.', '').isdigit():
                    parts = q.split('/')
                    if len(parts) == 2:
                        return float(parts[0]) / float(parts[1])
                return float(re.findall(r'[\d\.]+', q)[0]) if re.findall(r'[\d\.]+', q) else 1.0
            except Exception:
                return 1.0

        for ing in ingredients:
            name = (ing.get('name') or '').lower()
            qty = parse_quantity(ing.get('quantity', '1'))
            # Roughly determine key by checking lookup keys in name
            matched = None
            for key in lookup.keys():
                if key in name:
                    matched = key
                    break
            if not matched:
                # fallback using category
                cat = (ing.get('category') or '').lower()
                if cat in ['grains']:
                    matched = 'rice'
                elif cat in ['poultry', 'meat']:
                    matched = 'chicken'
                elif cat in ['dairy']:
                    matched = 'yogurt'
                else:
                    matched = None

            if matched and matched in lookup:
                per_quantity = lookup[matched]
                # scale totals by qty (very rough)
                totals['calories'] += per_quantity[0] * qty
                totals['protein'] += per_quantity[1] * qty
                totals['fat'] += per_quantity[2] * qty
                totals['carbs'] += per_quantity[3] * qty
                totals['fiber'] += per_quantity[4] * qty
                totals['sugar'] += per_quantity[5] * qty
                totals['sodium'] += per_quantity[6] * qty
            else:
                # unknown ingredient -> small default
                totals['calories'] += 20 * qty
                totals['carbs'] += 3 * qty

        # Round values
        for k in totals:
            if k == 'sodium':
                totals[k] = int(round(totals[k]))
            else:
                totals[k] = round(totals[k], 1)

        return totals
    
    def _basic_ingredient_extraction(self, soup):
        """Basic ingredient extraction fallback when IngredientExtractor is not available (handles Hindi/English)"""
        ingredients = []
        
        # Try to find ingredient lists
        ingredient_selectors = [
            {'itemprop': 'recipeIngredient'},
            {'class': 'recipe-ingredient'},
            {'class': 'ingredients'},
            {'id': 'ingredients'},
            {'class': re.compile(r'ingredient', re.I)}
        ]
        
        for selector in ingredient_selectors:
            elements = soup.find_all(attrs=selector)
            if elements:
                for elem in elements:
                    # Ensure UTF-8 encoding for Hindi text
                    try:
                        text = elem.get_text(separator='\n').strip()
                        text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    except:
                        text = elem.get_text().strip()
                    
                    if text and len(text) > 2:
                        # Try to parse with basic pattern
                        parsed = self._parse_basic_ingredient_line(text)
                        if parsed:
                            ingredients.append(parsed)
                        else:
                            # Fallback: just extract text
                            ingredients.append({
                                'name': text,
                                'quantity': '1',
                                'unit': '',
                                'category': self._categorize_ingredient(text)
                            })
                if ingredients:
                    break
        
        # If no structured list, try lists
        if not ingredients:
            lists = soup.find_all(['ul', 'ol'])
            for ul in lists:  # Check all lists (no limit)
                items = ul.find_all('li')
                for item in items:  # Check all items (no limit)
                    try:
                        text = item.get_text(separator='\n').strip()
                        text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    except:
                        text = item.get_text().strip()
                    
                    if text and len(text) > 2 and len(text) < 200:
                        # Try to parse
                        parsed = self._parse_basic_ingredient_line(text)
                        if parsed:
                            ingredients.append(parsed)
                        else:
                            ingredients.append({
                                'name': text,
                                'quantity': '1',
                                'unit': '',
                                'category': self._categorize_ingredient(text)
                            })
                if ingredients:
                    break
        
        return ingredients  # Return all ingredients (no limit)

    def _parse_bbc_good_food(self, soup, url, dish_name):
        """
        BBC Good Food site-specific parser
        Extracts ingredients and instructions from BBC's standard recipe template
        """
        try:
            # BBC Good Food uses schema.org microdata
            # First try structured data (JSON-LD)
            structured = self._extract_structured_recipe(soup)
            if structured:
                ingredients = self._ingredients_from_structured(structured)
                instructions = self._instructions_from_structured(structured)
                servings = self._extract_servings_from_structured(structured)
                title = structured.get('name', dish_name)
                
                if ingredients and len(ingredients) >= 3:
                    return {
                        'dish_name': title,
                        'ingredients': ingredients,
                        'instructions': instructions or [],
                        'servings': servings or 4,
                        'source_url': url,
                        'source_type': 'web_scraping'
                    }
            
            # Fallback: BBC-specific CSS selectors
            ingredients = []
            for li in soup.find_all('li', {'class': 'recipe-ingredient'}):
                text = li.get_text().strip()
                if text:
                    parsed = self._parse_basic_ingredient_line(text)
                    if parsed:
                        ingredients.append(parsed)
                    else:
                        ingredients.append({
                            'name': text,
                            'quantity': '1',
                            'unit': '',
                            'category': self._categorize_ingredient(text)
                        })
            
            if len(ingredients) < 3:
                return None
            
            # Extract instructions
            instructions = []
            for li in soup.find_all('li', {'class': 'recipe-step'}):
                text = li.get_text().strip()
                if text and len(text) > 10:
                    instructions.append(text)
            
            return {
                'dish_name': dish_name,
                'ingredients': ingredients,
                'instructions': instructions,
                'servings': 4,
                'source_url': url,
                'source_type': 'web_scraping'
            }
        except Exception as e:
            print(f"BBC Good Food parser error: {e}")
            return None

    def _parse_veg_recipes_of_india(self, soup, url, dish_name):
        """
        Veg Recipes of India site-specific parser
        Extracts ingredients and instructions optimized for Indian recipe format
        """
        try:
            # First try JSON-LD structured data
            structured = self._extract_structured_recipe(soup)
            if structured:
                ingredients = self._ingredients_from_structured(structured)
                instructions = self._instructions_from_structured(structured)
                servings = self._extract_servings_from_structured(structured)
                title = structured.get('name', dish_name)
                
                if ingredients and len(ingredients) >= 3:
                    return {
                        'dish_name': title,
                        'ingredients': ingredients,
                        'instructions': instructions or [],
                        'servings': servings or 4,
                        'source_url': url,
                        'source_type': 'web_scraping'
                    }
            
            # Fallback: VRI-specific patterns
            ingredients = []
            
            # Look for ingredient sections (commonly in divs or lists)
            for section in soup.find_all(['div', 'section']):
                section_text = section.get_text().lower()
                if 'ingredient' in section_text:
                    # Extract list items or paragraphs from this section
                    for li in section.find_all(['li', 'p', 'span']):
                        text = li.get_text().strip()
                        # Filter out headers
                        if text and len(text) > 3 and len(text) < 200 and not any(x in text.lower() for x in ['ingredient', 'instruction', 'step']):
                            parsed = self._parse_basic_ingredient_line(text)
                            if parsed:
                                ingredients.append(parsed)
                            elif text and len(text) > 5:
                                ingredients.append({
                                    'name': text,
                                    'quantity': '1',
                                    'unit': '',
                                    'category': self._categorize_ingredient(text)
                                })
                    if len(ingredients) >= 3:
                        break
            
            if len(ingredients) < 3:
                return None
            
            # Extract instructions
            instructions = []
            for section in soup.find_all(['div', 'section', 'ol']):
                section_text = section.get_text().lower()
                if any(x in section_text for x in ['instruction', 'method', 'step', 'procedure']):
                    # Extract ordered list items
                    for li in section.find_all('li'):
                        text = li.get_text().strip()
                        if text and len(text) > 10 and len(text) < 500:
                            instructions.append(text)
                    if instructions:
                        break
            
            return {
                'dish_name': dish_name,
                'ingredients': ingredients,  # Return all ingredients (no limit)
                'instructions': instructions,  # Return all instructions (no limit)
                'servings': 4,
                'source_url': url,
                'source_type': 'web_scraping'
            }
        except Exception as e:
            print(f"Veg Recipes of India parser error: {e}")
            return None

    def _get_cached_recipe(self, dish_name):
        """
        Try to retrieve recipe from MongoDB cache
        Returns recipe dict if found and not expired, else None
        """
        if not self.use_cache or not self.Recipe:
            return None
        
        try:
            recipe_doc = self.Recipe.objects(dish_name=dish_name.lower()).first()
            if recipe_doc:
                # Update access count and timestamp
                recipe_doc.times_accessed += 1
                recipe_doc.updated_at = datetime.utcnow()
                recipe_doc.save()
                
                return recipe_doc.to_dict()
        except Exception as e:
            print(f"Cache retrieval error: {e}")
        
        return None

    
    def _apply_india_localization(self, recipe_data):
        """
        Apply India-centric localization to recipe
        - Converts terminology to Indian style
        - Adds Indian cooking notes and wisdom
        - Determines regional context
        """
        if not recipe_data or not self.india_localizer:
            return recipe_data
        
        try:
            localized = self.india_localizer.localize_recipe(recipe_data)
            return localized
        except Exception as e:
            print(f"Warning: Could not localize recipe to Indian style: {e}")
            return recipe_data
    
    def _cache_recipe(self, dish_name, recipe_data, source_type='web_scraping'):
        """
        Store recipe in MongoDB cache with TTL
        TTL is set via expires_at field (expires after cache_ttl_hours)
        """
        if not self.use_cache or not self.Recipe:
            return
        
        try:
            from models.recipe import IngredientItem
            from datetime import datetime, timedelta
            
            # Prepare ingredients for embedding
            ingredients = []
            for ing in recipe_data.get('ingredients', []):
                ingredients.append(IngredientItem(
                    name=ing.get('name', ''),
                    quantity=str(ing.get('quantity', '1')),
                    unit=ing.get('unit', ''),
                    category=ing.get('category', '')
                ))
            
            # Try to update or create recipe document
            recipe_doc, created = self.Recipe.objects(dish_name=dish_name.lower()).update_one(
                set__source_url=recipe_data.get('source_url', ''),
                set__source_type=source_type,
                set__servings=recipe_data.get('servings', 4),
                set__prep_time=recipe_data.get('prep_time'),
                set__cook_time=recipe_data.get('cook_time'),
                set__total_time=recipe_data.get('total_time'),
                set__ingredients=ingredients,
                set__instructions=recipe_data.get('instructions', []),
                set__summary=recipe_data.get('summary', ''),
                set__title=recipe_data.get('title', ''),
                set__nutrition=recipe_data.get('nutrition'),
                set__updated_at=datetime.utcnow(),
                set__expires_at=self.Recipe.set_ttl_expiry(self.cache_ttl_hours),
                upsert=True
            )
            
            if created:
                print(f"[CACHE] New recipe cached: {dish_name}")
            else:
                print(f"[CACHE] Recipe updated in cache: {dish_name}")
        except Exception as e:
            print(f"Cache storage error: {e}")
            # Continue gracefully even if caching fails

    def _suggest_spelling_correction(self, dish_name):
        """
        Suggest spelling corrections for misspelled dish names using fuzzy matching.
        Common dishes and their misspellings are checked.
        Returns corrected dish name if a good match is found, else returns original.
        """
        # Dictionary of common Indian dishes and their misspellings
        common_dishes = {
            'biryani': ['briyani', 'biriyani', 'biryani', 'biryan', 'biryaan'],
            'pav bhaji': ['pav baji', 'pavbhaji', 'pav bhaji'],
            'paneer': ['panir', 'paneer', 'panir'],
            'butter chicken': ['butter chiken', 'butter chikn'],
            'dal': ['daal', 'dahl', 'dal'],
            'roti': ['roti', 'rotta', 'rotli'],
            'naan': ['nan', 'naan', 'nane'],
            'samosa': ['samosa', 'somosa', 'samoos'],
            'tandoori': ['tanduri', 'tandoori', 'tandoor'],
            'masala': ['masala', 'masla', 'masalah'],
            'curry': ['curry', 'curri', 'kari'],
            'dosa': ['dosa', 'dosha', 'dosai'],
            'idli': ['idli', 'idly', 'idle'],
            'chutney': ['chutney', 'chutni', 'chatni']
        }
        
        input_lower = dish_name.lower().strip()
        
        # Exact match check
        for canonical, variants in common_dishes.items():
            if input_lower in variants:
                return canonical if input_lower != canonical else dish_name
        
        # Fuzzy match check using simple edit distance
        best_match = None
        best_distance = float('inf')
        threshold = 2  # Max edit distance
        
        for canonical, variants in common_dishes.items():
            for variant in variants:
                distance = self._edit_distance(input_lower, variant)
                if distance < best_distance and distance <= threshold:
                    best_distance = distance
                    best_match = canonical
        
        if best_match:
            return best_match
        
        # If no match found, return original
        return dish_name
    
    def _edit_distance(self, s1, s2):
        """
        Calculate Levenshtein edit distance between two strings
        """
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer than s2
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

