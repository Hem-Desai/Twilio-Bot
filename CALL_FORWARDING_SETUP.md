# 🤖 AI Call Forwarding System Setup Guide

This guide will help you set up a complete AI call forwarding system that can find businesses in real-time and connect callers directly to them.

## 🎯 System Overview

Your call forwarding system will:

- Listen for business requests like "I need a dentist in Mumbai"
- Search for businesses in real-time using Google Places API
- Present options with ratings and hours
- Forward calls directly to selected businesses
- Log all interactions for monitoring

## 📋 Prerequisites

1. **Python 3.8+** - Check with `python --version`
2. **Active internet connection** - For API calls
3. **Phone for testing** - To call your system

## 🔧 Required API Keys

### 1. Groq API Key (FREE) ⭐

**Purpose**: Powers the AI conversation (completely free!)

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up (no credit card required)
3. Go to "API Keys" section
4. Create a new API key
5. Copy the key (starts with `gsk_`)

### 2. Google Places API Key 🗺️

**Purpose**: Real-time business search

1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the "Places API"
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy the API key
6. **Important**: Google gives $200 free credit monthly (covers ~4000 searches)

### 3. Twilio Account 📞

**Purpose**: Handle phone calls and forwarding

1. Sign up at [Twilio](https://www.twilio.com/try-twilio)
2. Get $15 free trial credit
3. Buy a phone number (~$1/month)
4. From the Console Dashboard, copy:
   - Account SID (starts with `AC`)
   - Auth Token
   - Phone Number (format: `+1xxxxxxxxxx`)

## 🚀 Installation Steps

### Step 1: Clone and Install

```bash
git clone <your-repo>
cd llm_convo
pip install -r requirements.txt
```

### Step 2: Create .env File

Create a `.env` file in the project root:

```bash
# AI Configuration (FREE)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Business Search
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here

# Phone Service
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Optional: Default location for "near me" searches
DEFAULT_SEARCH_LOCATION=Mumbai
```

### Step 3: Test the System

```bash
# Start the call forwarding service
python examples/call_forwarding_bot.py --preload_whisper --start_ngrok

# For existing phone bot with call forwarding:
python examples/groq_phone_bot.py --bot_type call_forwarding --start_ngrok
```

### Step 4: Configure Twilio Webhook

1. Copy the ngrok URL from the terminal (e.g., `https://abc123.ngrok.io`)
2. Go to your Twilio Console → Phone Numbers
3. Click on your phone number
4. Set the webhook URL to: `https://abc123.ngrok.io/incoming-voice`
5. Save configuration

### Step 5: Test with Phone Call

Call your Twilio phone number and try:

- "I need a dentist in Mumbai"
- "Find me a restaurant in Delhi"
- "I want a mechanic near me"

## 🎯 Usage Examples

### Basic Business Search

**Caller**: "I need a dentist in Ahmedabad"

**System Response**:

```
I found 3 dentist options in Ahmedabad:
1. City Dental Care (4.5 stars) - Open now
2. Smile Clinic (4.2 stars) - Open now
3. Perfect Dental (4.0 stars) - Closed now

Which one would you like me to connect you to?
```

**Caller**: "Connect me to number 1"

**System**: "Connecting you to City Dental Care now. Please hold..."

### Emergency Services

**Caller**: "I need a hospital in Mumbai"

**System**: Searches and connects to nearest available hospital

### Restaurant Recommendations

**Caller**: "Find me a good restaurant nearby"

**System**: "I can help you find a restaurant. Which city should I search in?"

## 🏗️ System Architecture

```
📞 Incoming Call → 🤖 Groq AI → 🔍 Google Places → 📋 Present Options → 🔄 Forward Call
                     ↓
                 💾 Database Logging
                     ↓
                 📊 Web Dashboard
```

## 🔧 Configuration Options

### Bot Types Available

- `call_forwarding` - Business search and call forwarding
- `customer_service` - General customer service
- `appointment` - Appointment scheduling
- `general` - General purpose assistant
- `pizza` - Pizza ordering bot

### Running Different Bots

```bash
# Call forwarding bot (main feature)
python examples/groq_phone_bot.py --bot_type call_forwarding --start_ngrok

# Customer service bot
python examples/groq_phone_bot.py --bot_type customer_service --start_ngrok

# General assistant
python examples/groq_phone_bot.py --bot_type general --start_ngrok
```

### Command Line Options

```bash
python examples/call_forwarding_bot.py \
    --port 8091 \                    # Port to run on
    --start_ngrok \                  # Create public tunnel
    --preload_whisper \              # Preload speech model
    --dashboard_port 5000            # Dashboard port
```

## 📊 Monitoring and Dashboard

### Web Dashboard

- Access at: `http://localhost:5000`
- View all conversations
- Monitor call forwarding statistics
- Track business search requests

### Database

- Conversations stored in `conversations.db`
- Full conversation history
- Business search logs
- Call forwarding success rates

## 🔒 Security Best Practices

1. **API Key Security**

   - Never commit `.env` file to version control
   - Use environment variables in production
   - Rotate API keys regularly

2. **Business Verification**

   - System uses Google Places verified businesses
   - Includes ratings and reviews
   - Shows business hours and status

3. **Call Logging**
   - All conversations logged for quality
   - Personal data handled securely
   - GDPR compliance considerations

## 💰 Cost Breakdown

### Free Tier Limits

- **Groq API**: Completely FREE (generous limits)
- **Google Places**: $200 monthly credit = ~4000 searches
- **Twilio**: $15 trial credit + ~$1/month for phone number

### Estimated Monthly Costs

- **Low usage** (< 100 calls): ~$1-2/month
- **Medium usage** (500 calls): ~$5-10/month
- **High usage** (2000+ calls): ~$20-50/month

## 🐛 Troubleshooting

### Common Issues

**"No businesses found"**

- Check Google Places API key
- Verify API is enabled in Google Cloud Console
- Check if location is valid

**"Call forwarding failed"**

- Verify Twilio credentials
- Check webhook URL is correct
- Ensure phone number format is correct

**"Groq API error"**

- Check API key is valid
- Verify internet connection
- Check rate limits

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python examples/call_forwarding_bot.py --start_ngrok
```

### Testing Without Phone

```bash
# Test business search functionality
python -c "
from llm_convo.business_search import create_business_directory_service
import asyncio

bot = create_business_directory_service()
result = asyncio.run(bot.process_request('I need a dentist in Mumbai'))
print(result)
"
```

## 🚀 Deployment Options

### Local Development

- Use ngrok for public access
- Perfect for testing and development

### Cloud Deployment (Railway)

```bash
# Deploy to Railway (free tier available)
railway login
railway init
railway deploy
```

### Cloud Deployment (Heroku)

```bash
# Deploy to Heroku
heroku create your-app-name
git push heroku main
```

## 📞 Support

Need help? Check:

1. This setup guide
2. Example scripts in `examples/`
3. API documentation for Groq, Google Places, and Twilio
4. GitHub issues for common problems

## 🎉 What's Next?

Once your system is running, you can:

1. Customize the AI prompts for your specific use case
2. Add more business categories
3. Integrate with your existing systems
4. Scale to handle more concurrent calls
5. Add analytics and reporting features

Happy call forwarding! 🤖📞
