import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///resume_matcher.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    WTF_CSRF_ENABLED = True

    # Gemini AI configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

    # Semantic matching weights (must sum to 1.0)
    MATCH_WEIGHTS = {
        'semantic': 0.45,    # cosine similarity of semantic embeddings
        'skills': 0.25,      # direct/related skill matches
        'capabilities': 0.15, # inferred capabilities from analysis
        'experience': 0.10,  # experience level alignment
        'education': 0.05,   # education requirement alignment
    }

    # Legacy weights kept for backward compatibility with matching_service.py tests
    TFIDF_WEIGHT = 0.40
    SKILL_WEIGHT = 0.40
    EXPERIENCE_WEIGHT = 0.10
    EDUCATION_WEIGHT = 0.10

    # Analysis version — increment to force re-analysis of all documents
    CURRENT_ANALYSIS_VERSION = 1


class DevelopmentConfig(Config):
    """Development configuration."""
    FLASK_ENV = 'development'
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    FLASK_ENV = 'production'
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
