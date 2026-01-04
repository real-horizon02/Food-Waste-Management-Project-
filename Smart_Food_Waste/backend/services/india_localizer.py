"""
India-Centric Recipe Localization Module
Converts international recipes to Indian cooking style, terminology, and preferences
Ensures all instructions, language, and guidance follow Indian culinary conventions
"""

import re
from typing import List, Dict, Optional


class IndiaCentricLocalizer:
    """
    Localizes recipes to Indian cooking style and terminology
    - Converts measurements to Indian standards
    - Replaces international terms with Indian equivalents
    - Adds Indian cooking techniques and wisdom
    - Ensures all instructions use Indian context
    """
    
    def __init__(self):
        # International term → Indian equivalent mapping
        self.ingredient_mapping = {
            # Oils & Fats
            'vegetable oil': 'tel / oil',
            'cooking oil': 'tel / oil',
            'olive oil': 'olive tel (though mustard oil is traditional)',
            'canola oil': 'sunflower or groundnut tel',
            'butter': 'makhan / ghee',
            'ghee': 'ghee / clarified butter',
            'coconut oil': 'nariyal tel',
            
            # Dairy
            'cream': 'malai',
            'sour cream': 'dahi (yogurt)',
            'yogurt': 'dahi',
            'milk': 'doodh',
            'paneer': 'paneer',
            'cheese': 'paneer or chhena',
            
            # Grains & Flour
            'all-purpose flour': 'maida',
            'whole wheat flour': 'atta',
            'rice flour': 'chawal ka atta',
            'cornstarch': 'cornflour',
            'semolina': 'suji / rava',
            'rice': 'chawal',
            'lentils': 'dal',
            'chickpeas': 'chane',
            
            # Spices (most already Indian)
            'turmeric': 'haldi',
            'cumin': 'jeera',
            'coriander': 'dhania',
            'mustard seeds': 'rai / sarson ke beej',
            'fenugreek': 'methi',
            'ginger': 'adrak',
            'garlic': 'lehsun',
            'green chili': 'hari mirch',
            'red chili': 'lal mirch',
            'chili powder': 'mirch powder',
            'garam masala': 'garam masala',
            'asafoetida': 'hing / asafoetida',
            'black pepper': 'kali mirch',
            
            # Vegetables
            'potato': 'aloo',
            'onion': 'pyaaz',
            'tomato': 'tamatar',
            'eggplant': 'baingan',
            'cauliflower': 'phool gobhi',
            'peas': 'matar',
            'carrot': 'gajjar',
            'spinach': 'palak',
            'bell pepper': 'shimla mirch',
            'cucumber': 'kheera',
            'okra': 'bhindi',
            'zucchini': 'zucchini (courgette)',
            'mushroom': 'khumbhi',
            
            # Proteins
            'chicken': 'murgh / chicken',
            'mutton': 'gosht (lamb/goat)',
            'fish': 'machhli',
            'shrimp': 'jhinga',
            'lentil': 'dal',
            'beans': 'beans / phasliyaan',
            'chickpea': 'chana',
            
            # Other
            'salt': 'namak',
            'sugar': 'shakkar / cheeni',
            'honey': 'shahad',
            'lemon': 'nimbu',
            'lime': 'kala nimbu',
            'coconut': 'nariyal',
            'tamarind': 'imli',
            'jaggery': 'gur',
        }
        
        # Cooking technique translations
        self.technique_mapping = {
            'fry': 'talna / fry in tal (oil)',
            'deep fry': 'tel mein talna',
            'shallow fry': 'halka talna',
            'sauté': 'pan mein talna',
            'stir fry': 'jhatpat talna',
            'boil': 'ubalna',
            'simmer': 'dhimi aach par pakana',
            'slow cook': 'dhime se pakana',
            'roast': 'bhunna',
            'grill': 'grill par pakana',
            'steam': 'bhap mein pakana',
            'bake': 'oven mein pakana',
            'toast': 'talna',
            'temper': 'tadka lagana',
            'season': 'swad ke anusar namak-mirch dalna',
            'blanch': 'ubalta pani mein dalna',
            'marinate': 'marinaid mein rakna',
            'knead': 'maida gundna',
            'roll': 'bel kar fashaana',
            'flatten': 'samtal karna',
            'chop': 'kharabhna',
            'slice': 'kaatna',
            'dice': 'boro-boro kaatna',
            'grate': 'rale se kaatna',
            'mince': 'barun kar dalna',
            'blend': 'mixer mein silbhana',
        }
        
        # Measurement conversions
        self.measurement_mapping = {
            'cup': '200ml / 1 cup',
            'tablespoon': '15ml / 1 tbsp',
            'teaspoon': '5ml / 1 tsp',
            'ounce': 'ounce / 28g',
            'pound': 'pound / 500g',
            'gram': 'gram',
            'milliliter': 'ml',
            'liter': 'liter',
        }
        
        # Cooking heat levels in Indian context
        self.heat_mapping = {
            'low': 'dhimi aach (slow flame)',
            'low-medium': 'dhimi-madhyam aach',
            'medium': 'madhyam aach (medium flame)',
            'medium-high': 'madhyam-tej aach',
            'high': 'tej aach (high flame)',
            'very high': 'bahut tej aach (very high flame)',
        }
        
        # Time descriptions with Indian context
        self.time_mapping = {
            'few minutes': 'kuch minit',
            'several minutes': 'kayi minut',
            '5 minutes': '5 minit',
            '10 minutes': '10 minit',
            '15 minutes': 'ek char (quarter hour)',
            '30 minutes': 'aadha ghanta',
            '1 hour': 'ek ghanta',
            '2 hours': 'do ghante',
            'overnight': 'raat bhar',
            'until golden': 'jab tak sunehra na ho jaye',
            'until tender': 'jab tak naram na ho jaye',
            'until cooked': 'jab tak pakna na ho jaye',
        }
        
        # Indian cooking wisdom and tips
        self.indian_wisdom = [
            "Use ghee or mustard oil for authentic flavor - these are traditional in Indian cooking",
            "Temper the dal with hot oil and spices (tadka) at the end for best taste",
            "Cook with curry leaves and mustard seeds in hot oil for classic Indian aroma",
            "Always save some of the cooked dish to use for next day's preparation - this is traditional",
            "Use kasuri methi (dried fenugreek leaves) for authentic Indian taste",
            "Roast spices lightly before grinding for more intense flavor - this is Indian tradition",
            "Cook with patience - slow cooking brings out true flavors in Indian cuisine",
            "Use Indian homemade masalas when possible - shop-bought may lack freshness",
            "Always finish Indian curries by tempering with oil, spices, and curry leaves",
            "Indian cooking emphasizes balance of flavors - sweet, salty, sour, spicy",
            "Rest the dough for at least 30 minutes - Indian baking needs proper hydration",
            "Use stone mill for grinding spices when possible - maintains authentic taste",
            "Cook with seasonal vegetables - this is how traditional Indian cooking works",
            "Save the first oil that comes out of grinding for final tempering",
            "Always taste and adjust seasoning - Indian cooking is about balance",
        ]
        
        # Regional preferences (India-centric)
        self.regional_notes = {
            'north_india': 'North Indian style: Rich, creamy gravies with tandoori techniques',
            'south_india': 'South Indian style: Coconut-based, rice-centric, uses curry leaves prominently',
            'east_india': 'East Indian style: Mustard oil dominant, uses Bengal spices',
            'west_india': 'West Indian style: Peanut and coconut based, simpler preparations',
            'maharashtra': 'Maharashtrian: Simple, oil-based with groundnuts and peanuts',
            'bengal': 'Bengali: Uses mustard and poppy seeds extensively',
            'kerala': 'Keralan: Coconut milk rich, fish and seafood prominent',
            'rajasthan': 'Rajasthani: Spice-heavy, uses ghee liberally',
        }
    
    def localize_recipe(self, recipe_data: Dict) -> Dict:
        """
        Localize entire recipe to Indian context
        
        Args:
            recipe_data: Dictionary with title, ingredients, instructions, etc.
        
        Returns:
            Localized recipe data with Indian terminology and context
        """
        localized = dict(recipe_data)
        
        # Localize ingredients
        if 'ingredients' in recipe_data:
            localized['ingredients'] = self._localize_ingredients(recipe_data['ingredients'])
        
        # Localize instructions
        if 'instructions' in recipe_data:
            localized['instructions'] = self._localize_instructions(recipe_data['instructions'])
        
        # Localize title
        if 'title' in recipe_data:
            localized['title'] = self._localize_title(recipe_data['title'])
        
        # Add Indian cooking notes
        localized['indian_notes'] = self._generate_indian_notes(recipe_data)
        
        # Add regional context
        localized['regional_context'] = self._determine_regional_context(recipe_data)
        
        return localized
    
    def _localize_ingredients(self, ingredients: List[Dict]) -> List[Dict]:
        """Convert ingredient names to Indian terminology"""
        localized = []
        
        for ing in ingredients:
            localized_ing = dict(ing)
            name = ing.get('name', '').lower()
            
            # Check for direct mapping
            for intl_term, indian_term in self.ingredient_mapping.items():
                if intl_term in name:
                    localized_ing['name_indian'] = name.replace(intl_term, indian_term)
                    localized_ing['name_original'] = ing.get('name', '')
                    break
            
            # Add measurement in both systems
            if 'unit' in ing:
                unit = ing['unit'].lower()
                for intl_unit, conversions in self.measurement_mapping.items():
                    if intl_unit in unit:
                        localized_ing['unit_indian'] = conversions
                        break
            
            localized.append(localized_ing)
        
        return localized
    
    def _localize_instructions(self, instructions: List[str]) -> List[str]:
        """Convert cooking instructions to Indian style"""
        localized = []
        
        for instruction in instructions:
            localized_instr = instruction
            
            # Replace cooking techniques
            for intl_term, indian_term in self.technique_mapping.items():
                pattern = r'\b' + intl_term + r'\b'
                localized_instr = re.sub(pattern, indian_term, localized_instr, flags=re.IGNORECASE)
            
            # Replace heat levels
            for heat_level, indian_heat in self.heat_mapping.items():
                pattern = r'\b' + heat_level + r'\b'
                localized_instr = re.sub(pattern, indian_heat, localized_instr, flags=re.IGNORECASE)
            
            # Replace ingredients
            for intl_term, indian_term in self.ingredient_mapping.items():
                pattern = r'\b' + intl_term + r'\b'
                localized_instr = re.sub(pattern, f'{intl_term} ({indian_term})', localized_instr, flags=re.IGNORECASE)
            
            localized.append(localized_instr)
        
        return localized
    
    def _localize_title(self, title: str) -> str:
        """Add Indian context to recipe title"""
        title_lower = title.lower()
        
        # Add Indian prefix if it's an Indian dish
        indian_dishes = [
            'biryani', 'curry', 'dal', 'samosa', 'paneer', 'kheer', 'gulab jamun',
            'naan', 'roti', 'tandoori', 'masala', 'tikka', 'kebab', 'pulao'
        ]
        
        for indian_dish in indian_dishes:
            if indian_dish in title_lower:
                return f"Traditional Indian {title}" if 'Indian' not in title else title
        
        return title
    
    def _generate_indian_notes(self, recipe_data: Dict) -> List[str]:
        """Generate context-specific Indian cooking notes"""
        notes = []
        
        # Identify recipe type
        title = recipe_data.get('title', '').lower()
        
        if any(x in title for x in ['dal', 'lentil', 'bean']):
            notes.append("Tip: Always temper the dal with hot oil, mustard seeds, and curry leaves before serving")
            notes.append("Traditional: Serve with warm rice or roti for complete meal")
        
        if any(x in title for x in ['curry', 'gravy']):
            notes.append("Tip: Cook curry on slow heat to develop flavors - this is key to authentic taste")
            notes.append("Technique: Remove oil layer (ghee) that forms on top for presentation")
        
        if any(x in title for x in ['bread', 'roti', 'naan', 'paratha']):
            notes.append("Indian tip: Let dough rest for 30 minutes - this is essential for proper texture")
            notes.append("Technique: Cook on high heat until puffed (phal bana)")
        
        if any(x in title for x in ['dessert', 'kheer', 'gulab', 'halwa']):
            notes.append("Traditional: Made during Indian festivals - use full-fat milk for richness")
            notes.append("Flavor: Add cardamom and rose petals for authentic Indian dessert taste")
        
        if any(x in title for x in ['rice', 'biryani', 'pulao']):
            notes.append("Technique: Rice should be 'dum pukht' (slow-cooked) for best flavor")
            notes.append("Indian style: Each grain should be separate - this indicates proper cooking")
        
        # Add random wisdom
        if not notes:
            notes.append("Indian cooking tip: " + self.indian_wisdom[0])
        
        notes.append("Serving: In Indian tradition, serve hot with accompaniments like pickle, yogurt, or chutney")
        
        return notes
    
    def _determine_regional_context(self, recipe_data: Dict) -> Dict:
        """Determine which Indian region this recipe belongs to"""
        context = {
            'region': 'Pan-Indian',
            'description': 'Recipe can be prepared in any Indian household',
            'notes': []
        }
        
        title = recipe_data.get('title', '').lower()
        ingredients_str = ' '.join([i.get('name', '').lower() for i in recipe_data.get('ingredients', [])])
        
        # South India detection
        if any(x in title + ingredients_str for x in ['coconut', 'curry leaves', 'tamarind', 'south', 'kerala', 'tamil', 'andhra']):
            context['region'] = 'South Indian'
            context['description'] = self.regional_notes['south_india']
            context['notes'].append("Use fresh curry leaves and grated coconut")
            context['notes'].append("Tamarind adds characteristic sour flavor")
        
        # North India detection
        if any(x in title + ingredients_str for x in ['tandoori', 'mughlai', 'paneer', 'north', 'delhi', 'punjab', 'lucknow']):
            context['region'] = 'North Indian'
            context['description'] = self.regional_notes['north_india']
            context['notes'].append("Use ghee liberally for rich flavor")
            context['notes'].append("Tandoori style: cook in high heat for char marks")
        
        # East India detection
        if any(x in title + ingredients_str for x in ['bengal', 'mustard', 'poppy seeds', 'east', 'bengali']):
            context['region'] = 'East Indian'
            context['description'] = self.regional_notes['bengal']
            context['notes'].append("Use mustard oil for authentic flavor")
            context['notes'].append("Temper with mustard and cumin seeds")
        
        # West India detection
        if any(x in title + ingredients_str for x in ['maharashtra', 'peanut', 'groundnut', 'west', 'gujrat']):
            context['region'] = 'West Indian'
            context['description'] = self.regional_notes.get('maharashtra', 'West Indian style')
            context['notes'].append("Peanuts and groundnuts add nutty flavor")
            context['notes'].append("Simpler spice profile - focus on basic flavors")
        
        return context
    
    def get_cooking_wisdom(self) -> str:
        """Return random Indian cooking wisdom"""
        import random
        return random.choice(self.indian_wisdom)
    
    def convert_international_to_indian_style(self, recipe_data: Dict) -> Dict:
        """
        Transform an international recipe to Indian cooking style
        - Suggests Indian spice additions
        - Recommends Indian cooking techniques
        - Adjusts ingredients to Indian pantry
        """
        adapted = dict(recipe_data)
        suggestions = []
        
        # Suggest Indian spices that could enhance
        title = recipe_data.get('title', '').lower()
        
        if any(x in title for x in ['vegetable', 'curry', 'stew', 'braise']):
            suggestions.append("Add Indian spices: 1 tsp mustard seeds, 1 tsp cumin, a pinch of asafoetida")
            suggestions.append("Temper in hot oil before adding other ingredients")
        
        if any(x in title for x in ['cream', 'sauce', 'gravy']):
            suggestions.append("Use Indian cream/malai instead of regular cream")
            suggestions.append("Add turmeric and coriander for warmth")
        
        if any(x in title for x in ['bread', 'dough']):
            suggestions.append("Use Indian whole wheat flour (atta) for better taste")
            suggestions.append("Add salt and yogurt for authentic texture")
        
        adapted['indian_adaptation_suggestions'] = suggestions
        
        return adapted


# Singleton instance
india_localizer = IndiaCentricLocalizer()
