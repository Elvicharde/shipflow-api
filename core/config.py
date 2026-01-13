from decouple import config, Csv

class Config:
    """Centralized app configuration"""

    # Core
    DEBUG = config('DEBUG', default=False, cast=bool)
    SECRET_KEY = config('SECRET_KEY')
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
    
    # Database
    DATABASE_URL = config('DATABASE_URL')
    DB_NAME = config('DB_NAME')
    DB_USER = config('DB_USER')
    DB_PASSWORD = config('DB_PASSWORD')
    DB_HOST = config('DB_HOST')
    DB_PORT = config('DB_PORT')
    
    # CORS
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
    
    # External Services
    USPS_USER_ID = config('USPS_USER_ID', default='xxxx')
    GEOAPIFY_API_KEY = config('GEOAPIFY_API_KEY', default='xxxx')
    HERE_API_KEY = config('HERE_API_KEY', default='xxxx')
    MAPBOX_ACCESS_TOKEN = config('MAPBOX_ACCESS_TOKEN', default='xxxx')
    GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='xxxx')


    # API LIMITS
    CACHE_TTL =  int(config('ADDRESS_VERIFICATION_CACHE_TTL', default=30 * 24 * 60 * 60)),  # 30 days
    CIRCUIT_BREAKER_THRESHOLD = int(config('ADDRESS_VERIFICATION_CIRCUIT_BREAKER_THRESHOLD', default=5)),
    CIRCUIT_BREAKER_TIMEOUT = int(config('ADDRESS_VERIFICATION_CIRCUIT_BREAKER_TIMEOUT', default=300)),

    # FILE MANAGEMENT
    FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
    DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB



    @classmethod
    def is_production(cls):
        return not cls.DEBUG