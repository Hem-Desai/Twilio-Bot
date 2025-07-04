from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path

# Import our configuration
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="SignalWire-based AI call assistant with business search and forwarding"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create audio directory if it doesn't exist
os.makedirs(settings.AUDIO_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    
    # Validate required environment variables
    try:
        settings.validate_required_vars()
        logger.info("✅ All required environment variables are set")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    
    logger.info(f"🎯 Ready to handle calls on SignalWire")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "signalwire_configured": bool(settings.SIGNALWIRE_PROJECT_ID)
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "signalwire": bool(settings.SIGNALWIRE_PROJECT_ID and settings.SIGNALWIRE_TOKEN),
            "groq": bool(settings.GROQ_API_KEY),
            "deepgram": bool(settings.DEEPGRAM_API_KEY),
            "google_places": bool(settings.GOOGLE_PLACES_API_KEY),
            "aws": bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        }
    }

# Import our handlers
from .webhooks import signalwire_handler
from .media_stream import media_stream_handler

# SignalWire webhook endpoints
@app.post("/webhook/incoming-call")
async def handle_incoming_call(request: Request):
    """Handle incoming SignalWire call webhook"""
    return await signalwire_handler.handle_incoming_call(request)

@app.post("/webhook/call-status")
async def handle_call_status(request: Request):
    """Handle call status updates from SignalWire"""
    return await signalwire_handler.handle_call_status(request)

@app.websocket("/ws/media-stream")
async def websocket_endpoint(websocket: WebSocket):
    """Handle SignalWire media stream WebSocket"""
    await media_stream_handler.handle_websocket(websocket)

# Call management endpoints
@app.post("/api/forward-call/{call_sid}")
async def forward_call(call_sid: str, request: Request):
    """Forward a call to a target phone number"""
    data = await request.json()
    target_phone = data.get("target_phone")
    
    if not target_phone:
        return {"error": "target_phone is required"}
    
    success = signalwire_handler.forward_call(call_sid, target_phone)
    return {"success": success, "call_sid": call_sid, "target_phone": target_phone}

@app.post("/api/hangup-call/{call_sid}")
async def hangup_call(call_sid: str):
    """Hangup a call"""
    success = signalwire_handler.hangup_call(call_sid)
    return {"success": success, "call_sid": call_sid}

@app.get("/api/active-sessions")
async def get_active_sessions():
    """Get list of active call sessions"""
    sessions = list(media_stream_handler.active_sessions.keys())
    return {"active_sessions": sessions, "count": len(sessions)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    ) 