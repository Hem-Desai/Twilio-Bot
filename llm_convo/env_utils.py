"""
Environment utilities for loading .env files and checking required variables
"""

import os
from pathlib import Path
from typing import Optional, List


def load_env_file(env_file: Optional[str] = None) -> bool:
    """
    Load environment variables from .env file
    
    Args:
        env_file: Path to .env file (defaults to .env in current directory)
        
    Returns:
        True if .env file was loaded successfully, False otherwise
    """
    try:
        from dotenv import load_dotenv
        
        if env_file is None:
            # Look for .env file in current directory and parent directories
            current_dir = Path.cwd()
            for path in [current_dir] + list(current_dir.parents):
                env_path = path / ".env"
                if env_path.exists():
                    env_file = str(env_path)
                    break
        
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"✅ Loaded environment variables from {env_file}")
            return True
        else:
            print("ℹ️ No .env file found (this is optional)")
            return False
            
    except ImportError:
        print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"⚠️ Error loading .env file: {e}")
        return False


def check_required_env_vars(required_vars: List[str], service_name: str = "service") -> bool:
    """
    Check if required environment variables are set
    
    Args:
        required_vars: List of required environment variable names
        service_name: Name of the service for error messages
        
    Returns:
        True if all required variables are set, False otherwise
    """
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables for {service_name}:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print(f"✅ All required environment variables for {service_name} are set")
    return True


def check_groq_setup() -> bool:
    """Check if Groq API key is set up"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ GROQ_API_KEY environment variable not found!")
        print("\n🔧 To get a FREE Groq API key:")
        print("1. Visit https://console.groq.com")
        print("2. Sign up for a free account")
        print("3. Go to API Keys section")
        print("4. Create a new API key")
        print("5. Add to your .env file: GROQ_API_KEY=your-key-here")
        return False
    
    print(f"✅ Groq API key found: {groq_api_key[:10]}...")
    return True


def check_twilio_setup() -> bool:
    """Check if Twilio credentials are set up"""
    required_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"]
    
    if not check_required_env_vars(required_vars, "Twilio"):
        print("\n🔧 To set up Twilio:")
        print("1. Sign up at https://www.twilio.com/try-twilio")
        print("2. Get your Account SID and Auth Token from console.twilio.com")
        print("3. Buy a phone number")
        print("4. Add to your .env file:")
        print("   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print("   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print("   TWILIO_PHONE_NUMBER=+1xxxxxxxxxx")
        return False
    
    return True


def check_google_places_setup() -> bool:
    """Check if Google Places API key is set up"""
    google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not google_api_key:
        print("💡 GOOGLE_PLACES_API_KEY not found (optional for business search)")
        print("\n🔧 To get a FREE Google Places API key ($200/month credit):")
        print("1. Visit https://console.cloud.google.com")
        print("2. Create a new project or select existing")
        print("3. Enable Places API")
        print("4. Create API key in 'Credentials'")
        print("5. Add to your .env file: GOOGLE_PLACES_API_KEY=your-key-here")
        print("\n💰 FREE tier supports ~4,000 searches/month!")
        return False
    
    print(f"✅ Google Places API key found: {google_api_key[:10]}...")
    return True


def setup_environment() -> bool:
    """
    Complete environment setup - loads .env file and checks required variables
    
    Returns:
        True if environment is properly set up, False otherwise
    """
    print("🔧 Setting up environment...")
    
    # Load .env file
    load_env_file()
    
    # Check if we have either Groq or OpenAI
    has_groq = os.getenv("GROQ_API_KEY")
    has_openai = os.getenv("OPENAI_API_KEY")
    
    if not has_groq and not has_openai:
        print("❌ No AI API key found!")
        print("\n💡 Recommendation: Use FREE Groq API")
        print("Add to your .env file: GROQ_API_KEY=your-groq-key")
        print("Get your free key at: https://console.groq.com")
        return False
    
    if has_groq:
        print("✅ Using Groq API (FREE!)")
    elif has_openai:
        print("✅ Using OpenAI API")
    
    return True


def create_env_file_if_missing():
    """Create .env file from .env.example if it doesn't exist"""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if not env_path.exists() and example_path.exists():
        print("📝 Creating .env file from .env.example...")
        env_path.write_text(example_path.read_text())
        print("✅ Created .env file. Please edit it with your actual credentials.")
        return True
    
    return False 