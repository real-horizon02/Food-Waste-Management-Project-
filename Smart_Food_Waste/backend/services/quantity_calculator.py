"""
Quantity calculation service for scaling ingredients based on household size
"""
import re
from fractions import Fraction


class QuantityCalculator:
    """Service for calculating ingredient quantities based on household size"""
    
    def __init__(self):
        # Unit conversion factors (to grams for standardization)
        self.conversion_factors = {
            'cup': {'flour': 120, 'sugar': 200, 'rice': 200, 'default': 240},
            'tbsp': {'default': 15},
            'tsp': {'default': 5},
            'gram': {'default': 1},
            'g': {'default': 1},
            'kg': {'default': 1000},
            'lb': {'default': 453.592},
            'lbs': {'default': 453.592},
            'oz': {'default': 28.3495},
            'ml': {'default': 1},
            'l': {'default': 1000},
            'liter': {'default': 1000}
        }
    
    def scale_ingredients(self, ingredients, recipe_servings, household_size):
        """
        Scale ingredient quantities based on household size
        
        Args:
            ingredients: List of ingredient dictionaries
            recipe_servings: Number of servings the recipe makes
            household_size: Number of people in household
        
        Returns:
            List of scaled ingredient dictionaries
        """
        if recipe_servings <= 0:
            recipe_servings = 4  # Default
        
        if household_size <= 0:
            household_size = 1  # Default
        
        scale_factor = household_size / recipe_servings
        
        scaled_ingredients = []
        
        for ingredient in ingredients:
            scaled_ing = self._scale_ingredient(ingredient, scale_factor)
            scaled_ingredients.append(scaled_ing)
        
        return scaled_ingredients
    
    def _scale_ingredient(self, ingredient, scale_factor):
        """
        Scale a single ingredient
        
        Args:
            ingredient: Ingredient dictionary or IngredientItem object
            scale_factor: Multiplier for scaling
        
        Returns:
            Scaled ingredient dictionary
        """
        # Handle both dictionary and IngredientItem object
        if hasattr(ingredient, 'quantity'):
            # It's an IngredientItem object
            original_quantity = str(ingredient.quantity or '1')
            unit = (ingredient.unit or '').lower()
            name = ingredient.name or ''
            category = ingredient.category or 'other'
        else:
            # It's a dictionary
            original_quantity = str(ingredient.get('quantity', '1'))
            unit = ingredient.get('unit', '').lower()
            name = ingredient.get('name', '')
            category = ingredient.get('category', 'other')
        
        # Parse quantity (handle fractions like "1/2", "1 1/2")
        quantity_value = self._parse_quantity(original_quantity)
        
        # Scale the quantity
        scaled_value = quantity_value * scale_factor
        
        # Format the scaled quantity
        scaled_quantity = self._format_quantity(scaled_value, unit)
        
        return {
            'name': name,
            'quantity': scaled_quantity,
            'unit': unit,
            'category': category
        }
    
    def _parse_quantity(self, quantity_str):
        """
        Parse quantity string to float
        
        Args:
            quantity_str: String like "1", "1/2", "1 1/2", "2.5"
        
        Returns:
            Float value
        """
        if not quantity_str:
            return 1.0
        
        quantity_str = quantity_str.strip()
        
        # Handle mixed fractions like "1 1/2"
        if ' ' in quantity_str and '/' in quantity_str:
            parts = quantity_str.split()
            whole = float(parts[0]) if parts[0] else 0
            fraction = self._parse_fraction(parts[1])
            return whole + fraction
        
        # Handle simple fractions like "1/2"
        if '/' in quantity_str:
            return self._parse_fraction(quantity_str)
        
        # Handle decimal numbers
        try:
            return float(quantity_str)
        except ValueError:
            return 1.0
    
    def _parse_fraction(self, fraction_str):
        """Parse fraction string to float"""
        try:
            parts = fraction_str.split('/')
            if len(parts) == 2:
                numerator = float(parts[0])
                denominator = float(parts[1])
                if denominator != 0:
                    return numerator / denominator
        except (ValueError, IndexError):
            pass
        return 1.0
    
    def _format_quantity(self, value, unit):
        """
        Format quantity value to readable string
        
        Args:
            value: Numeric quantity value
            unit: Unit of measurement
        
        Returns:
            Formatted quantity string
        """
        # Round to reasonable precision
        if value >= 1:
            # For values >= 1, round to 1 decimal place
            rounded = round(value, 1)
            if rounded == int(rounded):
                return str(int(rounded))
            return str(rounded)
        else:
            # For values < 1, convert to fraction
            return self._decimal_to_fraction(value)
    
    def _decimal_to_fraction(self, decimal):
        """Convert decimal to fraction string"""
        # Common fractions
        common_fractions = {
            0.125: '1/8',
            0.25: '1/4',
            0.33: '1/3',
            0.5: '1/2',
            0.67: '2/3',
            0.75: '3/4'
        }
        
        # Check if close to common fraction
        for dec, frac in common_fractions.items():
            if abs(decimal - dec) < 0.05:
                return frac
        
        # Try to convert using Fraction
        try:
            frac = Fraction(decimal).limit_denominator(8)
            if frac.numerator == 1 and frac.denominator <= 8:
                return f"{frac.numerator}/{frac.denominator}"
        except:
            pass
        
        # Fallback to rounded decimal
        return str(round(decimal, 2))

