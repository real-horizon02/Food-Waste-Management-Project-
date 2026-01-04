"""
Initialize MongoDB database and collections
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
    from backend.models.user import User
    from backend.models.dish import Dish
    from backend.models.recipe import Recipe
    from backend.models.ingredient import Ingredient
    from backend.models.grocery_list import GroceryList
except ImportError:
    # Try relative imports
    sys.path.insert(0, backend_dir)
    from models.user import User
    from models.dish import Dish
    from models.recipe import Recipe
    from models.ingredient import Ingredient
    from models.grocery_list import GroceryList


def init_database():
    """Initialize database connection and create indexes"""
    # Get MongoDB URI
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_waste_db')
    
    print("="*60)
    print("MongoDB Database Initialization")
    print("="*60)
    print(f"\nConnecting to MongoDB...")
    print(f"URI: {mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri}")
    
    try:
        connect(host=mongo_uri, serverSelectionTimeoutMS=5000)
        print("✓ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"\n❌ Failed to connect to MongoDB!")
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB service is running")
        print("2. Check MONGO_URI in backend/.env file")
        print("3. Test connection: python database/setup_mongodb.py")
        sys.exit(1)
    
    # Create indexes for better performance
    print("Creating indexes...")
    
    # User indexes
    User.ensure_indexes()
    print("✓ User indexes created")
    
    # Dish indexes
    Dish.ensure_indexes()
    print("✓ Dish indexes created")
    
    # Recipe indexes
    Recipe.ensure_indexes()
    print("✓ Recipe indexes created")
    
    # Ingredient indexes
    Ingredient.ensure_indexes()
    print("✓ Ingredient indexes created")
    
    # Grocery list indexes
    GroceryList.ensure_indexes()
    print("✓ Grocery list indexes created")
    
    print("\nDatabase initialization complete!")


if __name__ == '__main__':
    init_database()

