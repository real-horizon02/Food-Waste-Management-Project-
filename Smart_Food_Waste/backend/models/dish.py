"""
Dish model for MongoDB
"""
from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, ListField, DictField, IntField


class Dish(Document):
    """Dish model for storing dish information"""
    name = StringField(required=True, max_length=200)
    normalized_name = StringField(required=True)  # Normalized version for searching
    aliases = ListField(StringField(), default=list)  # Alternative names
    
    # Recipe information
    recipe_id = StringField()  # Reference to recipe
    servings = IntField(default=4)  # Default servings
    
    # Metadata
    cuisine_type = StringField()  # e.g., 'Indian', 'Italian', 'Chinese'
    difficulty = StringField(choices=['easy', 'medium', 'hard'], default='medium')
    prep_time = IntField()  # in minutes
    cook_time = IntField()  # in minutes
    
    # Usage statistics
    times_used = IntField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dishes',
        'indexes': ['name', 'normalized_name']
    }
    
    def to_dict(self):
        """Convert dish to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'normalized_name': self.normalized_name,
            'aliases': self.aliases,
            'recipe_id': self.recipe_id,
            'servings': self.servings,
            'cuisine_type': self.cuisine_type,
            'difficulty': self.difficulty,
            'prep_time': self.prep_time,
            'cook_time': self.cook_time,
            'times_used': self.times_used,
            'created_at': self.created_at.isoformat()
        }


