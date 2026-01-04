"""
Configuration settings for the Flask application
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # MongoDB configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_waste_db')
    
    # Google Search API configuration
    GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY', '')
    GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')
    
    # Spoonacular API (backup)
    SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY', '')
    # Edamam Nutrition Analysis API
    EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID', '')
    EDAMAM_APP_KEY = os.getenv('EDAMAM_APP_KEY', '')
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    MONGO_URI = os.getenv('TEST_MONGO_URI', 'mongodb://localhost:27017/smart_waste_test_db')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


