"""
Ingredient extraction service using NLP and regex
"""
import re
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.ingredient import Ingredient
except ImportError:
    try:
        from backend.models.ingredient import Ingredient
    except ImportError:
        Ingredient = None  # Optional import


class IngredientExtractor:
    """Service for extracting ingredients from recipe text"""
    
    def __init__(self):
        # Enhanced ingredient patterns - handles Hindi/English, fractions, decimals
        # Pattern: quantity (number/fraction) + optional unit + ingredient name
        self.quantity_pattern = re.compile(
            r'(?P<quantity>(?:\d+\s+\d+/\d+)|(?:\d+/\d+)|(?:\d+\.\d+)|(?:\d+))\s*'
            r'(?P<unit>[a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)?\s*'
            r'(?P<name>.+)',
            re.IGNORECASE | re.UNICODE
        )
        
        # Alternative pattern for Hindi/English mixed: "2 कप आटा" or "2 cups flour"
        self.alt_pattern = re.compile(
            r'(?P<quantity>(?:\d+\s+\d+/\d+)|(?:\d+/\d+)|(?:\d+\.\d+)|(?:\d+))\s+'
            r'(?P<name>.+)',
            re.IGNORECASE | re.UNICODE
        )
        
        # Common units (English and Hindi)
        self.units = [
            # English units
            'cup', 'cups', 'tbsp', 'tablespoon', 'tablespoons', 'tbs',
            'tsp', 'teaspoon', 'teaspoons', 'gram', 'grams', 'g', 'gm',
            'kg', 'kilogram', 'kilograms', 'lb', 'lbs', 'pound', 'pounds',
            'oz', 'ounce', 'ounces', 'ml', 'milliliter', 'milliliters', 'millilitre',
            'l', 'liter', 'liters', 'litre', 'litres', 'piece', 'pieces', 
            'clove', 'cloves', 'bunch', 'bunches', 'can', 'cans', 
            'package', 'packages', 'packet', 'packets',
            # Hindi units (transliterated and actual)
            'कप', 'कप्स', 'चम्मच', 'चमच', 'टेबलस्पून', 'टीस्पून',
            'ग्राम', 'किलो', 'किलोग्राम', 'लीटर', 'मिलीलीटर',
            'टुकड़ा', 'टुकड़े', 'लहसुन', 'कली', 'गांठ', 'गांठें'
        ]
        
        # Hindi unit mappings (Hindi -> English)
        self.hindi_unit_map = {
            'कप': 'cup', 'कप्स': 'cups', 'चम्मच': 'tsp', 'चमच': 'tsp',
            'टेबलस्पून': 'tbsp', 'टीस्पून': 'tsp', 'ग्राम': 'g', 'ग्राम्स': 'g',
            'किलो': 'kg', 'किलोग्राम': 'kg', 'लीटर': 'l', 'मिलीलीटर': 'ml',
            'टुकड़ा': 'piece', 'टुकड़े': 'pieces', 'कली': 'clove', 'कलियां': 'cloves',
            'गांठ': 'piece', 'गांठें': 'pieces'
        }
    
    def extract_from_html(self, soup):
        """
        Extract ingredients from HTML soup
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of ingredient dictionaries
        """
        ingredients = []
        seen = set()
        
        # Try to find structured ingredient lists
        ingredient_selectors = [
            {'itemprop': 'recipeIngredient'},
            {'class': 'recipe-ingredient'},
            {'class': 'ingredients'},
            {'class': 'ingredient'},
            {'id': 'ingredients'},
            {'class': 'ingredient-list'}
        ]
        
        for selector in ingredient_selectors:
            elements = soup.find_all(attrs=selector)
            if elements:
                for elem in elements:
                    text_block = elem.get_text(separator='\n')
                    for candidate in self._split_candidate_lines(text_block):
                        ingredient = self._parse_ingredient_text(candidate)
                        if ingredient:
                            key = (ingredient['name'].lower(), ingredient['quantity'], ingredient['unit'])
                            if key not in seen:
                                seen.add(key)
                                ingredients.append(ingredient)
                if ingredients:
                    break
        
        # If no structured list found, try to find lists
        if not ingredients:
            lists = soup.find_all(['ul', 'ol'])
            for ul in lists:
                items = ul.find_all('li')
                for item in items:
                    text_block = item.get_text(separator='\n')
                    for candidate in self._split_candidate_lines(text_block):
                        ingredient = self._parse_ingredient_text(candidate)
                        if ingredient:
                            key = (ingredient['name'].lower(), ingredient['quantity'], ingredient['unit'])
                            if key not in seen:
                                seen.add(key)
                                ingredients.append(ingredient)
                if ingredients:
                    break
        
        # If still no ingredients, try to extract from paragraphs
        if not ingredients:
            paragraphs = soup.find_all('p')
            for p in paragraphs[:20]:  # Limit search
                text = p.get_text().lower()
                if 'ingredient' in text or 'recipe' in text:
                    # Try to extract from this paragraph
                    for candidate in self._split_candidate_lines(p.get_text(separator='\n')):
                        ingredient = self._parse_ingredient_text(candidate)
                        if ingredient:
                            key = (ingredient['name'].lower(), ingredient['quantity'], ingredient['unit'])
                            if key not in seen:
                                seen.add(key)
                                ingredients.append(ingredient)
        
        return ingredients[:50]  # Limit to 50 ingredients

    def extract_from_lines(self, lines):
        """
        Extract structured ingredients from a list of raw ingredient strings.
        """
        if not lines:
            return []

        ingredients = []
        seen = set()
        for line in lines:
            for candidate in self._split_candidate_lines(line):
                ingredient = self._parse_ingredient_text(candidate)
                if ingredient:
                    key = (ingredient['name'].lower(), ingredient['quantity'], ingredient['unit'])
                    if key not in seen:
                        seen.add(key)
                        ingredients.append(ingredient)
        return ingredients[:50]
    
    def _parse_ingredient_text(self, text):
        """
        Parse ingredient text into structured format (handles Hindi/English)
        
        Args:
            text: Raw ingredient text (e.g., "2 cups flour" or "2 कप आटा")
        
        Returns:
            Dictionary with name, quantity, unit, category or None
        """
        if not text:
            return None
        
        # Clean text - handle UTF-8 encoding issues
        try:
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            pass
        
        text = text.replace('\xa0', ' ').replace('\u200b', '').strip()
        # Remove bullet points and special characters
        text = re.sub(r'^[\u2022\u2023\u25CF\u25CB\u25A0\-\*\·\•\u0964]+\s*', '', text, flags=re.UNICODE)
        text = re.sub(r'^\d+[\.\)]\s*', '', text)  # Remove numbered lists

        # Ignore obviously bad candidates
        if not text or len(text.strip()) < 2:
            return None
        if len(text) > 200:  # Increased limit for Hindi text
            return None
        
        # Try to match quantity pattern (with unit)
        match = self.quantity_pattern.match(text)
        
        if match:
            quantity = match.group('quantity').strip()
            unit = match.group('unit').strip() if match.group('unit') else ''
            ingredient_name = match.group('name').strip()
            
            # Convert Hindi units to English
            if unit:
                unit_lower = unit.lower()
                # Check if it's a Hindi unit
                if unit_lower in self.hindi_unit_map:
                    unit = self.hindi_unit_map[unit_lower]
                elif unit_lower not in [u.lower() for u in self.units]:
                    # Unit might be part of ingredient name, try to extract it
                    # Check if first word of ingredient_name is actually a unit
                    name_parts = ingredient_name.split()
                    if name_parts and name_parts[0].lower() in [u.lower() for u in self.units]:
                        unit = name_parts[0].lower()
                        ingredient_name = ' '.join(name_parts[1:])
                    elif name_parts and name_parts[0] in self.hindi_unit_map:
                        unit = self.hindi_unit_map[name_parts[0]]
                        ingredient_name = ' '.join(name_parts[1:])
                    else:
                        # Unit not recognized, keep it with ingredient name
                        ingredient_name = f"{unit} {ingredient_name}".strip()
                        unit = ''
            
            # Convert quantity fractions to decimals for better handling
            quantity = self._normalize_quantity(quantity)
            
            # Clean up ingredient name
            ingredient_name = self._clean_ingredient_name(ingredient_name)
            
            if not ingredient_name or len(ingredient_name) < 2:
                return None
            
            # Convert unit to Indian units
            if unit:
                unit, _ = self._convert_to_indian_unit(unit)
            
            # Determine category
            category = self._categorize_ingredient(ingredient_name)
            
            return {
                'name': ingredient_name,
                'quantity': quantity,
                'unit': unit,
                'category': category
            }
        else:
            # Try alternative pattern (quantity + name, no unit)
            alt_match = self.alt_pattern.match(text)
            if alt_match:
                quantity = alt_match.group('quantity').strip()
                ingredient_name = alt_match.group('name').strip()
                
                # Try to extract unit from ingredient name
                name_parts = ingredient_name.split()
                unit = ''
                if name_parts:
                    first_word = name_parts[0].lower()
                    if first_word in [u.lower() for u in self.units]:
                        unit = first_word
                        ingredient_name = ' '.join(name_parts[1:])
                    elif first_word in self.hindi_unit_map:
                        unit = self.hindi_unit_map[first_word]
                        ingredient_name = ' '.join(name_parts[1:])
                
                quantity = self._normalize_quantity(quantity)
                ingredient_name = self._clean_ingredient_name(ingredient_name)
                
                if not ingredient_name or len(ingredient_name) < 2:
                    return None
                
                if unit:
                    unit, _ = self._convert_to_indian_unit(unit)
                
                return {
                    'name': ingredient_name,
                    'quantity': quantity,
                    'unit': unit,
                    'category': self._categorize_ingredient(ingredient_name)
                }
            else:
                # No quantity found, treat entire text as ingredient name
                ingredient_name = self._clean_ingredient_name(text)
                
                if len(ingredient_name) < 2:
                    return None
                
                return {
                    'name': ingredient_name,
                    'quantity': '1',
                    'unit': '',
                    'category': self._categorize_ingredient(ingredient_name)
                }
    
    def _normalize_quantity(self, quantity):
        """Normalize quantity string (handle fractions)"""
        quantity = quantity.strip()
        
        # Handle mixed numbers: "1 1/2" -> "1.5"
        mixed_match = re.match(r'(\d+)\s+(\d+)/(\d+)', quantity)
        if mixed_match:
            whole = int(mixed_match.group(1))
            num = int(mixed_match.group(2))
            den = int(mixed_match.group(3))
            return str(whole + (num / den))
        
        # Handle fractions: "1/2" -> "0.5"
        frac_match = re.match(r'(\d+)/(\d+)', quantity)
        if frac_match:
            num = int(frac_match.group(1))
            den = int(frac_match.group(2))
            return str(num / den)
        
        return quantity
    
    def _convert_to_indian_unit(self, unit):
        """Convert unit to Indian standard units"""
        unit_lower = unit.lower()
        
        # Weight conversions
        if unit_lower in ['oz', 'ounce', 'ounces']:
            return 'g', 28.35  # Will be converted in recipe_service
        elif unit_lower in ['lb', 'lbs', 'pound', 'pounds']:
            return 'g', 453.59
        elif unit_lower in ['g', 'gram', 'grams', 'gm', 'ग्राम']:
            return 'g', 1
        elif unit_lower in ['kg', 'kilogram', 'kilograms', 'किलो', 'किलोग्राम']:
            return 'kg', 1
        
        # Volume conversions
        elif unit_lower in ['fl oz', 'fluid ounce', 'fluid ounces']:
            return 'ml', 29.57
        elif unit_lower in ['cup', 'cups', 'कप', 'कप्स']:
            return 'cup', 1
        elif unit_lower in ['tbsp', 'tablespoon', 'tablespoons', 'टेबलस्पून']:
            return 'tbsp', 1
        elif unit_lower in ['tsp', 'teaspoon', 'teaspoons', 'चम्मच', 'चमच', 'टीस्पून']:
            return 'tsp', 1
        elif unit_lower in ['ml', 'milliliter', 'milliliters', 'मिलीलीटर']:
            return 'ml', 1
        elif unit_lower in ['l', 'liter', 'liters', 'litre', 'litres', 'लीटर']:
            return 'l', 1
        
        # Keep as is
        return unit, 1
    
    def _clean_ingredient_name(self, name):
        """Clean and normalize ingredient name (handles Hindi/English)"""
        if not name:
            return ''
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common prefixes/suffixes (English and Hindi)
        name = re.sub(r'^(a|an|some|the|एक|कुछ)\s+', '', name, flags=re.IGNORECASE | re.UNICODE)
        name = re.sub(r'\s+(to taste|as needed|optional|स्वादानुसार|आवश्यकतानुसार)$', '', name, flags=re.IGNORECASE | re.UNICODE)
        
        # Don't force capitalization for Hindi text (preserve original)
        # Only capitalize if it's all English
        if name and re.match(r'^[a-zA-Z\s]+$', name):
            name = name[0].upper() + name[1:].lower()
        
        return name.strip()

    def _split_candidate_lines(self, text):
        """
        Break a block of text into likely ingredient lines.
        """
        if not text:
            return []

        candidates = []
        if isinstance(text, str):
            # Split on newlines and separators like commas when used as bullet
            fragments = re.split(r'[\n\r]+|(?<!\d),(?!\d)', text)
            for fragment in fragments:
                piece = fragment.strip()
                if piece:
                    candidates.append(piece)
        else:
            candidates.append(str(text))
        return candidates
    
    def _categorize_ingredient(self, name):
        """Categorize ingredient based on name (handles Hindi/English)"""
        name_lower = name.lower()
        
        # Indian spices and seasonings (Hindi + English)
        spice_keywords = [
            'turmeric', 'haldi', 'हल्दी', 'cumin', 'jeera', 'जीरा',
            'coriander', 'dhania', 'धनिया', 'cardamom', 'elaichi', 'इलाइची',
            'cinnamon', 'dalchini', 'दालचीनी', 'clove', 'laung', 'लौंग',
            'pepper', 'kali mirch', 'काली मिर्च', 'red chili', 'lal mirch', 'लाल मिर्च',
            'garam masala', 'गरम मसाला', 'curry powder', 'masala', 'मसाला',
            'spice', 'spices', 'salt', 'namak', 'नमक', 'hing', 'हींग',
            'mustard', 'rai', 'राई', 'fenugreek', 'methi', 'मेथी'
        ]
        if any(keyword in name_lower for keyword in spice_keywords):
            return 'spices'
        
        # Produce (including Indian vegetables)
        produce_keywords = [
            'tomato', 'tamatar', 'टमाटर', 'onion', 'pyaz', 'प्याज',
            'garlic', 'lehsun', 'लहसुन', 'potato', 'aloo', 'आलू',
            'carrot', 'gajar', 'गाजर', 'pepper', 'mirch', 'मिर्च',
            'cucumber', 'kheera', 'खीरा', 'spinach', 'palak', 'पालक',
            'cauliflower', 'gobi', 'गोभी', 'broccoli', 'brinjal', 'baingan', 'बैंगन',
            'okra', 'bhindi', 'भिंडी', 'cabbage', 'patta gobi', 'पत्ता गोभी',
            'lettuce', 'celery', 'mushroom', 'button mushroom'
        ]
        if any(keyword in name_lower for keyword in produce_keywords):
            return 'produce'
        
        # Dairy (including Indian dairy products)
        dairy_keywords = [
            'milk', 'doodh', 'दूध', 'cheese', 'paneer', 'पनीर',
            'butter', 'makhan', 'मक्खन', 'cream', 'malai', 'मलाई',
            'yogurt', 'curd', 'dahi', 'दही', 'yoghurt', 'ghee', 'घी'
        ]
        if any(keyword in name_lower for keyword in dairy_keywords):
            return 'dairy'
        
        # Meat
        meat_keywords = ['beef', 'pork', 'lamb', 'mutton', 'steak', 'ground beef', 'ground pork']
        if any(keyword in name_lower for keyword in meat_keywords):
            return 'meat'
        
        # Poultry
        poultry_keywords = ['chicken', 'murg', 'मुर्ग', 'turkey', 'duck']
        if any(keyword in name_lower for keyword in poultry_keywords):
            return 'poultry'
        
        # Seafood
        seafood_keywords = [
            'fish', 'machli', 'मछली', 'salmon', 'shrimp', 'prawn', 'jhinga', 'झींगा',
            'crab', 'lobster', 'tuna', 'cod'
        ]
        if any(keyword in name_lower for keyword in seafood_keywords):
            return 'seafood'
        
        # Grains and pulses (important for Indian cooking)
        grain_keywords = [
            'rice', 'chawal', 'चावल', 'pasta', 'noodles', 'flour', 'atta', 'आटा', 'maida', 'मैदा',
            'bread', 'roti', 'रोटी', 'chapati', 'चपाती', 'wheat', 'gehun', 'गेहूं', 'quinoa',
            'dal', 'दाल', 'lentil', 'chana', 'चना', 'rajma', 'राजमा', 'moong', 'मूंग',
            'urad', 'उड़द', 'toor', 'तूर', 'besan', 'बेसन'
        ]
        if any(keyword in name_lower for keyword in grain_keywords):
            return 'grains'
        
        # Default
        return 'other'

