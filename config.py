import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the Discord bot"""
    
    # discord bot config
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    
    # firebase config
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")  # JSON string
    
    # bot settings
    COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is required")
        
        if not any([cls.FIREBASE_CREDENTIALS_PATH, cls.FIREBASE_PROJECT_ID, cls.FIREBASE_CREDENTIALS]):
            errors.append("Firebase credentials not provided. Set FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID, or FIREBASE_CREDENTIALS")
        
        return errors
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration"""
        return {
            "credentials_path": cls.FIREBASE_CREDENTIALS_PATH,
            "project_id": cls.FIREBASE_PROJECT_ID,
            "credentials_json": cls.FIREBASE_CREDENTIALS
        } 