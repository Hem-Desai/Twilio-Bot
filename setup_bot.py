#!/usr/bin/env python3
"""
FREE AI Phone Bot Setup Script

This script helps you set up your FREE AI phone bot system step by step.
"""

import os
import sys
from pathlib import Path

def print_header():
    """Print welcome header"""
    print("""
🤖 FREE AI Phone Bot Setup
==========================

This script will help you set up your FREE AI phone bot system using:
- Groq API (100% FREE)
- Twilio (phone service)
- Local database and dashboard

Let's get started!
""")

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. You have:", sys.version)
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - Compatible!")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    dependencies = [
        "groq",
        "sqlalchemy", 
        "flask-sqlalchemy",
        "python-dateutil",
        "python-dotenv"
    ]
    
    try:
        import subprocess
        
        # Install main package
        print("Installing llm_convo package...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "git+https://github.com/sshh12/llm_convo"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ Warning installing llm_convo: {result.stderr}")
        else:
            print("✅ llm_convo package installed")
        
        # Install additional dependencies
        for dep in dependencies:
            print(f"Installing {dep}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {dep} installed")
            else:
                print(f"⚠️ Warning installing {dep}: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        print("\n🔧 Manual installation:")
        print("pip install git+https://github.com/sshh12/llm_convo")
        for dep in dependencies:
            print(f"pip install {dep}")
        return False

def setup_env_file():
    """Set up .env file"""
    print("\n📝 Setting up .env file...")
    
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
    
    if not example_path.exists():
        print("❌ .env.example file not found")
        return False
    
    # Copy example to .env
    env_path.write_text(example_path.read_text())
    print("✅ Created .env file from .env.example")
    
    return True

def get_groq_api_key():
    """Guide user through getting Groq API key"""
    print("\n🔑 Setting up FREE Groq API...")
    
    # Check if already set
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "your-groq-api-key-here":
            print("✅ Groq API key already configured!")
            return True
    except:
        pass
    
    print("""
🆓 Get your FREE Groq API key:

1. Visit: https://console.groq.com
2. Sign up (no credit card required!)
3. Go to 'API Keys' section
4. Create a new API key
5. Copy the key (starts with 'gsk_')

Then come back here and paste it.
""")
    
    api_key = input("Enter your Groq API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⏭️ Skipped Groq API key setup")
        return False
    
    if not api_key.startswith("gsk_"):
        print("⚠️ Warning: Groq API keys usually start with 'gsk_'")
    
    # Update .env file
    try:
        env_path = Path(".env")
        content = env_path.read_text()
        content = content.replace("GROQ_API_KEY=your-groq-api-key-here", f"GROQ_API_KEY={api_key}")
        env_path.write_text(content)
        print("✅ Groq API key saved to .env file!")
        return True
    except Exception as e:
        print(f"❌ Error saving API key: {e}")
        return False

def setup_twilio():
    """Guide user through Twilio setup"""
    print("\n📞 Setting up Twilio (optional for now)...")
    
    print("""
📞 Twilio Setup (needed for phone calls):

1. Sign up at: https://www.twilio.com/try-twilio
2. Get $15 free trial credit
3. Buy a phone number (~$1/month)
4. Get your credentials from console.twilio.com:
   - Account SID (starts with 'AC')
   - Auth Token
   - Phone Number (format: +1xxxxxxxxxx)

You can set this up later in your .env file.
""")
    
    setup_now = input("Set up Twilio credentials now? (y/N): ").strip().lower()
    
    if setup_now != 'y':
        print("⏭️ Skipped Twilio setup - you can add credentials to .env later")
        return False
    
    account_sid = input("Enter Twilio Account SID: ").strip()
    auth_token = input("Enter Twilio Auth Token: ").strip()
    phone_number = input("Enter Twilio Phone Number (+1xxxxxxxxxx): ").strip()
    
    if not all([account_sid, auth_token, phone_number]):
        print("⏭️ Incomplete Twilio setup - you can add credentials to .env later")
        return False
    
    # Update .env file
    try:
        env_path = Path(".env")
        content = env_path.read_text()
        content = content.replace("TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", f"TWILIO_ACCOUNT_SID={account_sid}")
        content = content.replace("TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", f"TWILIO_AUTH_TOKEN={auth_token}")
        content = content.replace("TWILIO_PHONE_NUMBER=+1xxxxxxxxxx", f"TWILIO_PHONE_NUMBER={phone_number}")
        env_path.write_text(content)
        print("✅ Twilio credentials saved to .env file!")
        return True
    except Exception as e:
        print(f"❌ Error saving Twilio credentials: {e}")
        return False

def test_setup():
    """Test the setup"""
    print("\n🧪 Testing your setup...")
    
    try:
        # Test Groq API
        print("Testing Groq API...")
        result = os.system("python test_groq_simple.py")
        
        if result == 0:
            print("✅ Setup test completed!")
        else:
            print("⚠️ Some tests failed - check the output above")
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")

def show_next_steps():
    """Show next steps"""
    print("""
🎉 Setup Complete!

🚀 Next Steps:

1. Test your bot:
   python test_groq_simple.py

2. Run your FREE AI phone bot:
   python examples/groq_phone_bot.py --start_ngrok --bot_type general

3. If you set up Twilio:
   - Copy the ngrok URL from the console
   - Set it as your Twilio webhook: https://your-url.ngrok.io/incoming-voice
   - Call your Twilio number to test!

4. Visit the dashboard:
   http://localhost:5000

📚 Documentation:
- Quick Start: QUICK_START.md
- Full Guide: FREE_SETUP_GUIDE.md
- Twilio Setup: TWILIO_SETUP.md

💡 Remember: Groq is completely FREE with generous rate limits!

Enjoy your FREE AI phone bot! 🤖📞
""")

def main():
    """Main setup process"""
    print_header()
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install dependencies
    if not install_dependencies():
        print("\n⚠️ Dependency installation had issues. You may need to install manually.")
    
    # Setup .env file
    if not setup_env_file():
        print("\n❌ Could not set up .env file")
        return 1
    
    # Get Groq API key
    if not get_groq_api_key():
        print("\n⚠️ Groq API key not configured. You can add it to .env later.")
    
    # Setup Twilio (optional)
    setup_twilio()
    
    # Test setup
    test_setup()
    
    # Show next steps
    show_next_steps()
    
    return 0

if __name__ == "__main__":
    exit(main()) 