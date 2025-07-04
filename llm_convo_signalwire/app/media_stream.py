import json
import base64
import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class MediaStreamHandler:
    """Handle real-time audio media streams from SignalWire"""
    
    def __init__(self):
        self.active_sessions: Dict[str, 'CallSession'] = {}
        logger.info("✅ Media stream handler initialized")
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle incoming WebSocket connection from SignalWire"""
        await websocket.accept()
        logger.info("🔌 Media stream WebSocket connected")
        
        session = None
        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    event = data.get('event')
                    
                    if event == 'connected':
                        logger.info("📡 Media stream protocol connected")
                        
                    elif event == 'start':
                        # Create new call session
                        session = CallSession(websocket, data)
                        self.active_sessions[session.call_sid] = session
                        logger.info(f"🎬 Call session started: {session.call_sid}")
                        await session.start()
                        
                    elif event == 'media':
                        # Process incoming audio data
                        if session:
                            await session.process_media(data)
                        
                    elif event == 'stop':
                        logger.info("🛑 Media stream stopped")
                        if session:
                            await session.stop()
                            if session.call_sid in self.active_sessions:
                                del self.active_sessions[session.call_sid]
                        break
                        
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Invalid JSON received: {message[:100]}...")
                except Exception as e:
                    logger.error(f"❌ Error processing media message: {e}")
                    
        except WebSocketDisconnect:
            logger.info("🔌 Media stream WebSocket disconnected")
        except Exception as e:
            logger.error(f"❌ Media stream error: {e}")
        finally:
            if session and session.call_sid in self.active_sessions:
                await session.cleanup()
                del self.active_sessions[session.call_sid]
    
    def get_session(self, call_sid: str) -> Optional['CallSession']:
        """Get active call session by SID"""
        return self.active_sessions.get(call_sid)
    
    async def send_audio_to_call(self, call_sid: str, audio_data: bytes):
        """Send audio data to a specific call"""
        session = self.get_session(call_sid)
        if session:
            await session.send_audio(audio_data)
        else:
            logger.warning(f"⚠️ No active session found for call {call_sid}")


class CallSession:
    """Manages individual call session with real-time audio processing"""
    
    def __init__(self, websocket: WebSocket, start_data: Dict[str, Any]):
        self.websocket = websocket
        self.call_sid = start_data['start']['callSid']
        self.account_sid = start_data['start']['accountSid']
        self.stream_sid = start_data['start']['streamSid']
        
        # Call metadata
        self.caller_phone = None
        self.start_time = None
        
        # Audio processing
        self.audio_buffer = bytearray()
        self.sequence_number = 0
        
        # Service integrations (will be initialized later)
        self.deepgram_client = None
        self.groq_client = None
        self.polly_client = None
        self.places_client = None
        
        # Conversation state
        self.conversation_state = "greeting"  # greeting, listening, processing, responding
        self.current_transcript = ""
        self.business_search_results = []
        
        logger.info(f"📞 Call session created for {self.call_sid}")
    
    async def start(self):
        """Initialize the call session and services"""
        try:
            # TODO: Initialize service clients
            # self.deepgram_client = DeepgramClient()
            # self.groq_client = GroqClient()
            # self.polly_client = PollyClient()
            # self.places_client = PlacesClient()
            
            logger.info(f"🚀 Call session {self.call_sid} started successfully")
            
            # Start listening for audio
            self.conversation_state = "listening"
            
        except Exception as e:
            logger.error(f"❌ Error starting call session {self.call_sid}: {e}")
    
    async def process_media(self, media_data: Dict[str, Any]):
        """Process incoming audio media data"""
        try:
            media = media_data.get('media', {})
            payload = media.get('payload')
            
            if payload:
                # Decode audio data (mulaw format from SignalWire)
                audio_chunk = base64.b64decode(payload)
                self.audio_buffer.extend(audio_chunk)
                
                # Process audio when we have enough data (e.g., 160ms chunks)
                if len(self.audio_buffer) >= 320:  # 160ms at 8kHz, 16-bit
                    await self._process_audio_chunk()
                    self.audio_buffer.clear()
                    
        except Exception as e:
            logger.error(f"❌ Error processing media data: {e}")
    
    async def _process_audio_chunk(self):
        """Process accumulated audio chunk for STT"""
        try:
            if self.conversation_state == "listening":
                # TODO: Send audio to Deepgram for real-time transcription
                # transcript = await self.deepgram_client.transcribe(self.audio_buffer)
                # if transcript:
                #     await self._handle_transcript(transcript)
                pass
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk: {e}")
    
    async def _handle_transcript(self, transcript: str):
        """Handle completed transcript from STT"""
        try:
            logger.info(f"👤 User said: {transcript}")
            self.current_transcript = transcript
            
            if self.conversation_state == "listening":
                self.conversation_state = "processing"
                
                # TODO: Process with Groq LLM
                # response = await self._process_with_llm(transcript)
                # await self._generate_response(response)
                
        except Exception as e:
            logger.error(f"❌ Error handling transcript: {e}")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data back to the caller via WebSocket"""
        try:
            # Convert audio to base64 and send as media message
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            media_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_b64
                }
            }
            
            await self.websocket.send_text(json.dumps(media_message))
            
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
    
    async def stop(self):
        """Stop the call session"""
        try:
            logger.info(f"🛑 Stopping call session {self.call_sid}")
            self.conversation_state = "ended"
            
            # TODO: Cleanup service connections
            # if self.deepgram_client:
            #     await self.deepgram_client.close()
            
        except Exception as e:
            logger.error(f"❌ Error stopping call session: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            logger.info(f"🧹 Cleaning up call session {self.call_sid}")
            
            # Clear buffers
            self.audio_buffer.clear()
            
            # TODO: Close service connections
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

# Create global instance
media_stream_handler = MediaStreamHandler() 