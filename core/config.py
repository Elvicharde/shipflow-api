from decouple import config, Csv

class Config:
    """Centralized app configuration"""

    # Core
    DEBUG = config('DEBUG', default=False, cast=bool)
    SECRET_KEY = config('SECRET_KEY')
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
    
    # Database
    DATABASE_URL = config('DATABASE_URL')
    
    # CORS
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
    
    # External Services
    STRIPE_API_KEY = config('STRIPE_API_KEY', default='')
    SHIPPO_API_KEY = config('SHIPPO_API_KEY', default='')
    
    @classmethod
    def is_production(cls):
        return not cls.DEBUG