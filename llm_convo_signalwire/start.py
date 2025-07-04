#!/usr/bin/env python3
"""
SignalWire Implementation Startup Script

Usage:
    python start.py                    # Run with default settings
    python start.py --port 8080        # Run on custom port
    python start.py --debug            # Run in debug mode
    python start.py --test-services    # Test all service connections
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import our modules
from config.settings import settings
from services.groq_client import groq_client
from services.deepgram_client import deepgram_client
from services.polly_client import polly_client
from services.places_client import places_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_all_services():
    """Test all service connections"""
    logger.info("🧪 Testing all service connections...")
    
    tests = []
    
    # Test Groq
    try:
        logger.info("Testing Groq...")
        test_intent = await groq_client.extract_business_intent("I need a dentist in New York")
        if test_intent and test_intent.get('business_type'):
            logger.info("✅ Groq test passed")
            tests.append(("Groq", True))
        else:
            logger.error("❌ Groq test failed")
            tests.append(("Groq", False))
    except Exception as e:
        logger.error(f"❌ Groq test error: {e}")
        tests.append(("Groq", False))
    
    # Test Google Places
    try:
        logger.info("Testing Google Places...")
        results = await places_client.search_businesses("restaurant", "New York")
        if results:
            logger.info(f"✅ Google Places test passed ({len(results)} results)")
            tests.append(("Google Places", True))
        else:
            logger.error("❌ Google Places test failed - no results")
            tests.append(("Google Places", False))
    except Exception as e:
        logger.error(f"❌ Google Places test error: {e}")
        tests.append(("Google Places", False))
    
    # Test Polly
    try:
        logger.info("Testing Amazon Polly...")
        success = await polly_client.test_synthesis()
        tests.append(("Amazon Polly", success))
    except Exception as e:
        logger.error(f"❌ Polly test error: {e}")
        tests.append(("Amazon Polly", False))
    
    # Test Deepgram (basic connectivity)
    try:
        logger.info("Testing Deepgram...")
        success = await deepgram_client.test_transcription()
        tests.append(("Deepgram", success))
    except Exception as e:
        logger.error(f"❌ Deepgram test error: {e}")
        tests.append(("Deepgram", False))
    
    # Print results
    logger.info("\n" + "="*50)
    logger.info("🧪 SERVICE TEST RESULTS")
    logger.info("="*50)
    
    for service, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{service:15} {status}")
    
    logger.info("="*50)
    
    passed_count = sum(1 for _, passed in tests if passed)
    total_count = len(tests)
    
    if passed_count == total_count:
        logger.info(f"🎉 All {total_count} services are working correctly!")
        return True
    else:
        logger.warning(f"⚠️  {passed_count}/{total_count} services passed. Check your configuration.")
        return False

def check_environment():
    """Check required environment variables"""
    logger.info("🔍 Checking environment configuration...")
    
    try:
        settings.validate_required_vars()
        logger.info("✅ All required environment variables are set")
        return True
    except ValueError as e:
        logger.error(f"❌ Environment configuration error: {e}")
        logger.info("\n💡 To fix this:")
        logger.info("1. Copy env.example to .env")
        logger.info("2. Fill in your API keys in the .env file")
        logger.info("3. Make sure all required services are configured")
        return False

async def preload_common_phrases():
    """Preload common TTS phrases for faster response"""
    logger.info("🔄 Preloading common phrases...")
    try:
        await polly_client.preload_common_phrases()
        logger.info("✅ Common phrases preloaded")
    except Exception as e:
        logger.warning(f"⚠️ Could not preload phrases: {e}")

def print_startup_info():
    """Print startup information and instructions"""
    logger.info("\n" + "="*60)
    logger.info("🚀 SIGNALWIRE IMPLEMENTATION STARTING")
    logger.info("="*60)
    logger.info(f"📋 App: {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"🌐 Domain: {settings.DOMAIN}")
    logger.info(f"📱 SignalWire Space: {settings.SIGNALWIRE_SPACE_URL}")
    logger.info(f"🤖 LLM Model: {settings.GROQ_MODEL}")
    logger.info(f"🎤 TTS Voice: {settings.POLLY_VOICE_ID}")
    logger.info("="*60)
    
    if settings.DEBUG:
        logger.info("🔧 DEBUG MODE - Using ngrok for webhooks")
        logger.info("📞 Set SignalWire webhook to: https://your-ngrok-url.ngrok.io/webhook/incoming-call")
    else:
        logger.info("🌍 PRODUCTION MODE")
        logger.info(f"📞 Set SignalWire webhook to: https://{settings.DOMAIN}/webhook/incoming-call")
    
    logger.info("\n🎯 Ready for business search and call forwarding!")
    logger.info("📞 Test by calling your SignalWire phone number")
    logger.info("="*60)

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="Start SignalWire Implementation")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--test-services", action="store_true", help="Test all services and exit")
    parser.add_argument("--preload-phrases", action="store_true", help="Preload common TTS phrases")
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        settings.DEBUG = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test services if requested
    if args.test_services:
        result = asyncio.run(test_all_services())
        sys.exit(0 if result else 1)
    
    # Print startup info
    print_startup_info()
    
    # Preload phrases if requested
    if args.preload_phrases:
        asyncio.run(preload_common_phrases())
    
    # Start the FastAPI application
    try:
        import uvicorn
        from app.main import app
        
        logger.info(f"🚀 Starting server on {args.host}:{args.port}")
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=settings.DEBUG,
            log_level="info" if not settings.DEBUG else "debug"
        )
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 