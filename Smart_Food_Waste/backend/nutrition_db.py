"""
Comprehensive nutrition database for common Indian and global ingredients.
Provides nutrition data per standard unit (100g, 1 cup, 1 tbsp, etc.)
"""

import re
from typing import Dict, Optional, Tuple

# USDA FoodData Central and Indian nutrition databases
# Values are per 100g unless otherwise specified
INGREDIENT_DB = {
    # Grains & Cereals
    'rice': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28, 'fiber': 0.4, 'sodium': 2},
    'wheat': {'calories': 364, 'protein': 13.2, 'fat': 2.5, 'carbs': 71, 'fiber': 10.7, 'sodium': 2},
    'flour': {'calories': 364, 'protein': 10, 'fat': 1.0, 'carbs': 76, 'fiber': 2.7, 'sodium': 2},
    'oats': {'calories': 389, 'protein': 16.9, 'fat': 6.9, 'carbs': 66.3, 'fiber': 10.6, 'sodium': 30},
    'bread': {'calories': 265, 'protein': 9, 'fat': 3.3, 'carbs': 49, 'fiber': 2.7, 'sodium': 490},
    'pasta': {'calories': 131, 'protein': 5, 'fat': 1.1, 'carbs': 25, 'fiber': 1.8, 'sodium': 6},
    'dal': {'calories': 353, 'protein': 24.63, 'fat': 0.38, 'carbs': 63.35, 'fiber': 15.5, 'sodium': 3},
    'lentil': {'calories': 116, 'protein': 9.02, 'fat': 0.38, 'carbs': 20.13, 'fiber': 1.8, 'sodium': 2},
    'chickpea': {'calories': 164, 'protein': 8.86, 'fat': 2.59, 'carbs': 27.42, 'fiber': 6.4, 'sodium': 7},
    
    # Proteins
    'chicken': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0, 'fiber': 0, 'sodium': 74},
    'chicken breast': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0, 'fiber': 0, 'sodium': 74},
    'beef': {'calories': 250, 'protein': 26, 'fat': 15, 'carbs': 0, 'fiber': 0, 'sodium': 75},
    'mutton': {'calories': 294, 'protein': 25, 'fat': 21, 'carbs': 0, 'fiber': 0, 'sodium': 67},
    'fish': {'calories': 96, 'protein': 20, 'fat': 0.9, 'carbs': 0, 'fiber': 0, 'sodium': 47},
    'salmon': {'calories': 206, 'protein': 20, 'fat': 13, 'carbs': 0, 'fiber': 0, 'sodium': 59},
    'tuna': {'calories': 132, 'protein': 29.9, 'fat': 1.3, 'carbs': 0, 'fiber': 0, 'sodium': 41},
    'egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1, 'fiber': 0, 'sodium': 124},
    'paneer': {'calories': 321, 'protein': 25.2, 'fat': 25, 'carbs': 1.2, 'fiber': 0, 'sodium': 245},
    'milk': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 5, 'fiber': 0, 'sodium': 44},
    'yogurt': {'calories': 59, 'protein': 10, 'fat': 0.4, 'carbs': 3.3, 'fiber': 0, 'sodium': 86},
    'curd': {'calories': 59, 'protein': 10, 'fat': 0.4, 'carbs': 3.3, 'fiber': 0, 'sodium': 86},
    
    # Vegetables
    'tomato': {'calories': 18, 'protein': 0.88, 'fat': 0.2, 'carbs': 3.89, 'fiber': 1.2, 'sodium': 5},
    'onion': {'calories': 40, 'protein': 1.1, 'fat': 0.1, 'carbs': 9, 'fiber': 1.7, 'sodium': 4},
    'garlic': {'calories': 149, 'protein': 6.39, 'fat': 0.5, 'carbs': 33.06, 'fiber': 2.1, 'sodium': 17},
    'ginger': {'calories': 80, 'protein': 1.82, 'fat': 0.75, 'carbs': 17.77, 'fiber': 2.4, 'sodium': 13},
    'carrot': {'calories': 41, 'protein': 0.93, 'fat': 0.24, 'carbs': 9.58, 'fiber': 2.8, 'sodium': 69},
    'potato': {'calories': 77, 'protein': 2.1, 'fat': 0.1, 'carbs': 17, 'fiber': 2.1, 'sodium': 6},
    'spinach': {'calories': 23, 'protein': 2.86, 'fat': 0.39, 'carbs': 3.63, 'fiber': 2.2, 'sodium': 79},
    'broccoli': {'calories': 34, 'protein': 2.82, 'fat': 0.37, 'carbs': 6.64, 'fiber': 2.4, 'sodium': 64},
    'cabbage': {'calories': 25, 'protein': 1.28, 'fat': 0.1, 'carbs': 5.8, 'fiber': 2.3, 'sodium': 16},
    'peas': {'calories': 81, 'protein': 5.4, 'fat': 0.4, 'carbs': 14.5, 'fiber': 2.8, 'sodium': 2},
    'beans': {'calories': 31, 'protein': 1.83, 'fat': 0.13, 'carbs': 7.13, 'fiber': 2.7, 'sodium': 3},
    'capsicum': {'calories': 31, 'protein': 1, 'fat': 0.3, 'carbs': 6, 'fiber': 2, 'sodium': 3},
    'bell pepper': {'calories': 31, 'protein': 1, 'fat': 0.3, 'carbs': 6, 'fiber': 2, 'sodium': 3},
    'cucumber': {'calories': 16, 'protein': 0.65, 'fat': 0.11, 'carbs': 3.63, 'fiber': 0.5, 'sodium': 2},
    'eggplant': {'calories': 25, 'protein': 0.98, 'fat': 0.19, 'carbs': 5.88, 'fiber': 3, 'sodium': 2},
    'mushroom': {'calories': 22, 'protein': 3.07, 'fat': 0.34, 'carbs': 3.26, 'fiber': 1, 'sodium': 5},
    'cauliflower': {'calories': 25, 'protein': 1.92, 'fat': 0.28, 'carbs': 4.97, 'fiber': 2.4, 'sodium': 30},
    'radish': {'calories': 16, 'protein': 0.68, 'fat': 0.1, 'carbs': 3.4, 'fiber': 1.6, 'sodium': 39},
    'beetroot': {'calories': 43, 'protein': 1.61, 'fat': 0.17, 'carbs': 9.56, 'fiber': 2.8, 'sodium': 78},
    'corn': {'calories': 86, 'protein': 3.27, 'fat': 1.35, 'carbs': 19.02, 'fiber': 2.7, 'sodium': 15},
    
    # Fruits
    'apple': {'calories': 52, 'protein': 0.26, 'fat': 0.17, 'carbs': 13.81, 'fiber': 2.4, 'sodium': 1},
    'banana': {'calories': 89, 'protein': 1.09, 'fat': 0.33, 'carbs': 22.84, 'fiber': 2.6, 'sodium': 1},
    'mango': {'calories': 60, 'protein': 0.82, 'fat': 0.38, 'carbs': 15, 'fiber': 1.6, 'sodium': 2},
    'orange': {'calories': 47, 'protein': 0.94, 'fat': 0.12, 'carbs': 11.75, 'fiber': 2.4, 'sodium': 1},
    'lemon': {'calories': 29, 'protein': 1.1, 'fat': 0.3, 'carbs': 9.3, 'fiber': 2.8, 'sodium': 1},
    'lime': {'calories': 30, 'protein': 0.7, 'fat': 0.2, 'carbs': 11, 'fiber': 2.8, 'sodium': 2},
    'coconut': {'calories': 354, 'protein': 3.33, 'fat': 33.5, 'carbs': 15.23, 'fiber': 9, 'sodium': 20},
    'coconut milk': {'calories': 230, 'protein': 2.3, 'fat': 23.8, 'carbs': 5.5, 'fiber': 0.4, 'sodium': 16},
    'watermelon': {'calories': 30, 'protein': 0.61, 'fat': 0.15, 'carbs': 7.55, 'fiber': 0.4, 'sodium': 1},
    'strawberry': {'calories': 32, 'protein': 0.67, 'fat': 0.3, 'carbs': 7.68, 'fiber': 2, 'sodium': 2},
    'guava': {'calories': 68, 'protein': 2.55, 'fat': 0.95, 'carbs': 14.32, 'fiber': 5.4, 'sodium': 2},
    'papaya': {'calories': 43, 'protein': 0.61, 'fat': 0.33, 'carbs': 10.82, 'fiber': 1.7, 'sodium': 8},
    'pineapple': {'calories': 50, 'protein': 0.54, 'fat': 0.12, 'carbs': 13.12, 'fiber': 1.4, 'sodium': 1},
    'pomegranate': {'calories': 83, 'protein': 1.67, 'fat': 1.17, 'carbs': 18.7, 'fiber': 4, 'sodium': 3},
    
    # Oils & Fats
    'oil': {'calories': 884, 'protein': 0, 'fat': 100, 'carbs': 0, 'fiber': 0, 'sodium': 0},
    'ghee': {'calories': 882, 'protein': 0.28, 'fat': 99.5, 'carbs': 0, 'fiber': 0, 'sodium': 5},
    'butter': {'calories': 717, 'protein': 0.85, 'fat': 81.11, 'carbs': 0.06, 'fiber': 0, 'sodium': 714},
    'coconut oil': {'calories': 892, 'protein': 0, 'fat': 99.1, 'carbs': 0, 'fiber': 0, 'sodium': 0},
    'olive oil': {'calories': 884, 'protein': 0, 'fat': 100, 'carbs': 0, 'fiber': 0, 'sodium': 2},
    'mustard oil': {'calories': 884, 'protein': 0, 'fat': 100, 'carbs': 0, 'fiber': 0, 'sodium': 0},
    
    # Spices & Seasonings
    'salt': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0, 'sodium': 38758},
    'chili powder': {'calories': 318, 'protein': 14.3, 'fat': 17.3, 'carbs': 56.6, 'fiber': 27.4, 'sodium': 67},
    'turmeric': {'calories': 312, 'protein': 9.68, 'fat': 3.25, 'carbs': 67.14, 'fiber': 21, 'sodium': 38},
    'cumin': {'calories': 375, 'protein': 17.81, 'fat': 22.27, 'carbs': 34.77, 'fiber': 10.2, 'sodium': 168},
    'coriander': {'calories': 298, 'protein': 12.37, 'fat': 17.77, 'carbs': 52.44, 'fiber': 41.5, 'sodium': 35},
    'pepper': {'calories': 251, 'protein': 10.39, 'fat': 3.29, 'carbs': 64.81, 'fiber': 25.3, 'sodium': 20},
    'mustard': {'calories': 508, 'protein': 26.08, 'fat': 36.24, 'carbs': 22.76, 'fiber': 7.9, 'sodium': 1086},
    'fenugreek': {'calories': 323, 'protein': 23.08, 'fat': 6.41, 'carbs': 58.35, 'fiber': 24.6, 'sodium': 67},
    
    # Condiments & Sauces
    'soy sauce': {'calories': 53, 'protein': 8.14, 'fat': 0.64, 'carbs': 4.9, 'fiber': 0, 'sodium': 5586},
    'vinegar': {'calories': 18, 'protein': 0.04, 'fat': 0.04, 'carbs': 0.9, 'fiber': 0, 'sodium': 5},
    'honey': {'calories': 304, 'protein': 0.3, 'fat': 0, 'carbs': 82.4, 'fiber': 0.2, 'sodium': 4},
    'sugar': {'calories': 387, 'protein': 0, 'fat': 0, 'carbs': 100, 'fiber': 0, 'sodium': 2},
    'jaggery': {'calories': 383, 'protein': 0.4, 'fat': 0.3, 'carbs': 98.8, 'fiber': 0, 'sodium': 30},
    
    # Nuts & Seeds
    'almond': {'calories': 579, 'protein': 21.15, 'fat': 49.93, 'carbs': 21.55, 'fiber': 12.5, 'sodium': 1},
    'peanut': {'calories': 567, 'protein': 25.8, 'fat': 49.24, 'carbs': 16.13, 'fiber': 9.3, 'sodium': 7},
    'walnut': {'calories': 654, 'protein': 9.08, 'fat': 65.21, 'carbs': 13.71, 'fiber': 6.7, 'sodium': 2},
    'cashew': {'calories': 553, 'protein': 18.22, 'fat': 43.85, 'carbs': 30.19, 'fiber': 3.3, 'sodium': 16},
    'sesame': {'calories': 563, 'protein': 17.73, 'fat': 50, 'carbs': 23.65, 'fiber': 11.8, 'sodium': 11},
    'sunflower seed': {'calories': 584, 'protein': 20.78, 'fat': 51.46, 'carbs': 20.03, 'fiber': 8.6, 'sodium': 30},
    'flax seed': {'calories': 534, 'protein': 18.29, 'fat': 42.16, 'carbs': 28.88, 'fiber': 27.3, 'sodium': 30},
    
    # Dairy
    'cheese': {'calories': 402, 'protein': 25.18, 'fat': 33.28, 'carbs': 1.28, 'fiber': 0, 'sodium': 714},
    'cream': {'calories': 340, 'protein': 2, 'fat': 34, 'carbs': 4, 'fiber': 0, 'sodium': 43},
    'condensed milk': {'calories': 320, 'protein': 7.7, 'fat': 8.8, 'carbs': 54.4, 'fiber': 0, 'sodium': 112},
}

# Common unit conversions (to grams)
UNIT_CONVERSIONS = {
    'g': 1.0,
    'gram': 1.0,
    'grams': 1.0,
    'mg': 0.001,
    'ml': 1.0,  # assume 1:1 for ml to grams for water-based ingredients
    'cup': 240.0,
    'cups': 240.0,
    'tbsp': 15.0,
    'tablespoon': 15.0,
    'tablespoons': 15.0,
    'tsp': 5.0,
    'teaspoon': 5.0,
    'teaspoons': 5.0,
    'oz': 28.35,
    'lb': 453.592,
    'pound': 453.592,
    'kg': 1000.0,
    'liter': 1000.0,
    'l': 1000.0,
    'piece': 150.0,  # average piece
    'pc': 150.0,
    'no': 100.0,
    'nos': 100.0,
}


def get_ingredient_nutrition(name: str, quantity: str = '', unit: str = '') -> Dict:
    """
    Get nutrition data for an ingredient.
    
    Args:
        name: Ingredient name
        quantity: Quantity (e.g., "1", "2.5")
        unit: Unit (e.g., "g", "cup", "tbsp")
    
    Returns:
        Dict with keys: calories, protein, fat, carbs, fiber, sodium (all 0 if not found)
    """
    default = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0, 'sodium': 0}
    
    if not name:
        return default
    
    # Normalize name
    normalized_name = name.lower().strip()
    # Remove common suffixes
    normalized_name = re.sub(r'\b(fresh|chopped|diced|minced|sliced|large|small|medium|finely|roughly|grated|peeled|cubed|boneless|skinless|cooked|raw)\b', '', normalized_name)
    normalized_name = re.sub(r'\([^)]*\)', '', normalized_name)  # Remove parentheses
    normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
    
    # Try exact match first
    if normalized_name in INGREDIENT_DB:
        nutrition = INGREDIENT_DB[normalized_name].copy()
    else:
        # Try to find partial match
        found = False
        for key in INGREDIENT_DB.keys():
            if normalized_name.startswith(key) or key in normalized_name:
                nutrition = INGREDIENT_DB[key].copy()
                found = True
                break
        if not found:
            return default
    
    # Convert quantity to grams if possible
    amount_grams = 100.0  # default to 100g
    if quantity and unit:
        try:
            qty = float(quantity)
            unit_lower = unit.lower().strip()
            
            if unit_lower in UNIT_CONVERSIONS:
                conversion = UNIT_CONVERSIONS[unit_lower]
                amount_grams = qty * conversion
            else:
                amount_grams = qty  # assume grams if unit not recognized
        except (ValueError, TypeError):
            amount_grams = 100.0
    elif quantity:
        try:
            amount_grams = float(quantity)
        except (ValueError, TypeError):
            amount_grams = 100.0
    
    # Scale nutrition based on amount
    scale = amount_grams / 100.0
    for key in nutrition:
        nutrition[key] = round(nutrition[key] * scale, 2)
    
    return nutrition
