import asyncio
import logging
import json
from typing import Optional, Callable, Dict, Any
from deepgram import DeepgramClient, PrerecordedOptions, LiveTranscriptionEvents, LiveOptions
from pathlib import Path
import sys
import io
import wave

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class DeepgramSTTClient:
    """Client for Deepgram real-time speech-to-text"""
    
    def __init__(self):
        if not settings.DEEPGRAM_API_KEY or settings.DEEPGRAM_API_KEY.startswith("test_"):
            logger.warning("⚠️ Using mock Deepgram STT client (no valid API key)")
            self.client = None
            self.mock_mode = True
        else:
            try:
                self.client = DeepgramClient(settings.DEEPGRAM_API_KEY)
                self.mock_mode = False
                logger.info("✅ Deepgram STT client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Deepgram client: {e}. Using mock mode.")
                self.client = None
                self.mock_mode = True
        self.active_connections: Dict[str, Any] = {}
    
    async def create_live_transcription(self, session_id: str, on_transcript: Callable[[str, bool], None]) -> Optional[Any]:
        """Create a live transcription connection"""
        try:
            logger.info(f"🎤 Creating live transcription for session {session_id}")
            
            if self.mock_mode:
                # Mock connection object
                mock_connection = {
                    "session_id": session_id,
                    "status": "connected",
                    "on_transcript": on_transcript
                }
                self.active_connections[session_id] = mock_connection
                logger.info(f"✅ Mock live transcription started for session {session_id}")
                return mock_connection
            
            # Configure live transcription options
            options = LiveOptions(
                model="nova-2",  # Latest and most accurate
                language="en-US",
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,  # 1 second silence to end utterance
                vad_events=True,  # Voice activity detection
                punctuate=True,
                profanity_filter=False,
                redact=False
            )
            
            # Create live transcription connection
            dg_connection = self.client.listen.websocket.v("1")
            
            # Set up event handlers
            def on_message(self, result, **kwargs):
                try:
                    transcript = result.channel.alternatives[0].transcript
                    is_final = result.is_final
                    
                    if transcript.strip():
                        logger.info(f"🎤 Transcript ({'final' if is_final else 'interim'}): {transcript}")
                        on_transcript(transcript, is_final)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing transcript: {e}")
            
            def on_metadata(self, metadata, **kwargs):
                logger.debug(f"📊 Metadata: {metadata}")
            
            def on_speech_started(self, speech_started, **kwargs):
                logger.debug("🗣️ Speech started")
            
            def on_utterance_end(self, utterance_end, **kwargs):
                logger.debug("🔚 Utterance ended")
            
            def on_error(self, error, **kwargs):
                logger.error(f"❌ Deepgram error: {error}")
            
            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            
            # Start the connection
            await dg_connection.start(options)
            
            # Store the connection
            self.active_connections[session_id] = dg_connection
            
            logger.info(f"✅ Live transcription started for session {session_id}")
            return dg_connection
            
        except Exception as e:
            logger.error(f"❌ Error creating live transcription: {e}")
            return None
    
    async def send_audio_data(self, session_id: str, audio_data: bytes):
        """Send audio data to live transcription"""
        try:
            connection = self.active_connections.get(session_id)
            if connection:
                if self.mock_mode:
                    # Simulate transcription result
                    mock_transcript = "This is a mock transcription result"
                    if connection.get("on_transcript"):
                        connection["on_transcript"](mock_transcript, True)
                    logger.debug(f"📝 Mock transcription: {mock_transcript}")
                else:
                    # Convert mulaw to linear PCM if needed (SignalWire sends mulaw)
                    pcm_audio = self._convert_mulaw_to_pcm(audio_data)
                    await connection.send(pcm_audio)
            else:
                logger.warning(f"⚠️ No active connection for session {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error sending audio data: {e}")
    
    async def close_transcription(self, session_id: str):
        """Close live transcription connection"""
        try:
            connection = self.active_connections.get(session_id)
            if connection:
                if not self.mock_mode:
                    await connection.finish()
                del self.active_connections[session_id]
                logger.info(f"🔌 Closed transcription for session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error closing transcription: {e}")
    
    def _convert_mulaw_to_pcm(self, mulaw_data: bytes) -> bytes:
        """Convert mulaw audio to linear PCM for Deepgram"""
        try:
            import audioop
            # Convert mulaw to linear PCM (16-bit)
            linear_data = audioop.ulaw2lin(mulaw_data, 2)
            return linear_data
        except Exception as e:
            logger.error(f"❌ Error converting audio format: {e}")
            return mulaw_data  # Return original if conversion fails
    
    async def transcribe_audio_file(self, audio_data: bytes, audio_format: str = "wav") -> Optional[str]:
        """Transcribe audio file (for batch processing)"""
        try:
            logger.info(f"🎤 Transcribing audio file ({len(audio_data)} bytes)")
            
            if self.mock_mode:
                mock_transcript = "This is a mock transcription of the audio file"
                logger.info(f"📝 Mock transcription result: {mock_transcript}")
                return mock_transcript
            
            # Configure prerecorded options
            options = PrerecordedOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                punctuate=True,
                profanity_filter=False,
                utterances=True
            )
            
            # Create payload
            payload = {
                "buffer": audio_data,
                "mimetype": f"audio/{audio_format}"
            }
            
            # Transcribe
            response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)
            
            # Extract transcript
            if response.results and response.results.channels:
                transcript = response.results.channels[0].alternatives[0].transcript
                logger.info(f"📝 Transcription result: {transcript}")
                return transcript.strip()
            else:
                logger.warning("⚠️ No transcription results")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error transcribing audio file: {e}")
            return None
    
    async def create_audio_buffer_transcriber(self, session_id: str, buffer_duration_ms: int = 2000) -> 'AudioBufferTranscriber':
        """Create an audio buffer transcriber for handling chunks"""
        return AudioBufferTranscriber(self, session_id, buffer_duration_ms)
    
    def get_connection_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of transcription connection"""
        connection = self.active_connections.get(session_id)
        return {
            "session_id": session_id,
            "connected": connection is not None,
            "active_connections": len(self.active_connections),
            "mode": "mock" if self.mock_mode else "real"
        }
    
    async def test_transcription(self) -> bool:
        """Test Deepgram transcription with a sample"""
        try:
            if self.mock_mode:
                logger.info("🧪 Testing mock Deepgram transcription...")
                test_audio = b"mock_audio_data"
                result = await self.transcribe_audio_file(test_audio, "wav")
                success = result is not None
                if success:
                    logger.info("✅ Mock Deepgram transcription test successful")
                else:
                    logger.error("❌ Mock Deepgram transcription test failed")
                return success
            
            # Create a simple test audio (sine wave)
            test_audio = self._generate_test_audio()
            result = await self.transcribe_audio_file(test_audio, "wav")
            
            success = result is not None
            if success:
                logger.info("✅ Deepgram transcription test successful")
            else:
                logger.error("❌ Deepgram transcription test failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Deepgram test error: {e}")
            return False
    
    def _generate_test_audio(self) -> bytes:
        """Generate a simple test audio file"""
        try:
            import math
            import struct
            
            # Generate 1 second of silence (for testing connectivity)
            sample_rate = 16000
            duration = 1.0
            samples = int(sample_rate * duration)
            
            # Create WAV file in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Write silence
                for i in range(samples):
                    wav_file.writeframes(struct.pack('<h', 0))
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"❌ Error generating test audio: {e}")
            return b""

class AudioBufferTranscriber:
    """Helper class for buffering audio and transcribing in chunks"""
    
    def __init__(self, deepgram_client: DeepgramSTTClient, session_id: str, buffer_duration_ms: int = 2000):
        self.deepgram_client = deepgram_client
        self.session_id = session_id
        self.buffer_duration_ms = buffer_duration_ms
        self.audio_buffer = bytearray()
        self.sample_rate = 8000  # SignalWire default
        self.bytes_per_sample = 2  # 16-bit audio
        self.buffer_size_bytes = int((buffer_duration_ms / 1000.0) * self.sample_rate * self.bytes_per_sample)
        
        self.last_transcript = ""
        self.is_speaking = False
        
        logger.info(f"📦 Audio buffer transcriber created (buffer size: {self.buffer_size_bytes} bytes)")
    
    async def add_audio_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Add audio chunk to buffer and transcribe when ready"""
        try:
            self.audio_buffer.extend(audio_chunk)
            
            # If buffer is full, transcribe it
            if len(self.audio_buffer) >= self.buffer_size_bytes:
                transcript = await self._transcribe_buffer()
                self.audio_buffer.clear()
                return transcript
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error adding audio chunk: {e}")
            return None
    
    async def _transcribe_buffer(self) -> Optional[str]:
        """Transcribe the current buffer"""
        try:
            if len(self.audio_buffer) == 0:
                return None
            
            # Convert buffer to WAV format
            wav_data = self._create_wav_from_buffer(bytes(self.audio_buffer))
            
            # Transcribe
            transcript = await self.deepgram_client.transcribe_audio_file(wav_data, "wav")
            
            if transcript and transcript.strip():
                self.last_transcript = transcript.strip()
                return self.last_transcript
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error transcribing buffer: {e}")
            return None
    
    def _create_wav_from_buffer(self, audio_data: bytes) -> bytes:
        """Create WAV file from raw audio buffer"""
        try:
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(self.bytes_per_sample)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"❌ Error creating WAV from buffer: {e}")
            return b""
    
    async def flush_buffer(self) -> Optional[str]:
        """Flush remaining buffer and transcribe"""
        if len(self.audio_buffer) > 0:
            transcript = await self._transcribe_buffer()
            self.audio_buffer.clear()
            return transcript
        return None

# Create singleton instance
deepgram_client = DeepgramSTTClient() 
