from fastapi import Request, Response, HTTPException
from signalwire.rest import Client
import logging
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class SignalWireWebhookHandler:
    """Handle SignalWire webhooks for incoming calls and media streams"""
    
    def __init__(self):
        self.client = Client(
            project=settings.SIGNALWIRE_PROJECT_ID,
            token=settings.SIGNALWIRE_TOKEN,
            signalwire_space_url=settings.SIGNALWIRE_SPACE_URL
        )
        logger.info("✅ SignalWire client initialized")
    
    async def handle_incoming_call(self, request: Request) -> Response:
        """Handle incoming call webhook from SignalWire"""
        try:
            # Get form data from SignalWire webhook
            form_data = await request.form()
            call_data = dict(form_data)
            
            logger.info(f"📞 Incoming call from {call_data.get('From', 'Unknown')}")
            logger.info(f"📋 Call SID: {call_data.get('CallSid', 'Unknown')}")
            
            # Extract call information
            caller_phone = call_data.get('From')
            call_sid = call_data.get('CallSid')
            to_phone = call_data.get('To')
            
            # Generate TwiML response to start media stream
            twiml_response = self._generate_media_stream_twiml()
            
            logger.info(f"🔊 Starting media stream for call {call_sid}")
            
            return Response(
                content=twiml_response,
                media_type="application/xml"
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling incoming call: {e}")
            # Return error TwiML to prevent call from hanging
            error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, there was a system error. Please try again later.</Say>
    <Hangup/>
</Response>"""
            return Response(content=error_twiml, media_type="application/xml")
    
    def _generate_media_stream_twiml(self) -> str:
        """Generate TwiML to start bidirectional media stream"""
        # Determine WebSocket URL based on environment
        if settings.DEBUG:
            ws_url = f"wss://{settings.DOMAIN}/ws/media-stream"
        else:
            ws_url = f"wss://{settings.DOMAIN}/ws/media-stream"
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! I am your business directory assistant. Please wait while I connect you.</Say>
    <Start>
        <Stream url="{ws_url}">
            <Parameter name="track">both</Parameter>
        </Stream>
    </Start>
    <Say voice="alice">What type of business are you looking for and in which area?</Say>
    <Pause length="60"/>
</Response>"""
        
        logger.info(f"📡 Generated TwiML with WebSocket URL: {ws_url}")
        return twiml
    
    async def handle_call_status(self, request: Request) -> Response:
        """Handle call status updates from SignalWire"""
        try:
            form_data = await request.form()
            status_data = dict(form_data)
            
            call_status = status_data.get('CallStatus')
            call_sid = status_data.get('CallSid')
            
            logger.info(f"📞 Call {call_sid} status: {call_status}")
            
            # Log different call statuses
            if call_status == 'completed':
                logger.info(f"✅ Call {call_sid} completed successfully")
            elif call_status == 'failed':
                logger.warning(f"❌ Call {call_sid} failed")
            elif call_status == 'busy':
                logger.info(f"📞 Call {call_sid} was busy")
            elif call_status == 'no-answer':
                logger.info(f"📞 Call {call_sid} was not answered")
            
            return Response(content="OK", status_code=200)
            
        except Exception as e:
            logger.error(f"❌ Error handling call status: {e}")
            return Response(content="Error", status_code=500)
    
    def forward_call(self, call_sid: str, target_phone: str) -> bool:
        """Forward an active call to a target phone number"""
        try:
            logger.info(f"📞 Forwarding call {call_sid} to {target_phone}")
            
            # Create TwiML for call forwarding
            forward_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connecting you now. Please hold.</Say>
    <Dial timeout="30" record="false">
        <Number>{target_phone}</Number>
    </Dial>
    <Say voice="alice">I'm sorry, that number appears to be unavailable. Please try calling them directly.</Say>
</Response>"""
            
            # Update the call with forwarding TwiML
            call = self.client.calls(call_sid).update(twiml=forward_twiml)
            
            logger.info(f"✅ Call forwarding initiated for {call_sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Call forwarding failed for {call_sid}: {e}")
            return False
    
    def hangup_call(self, call_sid: str) -> bool:
        """Hangup an active call"""
        try:
            logger.info(f"📞 Hanging up call {call_sid}")
            
            call = self.client.calls(call_sid).update(status='completed')
            
            logger.info(f"✅ Call {call_sid} hung up successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error hanging up call {call_sid}: {e}")
            return False

# Create global instance
signalwire_handler = SignalWireWebhookHandler() 