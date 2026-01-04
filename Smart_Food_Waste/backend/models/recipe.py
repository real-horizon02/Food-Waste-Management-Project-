"""
Recipe model for MongoDB
"""
from datetime import datetime, timedelta
from mongoengine import Document, StringField, ListField, DictField, IntField, DateTimeField, EmbeddedDocument, EmbeddedDocumentField


class IngredientItem(EmbeddedDocument):
    """Embedded document for recipe ingredients"""
    name = StringField(required=True)
    quantity = StringField(required=True)  # Store as string to handle fractions
    unit = StringField()  # e.g., 'cups', 'grams', 'tbsp'
    category = StringField()  # e.g., 'produce', 'dairy', 'meat'


class Recipe(Document):
    """Recipe model for storing recipe information with TTL caching"""
    dish_name = StringField(required=True, max_length=200, unique_with='source_type')
    source_url = StringField()  # URL where recipe was fetched from
    source_type = StringField(choices=['google_search', 'spoonacular', 'web_scraping', 'hardcoded', 'manual'], default='web_scraping')
    
    # Recipe details
    servings = IntField(default=4)
    prep_time = IntField()  # in minutes
    cook_time = IntField()  # in minutes
    total_time = IntField()  # in minutes
    
    # Ingredients
    ingredients = ListField(EmbeddedDocumentField(IngredientItem), default=list)
    
    # Instructions (stored as list of strings)
    instructions = ListField(StringField(), default=list)
    
    # NLP processed fields
    summary = StringField()  # Recipe summary from NLP processing
    title = StringField()  # Recipe title from NLP processing
    
    # Nutrition information
    nutrition = DictField()  # Nutrition data: calories, protein, fat, carbs, etc.
    
    # Raw recipe data (for debugging/reprocessing)
    raw_data = DictField()
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    times_accessed = IntField(default=0)
    expires_at = DateTimeField()  # TTL field: set to now + cache duration
    
    meta = {
        'collection': 'recipes',
        'indexes': [
            'dish_name',
            'source_url',
            'expires_at'  # TTL index will be managed by MongoDB
        ]
    }
    
    def to_dict(self, optimized=False):
        """
        Convert recipe to dictionary
        
        Args:
            optimized: If True, only returns essential fields for frontend display (faster)
                      If False, returns all fields for completeness
        """
        result = {
            'id': str(self.id),
            'dish_name': self.dish_name,
            'title': self.title or self.dish_name,  # Always include title for display
            'servings': self.servings,
            'ingredients': [
                {
                    'name': ing.name,
                    'quantity': ing.quantity,
                    'unit': ing.unit,
                    'category': ing.category
                }
                for ing in self.ingredients
            ],
            'instructions': self.instructions,
        }
        
        if optimized:
            # Optimized response: only essential fields
            # Skip: source_type, source_url, prep_time, cook_time, total_time, created_at, times_accessed
            # Include: nutrition if available, summary if available
            if self.nutrition:
                result['nutrition'] = self.nutrition
            if self.summary:
                result['summary'] = self.summary
            return result
        
        # Full response: all fields for backward compatibility
        result.update({
            'source_url': self.source_url,
            'source_type': self.source_type,
            'prep_time': self.prep_time,
            'cook_time': self.cook_time,
            'total_time': self.total_time,
            'created_at': self.created_at.isoformat(),
            'times_accessed': self.times_accessed
        })
        
        # Add NLP fields if available
        if self.summary:
            result['summary'] = self.summary
        
        # Add nutrition data if available
        if self.nutrition:
            result['nutrition'] = self.nutrition
        
        return result

    @staticmethod
    def set_ttl_expiry(duration_hours=24):
        """Helper to set TTL expiry time (default 24 hours)"""
        return datetime.utcnow() + timedelta(hours=duration_hours)


