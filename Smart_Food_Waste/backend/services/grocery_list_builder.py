"""
Grocery list builder service for aggregating and categorizing ingredients
"""
from collections import defaultdict


class GroceryListBuilder:
    """Service for building organized grocery lists"""
    
    def __init__(self):
        # Category order for display
        self.category_order = [
            'produce', 'meat', 'poultry', 'seafood', 'dairy',
            'grains', 'spices', 'condiments', 'beverages',
            'frozen', 'canned', 'bakery', 'snacks', 'other'
        ]
    
    def build_list(self, ingredients):
        """
        Build organized grocery list from ingredients
        
        Args:
            ingredients: List of ingredient dictionaries
        
        Returns:
            List of organized grocery items
        """
        # Group by ingredient name and category
        ingredient_map = defaultdict(lambda: {
            'quantities': [],
            'units': set(),
            'category': None
        })
        
        for ingredient in ingredients:
            # Handle both dictionary and object
            if hasattr(ingredient, 'name'):
                # It's an object (IngredientItem)
                name = (ingredient.name or '').strip().lower()
                quantity = str(ingredient.quantity or '1')
                unit = (ingredient.unit or '').lower()
                category = ingredient.category or 'other'
            else:
                # It's a dictionary
                name = ingredient.get('name', '').strip().lower()
                quantity = ingredient.get('quantity', '1')
                unit = ingredient.get('unit', '').lower()
                category = ingredient.get('category', 'other')
            
            if not name:
                continue
            
            if name in ingredient_map:
                # Add quantity to existing ingredient
                ingredient_map[name]['quantities'].append(quantity)
                if unit:
                    ingredient_map[name]['units'].add(unit)
            else:
                # New ingredient
                ingredient_map[name]['quantities'] = [quantity]
                ingredient_map[name]['units'] = {unit} if unit else set()
                ingredient_map[name]['category'] = category
        
        # Combine quantities and format
        grocery_items = []
        for name, data in ingredient_map.items():
            # Combine quantities if same unit
            combined_quantity = self._combine_quantities(data['quantities'])
            
            # Determine unit (use first non-empty unit, or empty)
            unit = list(data['units'])[0] if data['units'] else ''
            
            grocery_items.append({
                'ingredient_name': name.title(),  # Capitalize
                'quantity': combined_quantity,
                'unit': unit,
                'category': data['category'] or 'other'
            })
        
        # Sort by category order
        grocery_items.sort(key=lambda x: self._get_category_index(x['category']))
        
        return grocery_items
    
    def _combine_quantities(self, quantities):
        """
        Combine multiple quantity strings
        
        Args:
            quantities: List of quantity strings
        
        Returns:
            Combined quantity string
        """
        if not quantities:
            return '1'
        
        if len(quantities) == 1:
            return quantities[0]
        
        # For now, just return the first quantity
        # In a more sophisticated version, we could add them
        return quantities[0]
    
    def _get_category_index(self, category):
        """Get sort index for category"""
        try:
            return self.category_order.index(category)
        except ValueError:
            return len(self.category_order)  # Put unknown categories at end

