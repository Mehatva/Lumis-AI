import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    # Use absolute path to ensure all contexts use the same file
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.getenv("CHATBOT_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'chatbot.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5001")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Instagram
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "verify123")
    INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID", "")

    # Feature flags
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin123")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key") # Change in production
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    META_APP_ID = os.getenv("META_APP_ID", "")
    META_APP_SECRET = os.getenv("META_APP_SECRET", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
