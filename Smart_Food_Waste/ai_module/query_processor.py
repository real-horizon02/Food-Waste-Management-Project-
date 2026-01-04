"""
Query processing for Google Search API
"""
import re
from ai_module.nlp_processor import NLPProcessor


class QueryProcessor:
    """Service for processing search queries"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
    
    def build_search_query(self, dish_name):
        """
        Build optimized search query for Google Search API
        
        Args:
            dish_name: Dish name
        
        Returns:
            Optimized search query string
        """
        # Normalize dish name
        normalized = self.nlp.normalize_text(dish_name)
        
        # Add recipe keywords
        query = f"{normalized} recipe ingredients"
        
        return query
    
    def extract_dish_from_query(self, query):
        """
        Extract dish name from search query
        
        Args:
            query: Search query string
        
        Returns:
            Extracted dish name
        """
        # Remove common recipe-related words
        query = re.sub(r'\b(recipe|how to|ingredients|steps|instructions)\b', '', query, flags=re.IGNORECASE)
        
        # Normalize
        normalized = self.nlp.normalize_text(query)
        
        # Capitalize
        dish_name = ' '.join(word.capitalize() for word in normalized.split())
        
        return dish_name

