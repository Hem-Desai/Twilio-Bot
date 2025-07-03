#!/usr/bin/env python3
"""
AI Call Forwarding Service

This example creates a complete AI call forwarding system that:
- Listens for business requests ("I need a dentist in Mumbai")
- Searches for businesses in real-time using Google Places API
- Presents options with ratings and hours
- Forwards calls directly to selected businesses
- Logs all interactions to database

The system uses:
- Groq API for FREE AI conversation (no OpenAI costs!)
- Google Places API for real-time business search
- Twilio for call handling and forwarding
- Local database for conversation tracking
- Web dashboard for monitoring

Usage:
    python examples/call_forwarding_bot.py --preload_whisper --start_ngrok
    
    Then call your Twilio number and try:
    - "I need a dentist in Ahmedabad"
    - "Find me a restaurant in Mumbai" 
    - "I want a mechanic near me"

Setup:
    1. Copy .env.example to .env
    2. Get FREE Groq API key from https://console.groq.com
    3. Get Google Places API key from Google Cloud Console
    4. Set up Twilio account and phone number
    5. Update .env with all API keys
"""

from gevent import monkey
monkey.patch_all()

import logging
import argparse
import tempfile
import os
import sys
import time
import threading
from flask import Flask

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_convo.audio_input import get_whisper_model
from llm_convo.twilio_io import TwilioServer
from llm_convo.enhanced_conversation import run_enhanced_conversation, ConversationLogger
from llm_convo.database import DatabaseManager
from llm_convo.dashboard import ConversationDashboard
from llm_convo.groq_enhanced_agents import create_groq_call_forwarding_bot
from pyngrok import ngrok

# Create a simple health check app for Railway
health_app = Flask(__name__)

@health_app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': time.time()}

def start_health_server():
    """Start health check server in background"""
    import threading
    def run_health():
        health_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
    
    health_thread = threading.Thread(target=run_health, daemon=True)
    health_thread.start()
    return health_thread

def setup_environment():
    """Setup environment by loading .env file"""
    try:
        from llm_convo.env_utils import load_env_file, create_env_file_if_missing, check_groq_setup
        
        # Create .env file from example if it doesn't exist
        if create_env_file_if_missing():
            print("📝 Created .env file from .env.example")
            print("🔧 Please edit the .env file with your actual credentials:")
            print("   1. Add your GROQ_API_KEY (get free at https://console.groq.com)")
            print("   2. Add your GOOGLE_PLACES_API_KEY (get from Google Cloud Console)")
            print("   3. Add your Twilio credentials (see TWILIO_SETUP.md)")
            print("   4. Run this script again")
            return False
        
        # Load environment variables
        load_env_file()
        
        # Check Groq setup
        return check_groq_setup() and check_google_places_setup()
        
    except ImportError:
        print("⚠️ Environment utilities not available. Using system environment variables.")
        return check_groq_setup_basic() and check_google_places_setup()

def check_groq_setup_basic():
    """Basic Groq setup check without env_utils"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ GROQ_API_KEY environment variable not found!")
        print("\n🔧 To get a FREE Groq API key:")
        print("1. Visit https://console.groq.com")
        print("2. Sign up for a free account")
        print("3. Go to API Keys section")
        print("4. Create a new API key")
        print("5. Add to .env file: GROQ_API_KEY='your-key-here'")
        print("\n💡 Groq is completely FREE with generous rate limits!")
        return False
    
    print(f"✅ Groq API key found: {groq_api_key[:10]}...")
    return True

def check_google_places_setup():
    """Check Google Places API setup"""
    google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not google_api_key:
        print("❌ GOOGLE_PLACES_API_KEY environment variable not found!")
        print("\n🔧 To get a Google Places API key:")
        print("1. Visit https://console.cloud.google.com")
        print("2. Create a new project or select existing")
        print("3. Enable Places API")
        print("4. Create credentials (API Key)")
        print("5. Add to .env file: GOOGLE_PLACES_API_KEY='your-key-here'")
        print("\n💰 Google gives $200 free credit monthly (covers ~4000 searches)")
        return False
    
    print(f"✅ Google Places API key found: {google_api_key[:10]}...")
    return True

def start_dashboard(database_url=None, dashboard_port=5000):
    """Start the web dashboard in a separate thread"""
    def run_dashboard():
        dashboard = ConversationDashboard(database_url=database_url, port=dashboard_port)
        dashboard.run(debug=False)
    
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    return dashboard_thread

def print_system_info():
    """Print system capabilities and setup info"""
    print("""
🤖 AI Call Forwarding Service
=============================

🔍 System Capabilities:
- Real-time business search using Google Places API
- Live call forwarding to any business
- AI intent understanding with Groq (FREE!)
- Conversation logging and dashboard
- Support for multiple languages

📞 Example Requests:
- "I need a dentist in Mumbai"
- "Find me a restaurant in Delhi"  
- "I want a mechanic near me"
- "Connect me to a hospital in Bangalore"

🚀 The system will:
1. Understand your request using AI
2. Search for businesses in real-time
3. Present options with ratings and hours
4. Forward your call directly to chosen business
5. Log everything for monitoring

🎯 Perfect for:
- Directory assistance services
- Business referral services
- Emergency service routing
- Customer service automation
""")

def main(port, remote_host, start_ngrok, dashboard_port, preload_whisper):
    # Print system info
    print_system_info()
    
    # Setup environment first
    if not setup_environment():
        return
    
    # Setup logging
    logging.getLogger().setLevel(logging.INFO)
    
    # For Railway deployment, use PORT environment variable
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        port = int(os.environ.get('PORT', 8080))
        dashboard_port = port  # Use same port for Railway
        start_ngrok = False  # Don't use ngrok on Railway
        remote_host = f"0.0.0.0:{port}"
        logging.info("🚂 Railway deployment detected")
    
    # Start health check server for Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        start_health_server()
        logging.info(f"✅ Health check server started on port {port}")
    
    # Preload Whisper model if requested
    if preload_whisper:
        logging.info("Preloading Whisper model...")
        get_whisper_model()
    
    # Setup ngrok if requested (not for Railway)
    if start_ngrok and not os.environ.get('RAILWAY_ENVIRONMENT'):
        ngrok_http = ngrok.connect(port)
        remote_host = ngrok_http.public_url.split("//")[1]
        print(f"🌐 Ngrok tunnel: https://{remote_host}")
    
    # Setup directories
    static_dir = os.path.join(tempfile.gettempdir(), "twilio_static")
    os.makedirs(static_dir, exist_ok=True)
    
    # Initialize database
    database_url = f"sqlite:///{os.path.join(os.getcwd(), 'conversations.db')}"
    db_manager = DatabaseManager(database_url)
    
    # Start dashboard (only if not Railway or different port)
    if not os.environ.get('RAILWAY_ENVIRONMENT') or dashboard_port != port:
        logging.info(f"📊 Starting dashboard on http://localhost:{dashboard_port}")
        start_dashboard(database_url, dashboard_port)
    
    # Setup Twilio server
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Railway provides the public URL
        public_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', 'your-app.railway.app')}"
        logging.info(f"🚂 Railway URL: {public_url}")
        logging.info(f"🔗 Set Twilio webhook to: {public_url}/incoming-voice")
        logging.info(f"📊 Dashboard will be at: {public_url}")
    else:
        logging.info(f"🚀 Starting Twilio server at {remote_host} from local:{port}")
        logging.info(f"🔗 Set call webhook to https://{remote_host}/incoming-voice")
        logging.info(f"📊 Dashboard available at http://localhost:{dashboard_port}")
    
    print(f"\n🎯 Ready for business search and call forwarding!")
    print(f"📞 Call your Twilio number and try: 'I need a dentist in Mumbai'")
    
    tws = TwilioServer(remote_host=remote_host, port=port, static_dir=static_dir)
    tws.start()
    
    # Create conversation logger
    conversation_logger = ConversationLogger(db_manager)
    
    # Get API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    
    # Create call forwarding bot
    bot = create_groq_call_forwarding_bot(
        conversation_logger=conversation_logger, 
        groq_api_key=groq_api_key,
        google_api_key=google_api_key
    )
    logging.info("🤖 Created call forwarding bot with business search!")
    
    def run_chat(sess):
        try:
            logging.info("📞 New call received - starting call forwarding session")
            ai_agent, twilio_agent = bot.create_agents(sess)
            run_enhanced_conversation(ai_agent, twilio_agent, conversation_logger)
        except Exception as e:
            logging.error(f"❌ Error in call session: {e}")
    
    tws.on_session = run_chat
    
    logging.info("✅ Call forwarding service is running!")
    logging.info("🎯 Try calling and saying: 'I need a dentist in your city'")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\n👋 Shutting down call forwarding service...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Call Forwarding Service")
    parser.add_argument("--port", type=int, default=8091, help="Port to run on")
    parser.add_argument("--remote_host", default="localhost:8091", help="Remote host")
    parser.add_argument("--start_ngrok", action="store_true", help="Start ngrok tunnel")
    parser.add_argument("--dashboard_port", type=int, default=5000, help="Dashboard port")
    parser.add_argument("--preload_whisper", action="store_true", help="Preload Whisper model")
    
    args = parser.parse_args()
    
    main(
        port=args.port,
        remote_host=args.remote_host,
        start_ngrok=args.start_ngrok,
        dashboard_port=args.dashboard_port,
        preload_whisper=args.preload_whisper
    ) 