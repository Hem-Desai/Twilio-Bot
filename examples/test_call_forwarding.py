#!/usr/bin/env python3
"""
Call Forwarding System Test Script

This script helps you test your call forwarding setup without making actual phone calls.
It verifies that all APIs are working correctly and simulates the business search process.

Usage:
    python examples/test_call_forwarding.py

This will test:
- Groq API connection (AI conversation)
- Google Places API (business search)
- Intent extraction
- Business selection logic
"""

import os
import sys
import asyncio
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_environment():
    """Load environment variables"""
    try:
        from llm_convo.env_utils import load_env_file
        load_env_file()
        print("✅ Environment loaded from .env file")
    except ImportError:
        print("⚠️ Using system environment variables")

def test_groq_api():
    """Test Groq API connection"""
    print("\n🤖 Testing Groq API...")
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": "Say 'Hello World'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Groq API working! Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return False

def test_google_places_api():
    """Test Google Places API connection"""
    print("\n🗺️ Testing Google Places API...")
    
    google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not google_api_key:
        print("❌ GOOGLE_PLACES_API_KEY not found in environment")
        return False
    
    try:
        import googlemaps
        gmaps = googlemaps.Client(key=google_api_key)
        
        # Test with a simple search
        results = gmaps.places(
            query="restaurant in Mumbai",
            type='establishment',
            language='en'
        )
        
        if results['status'] == 'OK' and results['results']:
            business_count = len(results['results'])
            print(f"✅ Google Places API working! Found {business_count} results")
            return True
        else:
            print(f"❌ Google Places API returned: {results['status']}")
            return False
            
    except Exception as e:
        print(f"❌ Google Places API error: {e}")
        return False

async def test_business_search():
    """Test the business search service"""
    print("\n🔍 Testing Business Search Service...")
    
    try:
        from llm_convo.business_search import BusinessSearchService
        
        service = BusinessSearchService()
        results = await service.search_businesses("restaurant", "Mumbai", max_results=2)
        
        if results:
            print(f"✅ Business search working! Found {len(results)} businesses:")
            for i, business in enumerate(results, 1):
                print(f"   {i}. {business['name']} - {business['phone']}")
            return True
        else:
            print("❌ No businesses found in search")
            return False
            
    except Exception as e:
        print(f"❌ Business search error: {e}")
        return False

async def test_intent_extraction():
    """Test the intent extraction"""
    print("\n🧠 Testing Intent Extraction...")
    
    try:
        from llm_convo.business_search import IntentExtractor
        
        extractor = IntentExtractor()
        
        test_queries = [
            "I need a dentist in Mumbai",
            "Find me a restaurant in Delhi",
            "What's the weather like?",
            "I want a mechanic near me"
        ]
        
        for query in test_queries:
            intent = await extractor.extract_intent(query)
            is_business = intent.get('is_business_request', False)
            confidence = intent.get('confidence', 0)
            service_type = intent.get('service_type', 'N/A')
            location = intent.get('location', 'N/A')
            
            status = "✅" if is_business and confidence > 0.5 else "⚠️"
            print(f"   {status} '{query}' → Business: {is_business}, Confidence: {confidence:.2f}")
            print(f"      Service: {service_type}, Location: {location}")
        
        print("✅ Intent extraction working!")
        return True
        
    except Exception as e:
        print(f"❌ Intent extraction error: {e}")
        return False

async def test_end_to_end():
    """Test the complete business directory bot"""
    print("\n🎯 Testing End-to-End Business Directory...")
    
    try:
        from llm_convo.business_search import BusinessDirectoryBot
        
        bot = BusinessDirectoryBot()
        
        test_query = "I need a dentist in Mumbai"
        print(f"Testing query: '{test_query}'")
        
        response, businesses, should_forward = await bot.process_request(test_query)
        
        print(f"Response: {response[:100]}{'...' if len(response) > 100 else ''}")
        print(f"Found {len(businesses)} businesses, Should forward: {should_forward}")
        
        if businesses:
            print("✅ End-to-end test successful!")
            
            # Test business selection
            if len(businesses) > 1:
                selected = bot.select_business("1", businesses)
                if selected:
                    print(f"✅ Business selection working! Selected: {selected['name']}")
                else:
                    print("⚠️ Business selection had issues")
        else:
            print("⚠️ No businesses found in end-to-end test")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test error: {e}")
        return False

def test_database():
    """Test database connectivity"""
    print("\n💾 Testing Database...")
    
    try:
        from llm_convo.database import DatabaseManager
        
        db = DatabaseManager()
        
        # Test creating a conversation
        test_call_sid = f"test_call_{int(asyncio.get_event_loop().time())}"
        conversation = db.create_conversation(test_call_sid, "+1234567890")
        
        if conversation:
            print(f"✅ Database working! Created test conversation: {conversation.id}")
            
            # Test adding a message
            message = db.add_message(conversation.id, "user", "Test message")
            if message:
                print(f"✅ Message logging working! Message ID: {message.id}")
            
            # Clean up
            db.end_conversation(conversation.id)
            return True
        else:
            print("❌ Failed to create test conversation")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Call Forwarding System Test Suite")
    print("=====================================")
    
    # Setup environment
    setup_environment()
    
    # Run tests
    tests = [
        ("Groq API", test_groq_api),
        ("Google Places API", test_google_places_api),
        ("Business Search", test_business_search),
        ("Intent Extraction", test_intent_extraction),
        ("End-to-End Flow", test_end_to_end),
        ("Database", test_database)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your call forwarding system is ready!")
        print("\n🚀 Next steps:")
        print("1. Run: python examples/call_forwarding_bot.py --start_ngrok")
        print("2. Set up Twilio webhook with the ngrok URL")
        print("3. Call your Twilio number and test live!")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check your configuration:")
        print("1. Verify your .env file has all required API keys")
        print("2. Check API key permissions and quotas")
        print("3. Ensure internet connectivity")
        print("4. Review the error messages above")

if __name__ == "__main__":
    asyncio.run(main()) 