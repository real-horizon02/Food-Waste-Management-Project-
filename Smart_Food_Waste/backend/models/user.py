"""
User model for MongoDB
"""
from datetime import datetime
from mongoengine import Document, StringField, EmailField, DateTimeField, ListField, DictField, BooleanField
from werkzeug.security import generate_password_hash, check_password_hash


class User(Document):
    """User model for authentication and preferences"""
    username = StringField(required=True, unique=True, max_length=50)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    
    # User preferences
    household_size = StringField(default='1')  # Store as string for flexibility
    dietary_restrictions = ListField(StringField(), default=list)  # e.g., ['vegetarian', 'vegan', 'gluten-free']
    preferred_stores = ListField(StringField(), default=list)
    
    # Favorite dishes for quick reuse
    favorite_dishes = ListField(StringField(), default=list)
    
    # User type: household, restaurant, grocery_shop
    user_type = StringField(default='household', choices=['household', 'restaurant', 'grocery_shop'])
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)
    
    meta = {
        'collection': 'users',
        'indexes': ['username', 'email']
    }
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'household_size': self.household_size,
            'dietary_restrictions': self.dietary_restrictions,
            'preferred_stores': self.preferred_stores,
            'favorite_dishes': self.favorite_dishes,
            'user_type': self.user_type,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


