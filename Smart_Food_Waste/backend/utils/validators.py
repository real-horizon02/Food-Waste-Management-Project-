"""
Input validation utilities
"""
import re


def validate_email(email):
    """
    Validate email format
    
    Args:
        email: Email string
    
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password):
    """
    Validate password (minimum requirements)
    
    Args:
        password: Password string
    
    Returns:
        True if valid, False otherwise
    """
    if not password:
        return False
    
    # Minimum 6 characters
    if len(password) < 6:
        return False
    
    return True


def validate_dish_name(dish_name):
    """
    Validate dish name
    
    Args:
        dish_name: Dish name string
    
    Returns:
        True if valid, False otherwise
    """
    if not dish_name:
        return False
    
    if len(dish_name.strip()) < 2:
        return False
    
    if len(dish_name) > 200:
        return False
    
    return True


def validate_household_size(household_size):
    """
    Validate household size
    
    Args:
        household_size: Household size string or int
    
    Returns:
        True if valid, False otherwise
    """
    try:
        size = int(household_size)
        return 1 <= size <= 50  # Reasonable range
    except (ValueError, TypeError):
        return False

