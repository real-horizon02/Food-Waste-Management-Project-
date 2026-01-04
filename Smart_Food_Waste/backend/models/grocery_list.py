"""
Grocery List model for MongoDB
"""
from datetime import datetime
from mongoengine import Document, StringField, ListField, DictField, DateTimeField, EmbeddedDocument, EmbeddedDocumentField, ReferenceField


class GroceryItem(EmbeddedDocument):
    """Embedded document for grocery list items"""
    ingredient_name = StringField(required=True)
    quantity = StringField(required=True)
    unit = StringField()
    category = StringField()
    checked = StringField(default='false')  # Track if item is purchased


class GroceryList(Document):
    """Grocery List model for storing user grocery lists"""
    user_id = StringField(required=True)  # Reference to user
    dish_name = StringField(required=True)
    household_size = StringField(required=True)
    
    # Grocery items
    items = ListField(EmbeddedDocumentField(GroceryItem), default=list)
    
    # List metadata
    is_favorite = StringField(default='false')
    notes = StringField()
    
    # Output formats
    pdf_url = StringField()  # URL to generated PDF
    csv_data = DictField()  # CSV data if needed
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'grocery_lists',
        'indexes': ['user_id', 'dish_name', 'created_at']
    }
    
    def to_dict(self):
        """Convert grocery list to dictionary"""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'dish_name': self.dish_name,
            'household_size': self.household_size,
            'items': [
                {
                    'ingredient_name': item.ingredient_name,
                    'quantity': item.quantity,
                    'unit': item.unit,
                    'category': item.category,
                    'checked': item.checked
                }
                for item in self.items
            ],
            'is_favorite': self.is_favorite,
            'notes': self.notes,
            'pdf_url': self.pdf_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


