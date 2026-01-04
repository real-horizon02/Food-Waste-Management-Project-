"""
Seed database with sample data
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

from mongoengine import connect

# Import models
try:
    from backend.models.ingredient import Ingredient
except ImportError:
    sys.path.insert(0, backend_dir)
    from models.ingredient import Ingredient


def seed_ingredients():
    """Seed common ingredients"""
    print("Seeding ingredients...")
    
    common_ingredients = [
        {
            'name': 'Tomato',
            'normalized_name': 'tomato',
            'synonyms': ['tomatoes'],
            'category': 'produce',
            'common_units': ['pieces', 'cups', 'grams']
        },
        {
            'name': 'Onion',
            'normalized_name': 'onion',
            'synonyms': ['onions'],
            'category': 'produce',
            'common_units': ['pieces', 'cups', 'grams']
        },
        {
            'name': 'Garlic',
            'normalized_name': 'garlic',
            'synonyms': ['garlic cloves'],
            'category': 'spices',
            'common_units': ['cloves', 'tbsp']
        },
        {
            'name': 'Flour',
            'normalized_name': 'flour',
            'synonyms': ['all-purpose flour', 'wheat flour'],
            'category': 'grains',
            'common_units': ['cups', 'grams', 'kg']
        },
        {
            'name': 'Rice',
            'normalized_name': 'rice',
            'synonyms': ['basmati rice', 'white rice'],
            'category': 'grains',
            'common_units': ['cups', 'grams', 'kg']
        },
        {
            'name': 'Milk',
            'normalized_name': 'milk',
            'synonyms': ['whole milk', 'cow milk'],
            'category': 'dairy',
            'common_units': ['cups', 'ml', 'l']
        },
        {
            'name': 'Butter',
            'normalized_name': 'butter',
            'synonyms': ['unsalted butter'],
            'category': 'dairy',
            'common_units': ['tbsp', 'cups', 'grams']
        },
        {
            'name': 'Chicken',
            'normalized_name': 'chicken',
            'synonyms': ['chicken breast', 'chicken thighs'],
            'category': 'poultry',
            'common_units': ['grams', 'kg', 'lbs', 'pieces']
        },
        {
            'name': 'Salt',
            'normalized_name': 'salt',
            'synonyms': ['table salt', 'sea salt'],
            'category': 'spices',
            'common_units': ['tsp', 'tbsp']
        },
        {
            'name': 'Pepper',
            'normalized_name': 'pepper',
            'synonyms': ['black pepper'],
            'category': 'spices',
            'common_units': ['tsp', 'tbsp']
        }
    ]
    
    for ing_data in common_ingredients:
        ingredient = Ingredient.objects(normalized_name=ing_data['normalized_name']).first()
        if not ingredient:
            ingredient = Ingredient(**ing_data)
            ingredient.save()
            print(f"  ✓ Created ingredient: {ing_data['name']}")
        else:
            print(f"  - Ingredient already exists: {ing_data['name']}")
    
    print("✓ Ingredients seeding complete!\n")


if __name__ == '__main__':
    # Get MongoDB URI
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_waste_db')
    
    print("="*60)
    print("Seeding Database")
    print("="*60)
    print(f"\nConnecting to MongoDB...")
    
    try:
        connect(host=mongo_uri, serverSelectionTimeoutMS=5000)
        print("✓ Connected!\n")
    except Exception as e:
        print(f"\n❌ Failed to connect to MongoDB!")
        print(f"Error: {str(e)}")
        print("\nMake sure MongoDB is running and MONGO_URI is correct in backend/.env")
        sys.exit(1)
    
    seed_ingredients()
    
    print("Database seeding complete!")

