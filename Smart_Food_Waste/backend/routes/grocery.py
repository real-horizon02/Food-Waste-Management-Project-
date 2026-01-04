"""
Grocery list routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.grocery_list import GroceryList, GroceryItem
    from models.recipe import Recipe
    from config import Config
    from services.grocery_list_builder import GroceryListBuilder
    from services.quantity_calculator import QuantityCalculator
    from services.pdf_generator import PDFGenerator
except ImportError:
    try:
        from backend.models.grocery_list import GroceryList, GroceryItem
        from backend.models.recipe import Recipe
        from backend.config import Config
        from backend.services.grocery_list_builder import GroceryListBuilder
        from backend.services.quantity_calculator import QuantityCalculator
        from backend.services.pdf_generator import PDFGenerator
    except ImportError as e:
        print(f"Import error: {e}")
        GroceryList = None
        GroceryItem = None
        Recipe = None
        Config = None
        GroceryListBuilder = None
        QuantityCalculator = None
        PDFGenerator = None

bp = Blueprint('grocery', __name__)

# MongoDB connection is handled in app.py - no need to connect here

# Initialize services
if GroceryListBuilder and QuantityCalculator and PDFGenerator:
    grocery_builder = GroceryListBuilder()
    quantity_calculator = QuantityCalculator()
    pdf_generator = PDFGenerator()
else:
    print("Error: Could not import required services for grocery routes")


@bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_grocery_list():
    """Generate grocery list from dish name and household size"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        dish_name = data.get('dish_name', '').strip()
        household_size = data.get('household_size', '').strip()
        recipe_id = data.get('recipe_id', '')
        
        if not dish_name:
            return jsonify({'error': 'Dish name is required'}), 400
        
        if not household_size:
            return jsonify({'error': 'Household size is required'}), 400
        
        # Get recipe
        if recipe_id:
            recipe = Recipe.objects(id=recipe_id).first()
        else:
            # Try to find recipe by dish name
            recipe = Recipe.objects(dish_name=dish_name).first()
        
        if not recipe:
            return jsonify({'error': 'Recipe not found. Please search for the dish first.'}), 404
        
        # Calculate scaled quantities
        scaled_ingredients = quantity_calculator.scale_ingredients(
            recipe.ingredients,
            recipe.servings,
            int(household_size)
        )
        
        # Build grocery list
        grocery_items = grocery_builder.build_list(scaled_ingredients)
        
        # Create grocery list document
        grocery_list = GroceryList(
            user_id=user_id,
            dish_name=dish_name,
            household_size=household_size,
            items=[GroceryItem(**item) for item in grocery_items]
        )
        grocery_list.save()
        
        # Generate PDF
        pdf_url = pdf_generator.generate_pdf(grocery_list)
        grocery_list.pdf_url = pdf_url
        grocery_list.save()
        
        return jsonify({
            'message': 'Grocery list generated successfully',
            'grocery_list': grocery_list.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists', methods=['GET'])
@jwt_required()
def get_user_lists():
    """Get all grocery lists for current user"""
    try:
        user_id = get_jwt_identity()
        
        lists = GroceryList.objects(user_id=user_id).order_by('-created_at')
        
        return jsonify({
            'grocery_lists': [grocery_list.to_dict() for grocery_list in lists]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists/<list_id>', methods=['GET'])
@jwt_required()
def get_grocery_list(list_id):
    """Get specific grocery list by ID"""
    try:
        user_id = get_jwt_identity()
        
        grocery_list = GroceryList.objects(id=list_id, user_id=user_id).first()
        
        if not grocery_list:
            return jsonify({'error': 'Grocery list not found'}), 404
        
        return jsonify(grocery_list.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists/<list_id>', methods=['PUT'])
@jwt_required()
def update_grocery_list(list_id):
    """Update grocery list (mark items as checked, add notes, etc.)"""
    try:
        user_id = get_jwt_identity()
        
        grocery_list = GroceryList.objects(id=list_id, user_id=user_id).first()
        
        if not grocery_list:
            return jsonify({'error': 'Grocery list not found'}), 404
        
        data = request.get_json()
        
        # Update items
        if 'items' in data:
            grocery_list.items = [GroceryItem(**item) for item in data['items']]
        
        # Update notes
        if 'notes' in data:
            grocery_list.notes = data['notes']
        
        # Update favorite status
        if 'is_favorite' in data:
            grocery_list.is_favorite = data['is_favorite']
        
        grocery_list.save()
        
        return jsonify({
            'message': 'Grocery list updated successfully',
            'grocery_list': grocery_list.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists/<list_id>', methods=['DELETE'])
@jwt_required()
def delete_grocery_list(list_id):
    """Delete grocery list"""
    try:
        user_id = get_jwt_identity()
        
        grocery_list = GroceryList.objects(id=list_id, user_id=user_id).first()
        
        if not grocery_list:
            return jsonify({'error': 'Grocery list not found'}), 404
        
        grocery_list.delete()
        
        return jsonify({'message': 'Grocery list deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists/<list_id>/download/pdf', methods=['GET'])
@jwt_required()
def download_pdf(list_id):
    """Download grocery list as PDF"""
    try:
        user_id = get_jwt_identity()
        
        grocery_list = GroceryList.objects(id=list_id, user_id=user_id).first()
        
        if not grocery_list:
            return jsonify({'error': 'Grocery list not found'}), 404
        
        # Generate PDF if not exists
        if not grocery_list.pdf_url:
            pdf_url = pdf_generator.generate_pdf(grocery_list)
            grocery_list.pdf_url = pdf_url
            grocery_list.save()
        
        return jsonify({'pdf_url': grocery_list.pdf_url}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/lists/<list_id>/download/csv', methods=['GET'])
@jwt_required()
def download_csv(list_id):
    """Download grocery list as CSV"""
    try:
        user_id = get_jwt_identity()
        
        grocery_list = GroceryList.objects(id=list_id, user_id=user_id).first()
        
        if not grocery_list:
            return jsonify({'error': 'Grocery list not found'}), 404
        
        # Generate CSV data
        csv_data = []
        for item in grocery_list.items:
            csv_data.append({
                'ingredient': item.ingredient_name,
                'quantity': item.quantity,
                'unit': item.unit or '',
                'category': item.category or ''
            })
        
        return jsonify({
            'csv_data': csv_data,
            'dish_name': grocery_list.dish_name,
            'household_size': grocery_list.household_size
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

