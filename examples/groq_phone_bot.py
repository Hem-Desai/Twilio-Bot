#!/usr/bin/env python3
"""
Enhanced AI Phone Bot with Groq (FREE Alternative to OpenAI)

This example creates a complete AI phone bot system using Groq's free API with:
- Live transcription and TTS
- Database storage of conversations
- Web dashboard for monitoring
- Multiple bot personalities
- FREE Groq API (no OpenAI costs!)

Usage:
    python examples/groq_phone_bot.py --preload_whisper --start_ngrok --bot_type customer_service
    
    Then visit http://localhost:5000 for the dashboard

Setup:
    1. Copy .env.example to .env
    2. Get free Groq API key from https://console.groq.com
    3. Add GROQ_API_KEY to your .env file
    4. Set up Twilio credentials in .env file (see TWILIO_SETUP.md)
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
from llm_convo.groq_enhanced_agents import (
    create_groq_customer_service_bot, 
    create_groq_appointment_scheduler_bot, 
    create_groq_general_assistant_bot,
    create_groq_pizza_bot
)
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
            print("   2. Add your Twilio credentials (see TWILIO_SETUP.md)")
            print("   3. Run this script again")
            return False
        
        # Load environment variables
        load_env_file()
        
        # Check Groq setup
        return check_groq_setup()
        
    except ImportError:
        print("⚠️ Environment utilities not available. Using system environment variables.")
        return check_groq_setup_basic()


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
        print("5. Set environment variable: export GROQ_API_KEY='your-key-here'")
        print("\n💡 Groq is completely FREE with generous rate limits!")
        return False
    
    print(f"✅ Groq API key found: {groq_api_key[:10]}...")
    return True


def start_dashboard(database_url=None, dashboard_port=5000):
    """Start the web dashboard in a separate thread"""
    def run_dashboard():
        dashboard = ConversationDashboard(database_url=database_url, port=dashboard_port)
        dashboard.run(debug=False)
    
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    return dashboard_thread


def main(port, remote_host, start_ngrok, bot_type, dashboard_port, preload_whisper):
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
    
    # Setup directories
    static_dir = os.path.join(tempfile.gettempdir(), "twilio_static")
    os.makedirs(static_dir, exist_ok=True)
    
    # Initialize database
    database_url = f"sqlite:///{os.path.join(os.getcwd(), 'conversations.db')}"
    db_manager = DatabaseManager(database_url)
    
    # Start dashboard (only if not Railway or different port)
    if not os.environ.get('RAILWAY_ENVIRONMENT') or dashboard_port != port:
        logging.info(f"Starting dashboard on http://localhost:{dashboard_port}")
        start_dashboard(database_url, dashboard_port)
    
    # Setup Twilio server
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Railway provides the public URL
        public_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', 'your-app.railway.app')}"
        logging.info(f"🚂 Railway URL: {public_url}")
        logging.info(f"🔗 Set Twilio webhook to: {public_url}/incoming-voice")
        logging.info(f"📊 Dashboard will be at: {public_url}")
    else:
        logging.info(f"Starting Twilio server at {remote_host} from local:{port}")
        logging.info(f"Set call webhook to https://{remote_host}/incoming-voice")
        logging.info(f"Dashboard available at http://localhost:{dashboard_port}")
    
    tws = TwilioServer(remote_host=remote_host, port=port, static_dir=static_dir)
    tws.start()
    
    # Create conversation logger
    conversation_logger = ConversationLogger(db_manager)
    
    # Get Groq API key
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # Create bot based on type using Groq
    bot_creators = {
        'customer_service': create_groq_customer_service_bot,
        'appointment': create_groq_appointment_scheduler_bot,
        'general': create_groq_general_assistant_bot,
        'pizza': create_groq_pizza_bot
    }
    
    if bot_type not in bot_creators:
        raise ValueError(f"Unknown bot type: {bot_type}. Available: {list(bot_creators.keys())}")
    
    bot = bot_creators[bot_type](conversation_logger, groq_api_key)
    logging.info(f"Created {bot_type} bot using Groq (FREE!)")
    
    def run_chat(sess):
        """Handle incoming call session"""
        try:
            # Create agents for this conversation
            ai_agent, twilio_agent = bot.create_agents(sess)
            
            # Wait for media stream to connect
            while not twilio_agent.session.media_stream_connected():
                time.sleep(0.1)
            
            logging.info("Media stream connected, starting conversation")
            
            # Run the enhanced conversation with database logging
            run_enhanced_conversation(ai_agent, twilio_agent, conversation_logger)
            
            logging.info("Conversation ended")
            
        except Exception as e:
            logging.error(f"Error in conversation: {e}")
            conversation_logger.end_conversation('failed')
    
    # Set the session handler
    tws.on_session = run_chat
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        db_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced AI Phone Bot with FREE Groq API")
    parser.add_argument("--preload_whisper", action="store_true", 
                       help="Preload Whisper model for faster startup")
    parser.add_argument("--start_ngrok", action="store_true", 
                       help="Start ngrok tunnel for public access")
    parser.add_argument("--port", type=int, default=8080, 
                       help="Port for Twilio webhook server")
    parser.add_argument("--dashboard_port", type=int, default=5000, 
                       help="Port for web dashboard")
    parser.add_argument("--remote_host", type=str, default="localhost", 
                       help="Remote host (ignored if using ngrok)")
    parser.add_argument("--bot_type", type=str, default="general", 
                       choices=["customer_service", "appointment", "general", "pizza"],
                       help="Type of bot to create")
    
    args = parser.parse_args()
    
    print(f"""
🤖 Enhanced AI Phone Bot with FREE Groq API

Configuration:
- Bot Type: {args.bot_type}
- Twilio Port: {args.port}
- Dashboard Port: {args.dashboard_port}
- Ngrok: {'Yes' if args.start_ngrok else 'No'}
- Preload Whisper: {'Yes' if args.preload_whisper else 'No'}
- AI Provider: Groq (FREE!)

💡 Benefits of using Groq:
- Completely FREE API with generous limits
- Very fast response times (great for phone calls)
- Multiple models available (Llama3, Mixtral, etc.)
- No credit card required

📝 Setup:
1. Make sure you have a .env file with your credentials
2. Get free Groq API key from https://console.groq.com
3. Set up Twilio credentials (see TWILIO_SETUP.md)

After startup:
1. Set your Twilio webhook to the provided URL
2. Visit http://localhost:{args.dashboard_port} for the dashboard
3. Make a call to your Twilio number to test

Press Ctrl+C to stop.
    """)
    
    main(
        port=args.port,
        remote_host=args.remote_host,
        start_ngrok=args.start_ngrok,
        bot_type=args.bot_type,
        dashboard_port=args.dashboard_port,
        preload_whisper=args.preload_whisper
    ) 