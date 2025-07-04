# LLM Convo SignalWire

AI-powered phone assistant with business search and call forwarding using **SignalWire + Groq + Deepgram + Amazon Polly**.

## 🚀 Features

- **Real-time conversation** via SignalWire telephony
- **Instant speech recognition** with Deepgram streaming STT
- **Ultra-fast AI responses** using Groq (Llama 3.1)
- **Natural voice synthesis** with Amazon Polly Neural
- **Business search** via Google Places API
- **Call forwarding** to found businesses
- **Redis caching** for performance optimization
- **FastAPI async architecture** for high concurrency

## 🏗️ Architecture

```
Caller → SignalWire → FastAPI → Deepgram (STT)
                              ↓
                         Groq (LLM) ← Redis Cache
                              ↓
                    Amazon Polly (TTS) → Audio Response
                              ↓
                    Google Places API (Business Search)
                              ↓
                    SignalWire (Call Forwarding)
```

## 📋 Prerequisites

1. **SignalWire Account** - [signup](https://signalwire.com) for $10 free credits
2. **Groq API Key** - [get free key](https://console.groq.com)
3. **Deepgram API Key** - [get free credits](https://deepgram.com)
4. **AWS Account** - for Amazon Polly TTS
5. **Google Places API** - [enable API](https://console.cloud.google.com)
6. **Redis** - local or cloud instance

## 🛠️ Setup Instructions

### Step 1: Clone and Setup Project

```bash
cd llm_convo_signalwire
pip install -r requirements.txt
```

### Step 2: Environment Configuration

```bash
# Copy the template
cp env.example .env

# Edit .env with your API keys
```

Required environment variables:

- `SIGNALWIRE_PROJECT_ID` - From SignalWire dashboard
- `SIGNALWIRE_TOKEN` - From SignalWire dashboard
- `SIGNALWIRE_SPACE_URL` - Your SignalWire space URL
- `GROQ_API_KEY` - From Groq console
- `DEEPGRAM_API_KEY` - From Deepgram console
- `GOOGLE_PLACES_API_KEY` - From Google Cloud console
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` - For Polly TTS

### Step 3: SignalWire Account Setup

1. **Create account** at [signalwire.com](https://signalwire.com)
2. **Get $10 free credits** (no credit card required initially)
3. **Buy a phone number** (~$1/month)
4. **Note your credentials**:
   - Project ID
   - Auth Token
   - Space URL (e.g., `yourspace.signalwire.com`)

### Step 4: Start Development Server

```bash
# Start Redis (if using local)
redis-server

# Start FastAPI app
python app/main.py
```

The app will run on `http://localhost:8000`

### Step 5: Expose with ngrok (for testing)

```bash
# Install ngrok if needed
# Start ngrok tunnel
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

### Step 6: Configure SignalWire Webhook

1. Go to SignalWire dashboard → Phone Numbers
2. Click your phone number
3. Set webhook URL to: `https://abc123.ngrok.io/webhook/incoming-call`
4. Save configuration

## 🧪 Testing

### Test Health Check

```bash
curl http://localhost:8000/health
```

### Test Phone Call

1. Call your SignalWire phone number
2. Should hear: "Hello! Call handling coming soon."
3. Check logs for webhook activity

## 📞 Expected Call Flow (When Complete)

1. **Caller dials** your SignalWire number
2. **Assistant greets**: "Hello! I'm your business directory assistant. What type of business are you looking for and in which area?"
3. **User responds**: "I need a dentist in Mumbai"
4. **System processes**:
   - Deepgram transcribes in real-time
   - Groq extracts business type + location
   - Google Places searches for results
   - Results ranked by rating/distance
5. **Assistant presents options**: "I found 3 great dentists..."
6. **User chooses**: "Connect me to number 1"
7. **System forwards call** to selected business

## 🎯 Performance Targets

- **Total Latency**: <600ms (Audio → Response)
- **Cost**: <$30 per 1000 minutes
- **Concurrency**: 50+ simultaneous calls
- **Accuracy**: >90% business search relevance

## 📁 Project Structure

```
llm_convo_signalwire/
├── app/
│   ├── main.py              # FastAPI application
│   ├── webhooks.py          # SignalWire webhooks (coming next)
│   └── static/audio/        # Cached audio files
├── services/
│   ├── groq_client.py       # LLM service (coming next)
│   ├── deepgram_client.py   # STT service (coming next)
│   ├── polly_client.py      # TTS service (coming next)
│   └── places_client.py     # Business search (coming next)
├── models/
│   └── call_session.py      # Data models (coming next)
├── config/
│   └── settings.py          # Configuration
├── deploy/                  # Deployment configs (coming next)
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🚀 Next Steps

This is **Phase 1** - basic project setup complete!

**Coming next in Phase 2**:

- SignalWire webhook implementation
- Groq LLM integration
- Deepgram streaming STT
- Amazon Polly TTS
- Google Places business search
- Call forwarding logic

## 💰 Cost Estimation

Based on 1000 minutes of calls:

- **SignalWire**: ~$10 (cheaper than Twilio)
- **Groq**: ~$0.30 (70% cheaper than OpenAI)
- **Deepgram**: ~$12 (real-time STT)
- **Polly**: ~$2 (neural voices)
- **Places API**: ~$1 (search requests)
- **Infrastructure**: ~$5 (hosting/Redis)
- **Total**: ~**$30 per 1000 minutes**

## 🐛 Troubleshooting

### Common Issues

**"Missing environment variables"**

- Check your `.env` file has all required keys
- Verify API keys are valid and have proper permissions

**"SignalWire webhook not working"**

- Ensure ngrok tunnel is running
- Check webhook URL is set correctly in SignalWire dashboard
- Verify endpoint is accessible: `curl your-ngrok-url/webhook/incoming-call`

**"Can't connect to Redis"**

- Start Redis server: `redis-server`
- Or update `REDIS_URL` for cloud Redis instance

## 📞 Support

- SignalWire Docs: [docs.signalwire.com](https://docs.signalwire.com)
- Groq API Docs: [console.groq.com/docs](https://console.groq.com/docs)
- FastAPI Docs: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
