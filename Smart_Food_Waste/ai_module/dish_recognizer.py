"""
Dish name recognition and normalization
"""
import re
from ai_module.nlp_processor import NLPProcessor


class DishRecognizer:
    """Service for recognizing and normalizing dish names"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
        
        # Common dish name patterns
        self.dish_patterns = {
            'curry': ['curry', 'kari', 'kadhi'],
            'rice': ['rice', 'biryani', 'pulao', 'fried rice'],
            'soup': ['soup', 'stew', 'broth'],
            'salad': ['salad', 'raita'],
            'bread': ['bread', 'roti', 'naan', 'chapati', 'paratha']
        }
    
    def normalize_dish_name(self, dish_name):
        """
        Normalize dish name for searching
        
        Args:
            dish_name: Raw dish name input
        
        Returns:
            Normalized dish name
        """
        if not dish_name:
            return ''
        
        # Normalize text
        normalized = self.nlp.normalize_text(dish_name)
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(recipe|how to make|how to cook)\s+', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s+(recipe|dish)$', '', normalized, flags=re.IGNORECASE)
        
        # Capitalize first letter of each word
        normalized = ' '.join(word.capitalize() for word in normalized.split())
        
        return normalized
    
    def find_similar_dishes(self, dish_name):
        """
        Find similar dishes based on keywords
        
        Args:
            dish_name: Dish name to find similar dishes for
        
        Returns:
            List of similar dish names
        """
        normalized = self.normalize_dish_name(dish_name)
        keywords = self.nlp.extract_keywords(normalized)
        
        similar = []
        for keyword in keywords:
            for pattern, variations in self.dish_patterns.items():
                if keyword in variations:
                    similar.extend(variations)
        
        # Remove duplicates and original
        similar = list(set(similar))
        if normalized.lower() in similar:
            similar.remove(normalized.lower())
        
        return similar[:5]  # Return top 5

