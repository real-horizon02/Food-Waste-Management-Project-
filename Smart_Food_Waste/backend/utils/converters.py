"""
Unit conversion utilities
"""
from fractions import Fraction


def convert_unit(value, from_unit, to_unit, ingredient_name=''):
    """
    Convert between units
    
    Args:
        value: Numeric value to convert
        from_unit: Source unit
        to_unit: Target unit
        ingredient_name: Name of ingredient (for context-specific conversions)
    
    Returns:
        Converted value
    """
    # Common conversions
    conversions = {
        # Volume
        ('cup', 'ml'): 240,
        ('cup', 'tbsp'): 16,
        ('tbsp', 'tsp'): 3,
        ('tbsp', 'ml'): 15,
        ('tsp', 'ml'): 5,
        
        # Weight
        ('lb', 'g'): 453.592,
        ('lb', 'kg'): 0.453592,
        ('oz', 'g'): 28.3495,
        ('kg', 'g'): 1000,
        
        # Length (for some ingredients)
        ('inch', 'cm'): 2.54
    }
    
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    
    if from_unit == to_unit:
        return value
    
    # Direct conversion
    if (from_unit, to_unit) in conversions:
        return value * conversions[(from_unit, to_unit)]
    
    # Reverse conversion
    if (to_unit, from_unit) in conversions:
        return value / conversions[(to_unit, from_unit)]
    
    # Return original value if conversion not found
    return value


def normalize_unit(unit):
    """
    Normalize unit name (handle variations)
    
    Args:
        unit: Unit string
    
    Returns:
        Normalized unit string
    """
    if not unit:
        return ''
    
    unit = unit.lower().strip()
    
    # Mapping of variations to standard names
    unit_map = {
        'tablespoon': 'tbsp',
        'tablespoons': 'tbsp',
        'teaspoon': 'tsp',
        'teaspoons': 'tsp',
        'cup': 'cup',
        'cups': 'cup',
        'gram': 'g',
        'grams': 'g',
        'kilogram': 'kg',
        'kilograms': 'kg',
        'pound': 'lb',
        'pounds': 'lb',
        'ounce': 'oz',
        'ounces': 'oz',
        'milliliter': 'ml',
        'milliliters': 'ml',
        'liter': 'l',
        'liters': 'l'
    }
    
    return unit_map.get(unit, unit)

