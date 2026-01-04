"""
Ingredient model for MongoDB
"""
from datetime import datetime
from mongoengine import Document, StringField, ListField, DateTimeField


class Ingredient(Document):
    """Ingredient model for storing ingredient information and synonyms"""
    name = StringField(required=True, unique=True, max_length=100)
    normalized_name = StringField(required=True)  # Normalized version for matching
    
    # Synonyms and variations
    synonyms = ListField(StringField(), default=list)
    
    # Category classification
    category = StringField(required=True, choices=[
        'produce', 'dairy', 'meat', 'seafood', 'poultry',
        'grains', 'spices', 'condiments', 'beverages',
        'frozen', 'canned', 'bakery', 'snacks', 'other'
    ])
    
    # Common units for this ingredient
    common_units = ListField(StringField(), default=list)  # e.g., ['cups', 'grams', 'lbs']
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'ingredients',
        'indexes': ['name', 'normalized_name', 'category']
    }
    
    def to_dict(self):
        """Convert ingredient to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'normalized_name': self.normalized_name,
            'synonyms': self.synonyms,
            'category': self.category,
            'common_units': self.common_units,
            'created_at': self.created_at.isoformat()
        }


