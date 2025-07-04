import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # App Configuration
    APP_NAME = "LLM Convo SignalWire"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DOMAIN = os.getenv("DOMAIN", "localhost:8000")
    
    # SignalWire Configuration
    SIGNALWIRE_PROJECT_ID = os.getenv("SIGNALWIRE_PROJECT_ID")
    SIGNALWIRE_TOKEN = os.getenv("SIGNALWIRE_TOKEN")
    SIGNALWIRE_SPACE_URL = os.getenv("SIGNALWIRE_SPACE_URL")  # e.g., "yourspace.signalwire.com"
    SIGNALWIRE_PHONE_NUMBER = os.getenv("SIGNALWIRE_PHONE_NUMBER")
    
    # AI Service Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    
    # AWS Configuration (for Polly)
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    
    # Google Configuration
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Audio Configuration
    AUDIO_DIR = os.getenv("AUDIO_DIR", "app/static/audio")
    
    # LLM Configuration
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    
    # TTS Configuration
    POLLY_VOICE_ID = os.getenv("POLLY_VOICE_ID", "Joanna")
    POLLY_ENGINE = os.getenv("POLLY_ENGINE", "neural")
    
    # Business Search Configuration
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    MIN_RATING = float(os.getenv("MIN_RATING", "4.0"))
    
    @classmethod
    def validate_required_vars(cls):
        """Validate that all required environment variables are set"""
        # For testing purposes, allow missing or test values
        required_vars = [
            "SIGNALWIRE_PROJECT_ID",
            "SIGNALWIRE_TOKEN", 
            "SIGNALWIRE_SPACE_URL",
            "GROQ_API_KEY",
            "DEEPGRAM_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "GOOGLE_PLACES_API_KEY"
        ]
        
        missing_vars = []
        test_mode = cls.DEBUG
        
        for var in required_vars:
            value = getattr(cls, var)
            # In test mode, allow empty or test values
            if not test_mode and not value:
                missing_vars.append(var)
            elif not test_mode and value and (value.startswith("test_") or value.endswith("_here")):
                missing_vars.append(var)
        
        if missing_vars and not test_mode:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        elif missing_vars and test_mode:
            print(f"⚠️ Warning: Missing or test values for: {', '.join(missing_vars)}")
            print("🧪 Running in test mode with mock services")
        
        return True

# Create settings instance
settings = Settings() 