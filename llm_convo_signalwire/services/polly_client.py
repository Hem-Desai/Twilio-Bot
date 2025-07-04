import asyncio
import logging
import hashlib
import os
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import sys
import aiofiles

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class PollyClient:
    """Client for Amazon Polly text-to-speech with caching"""
    
    def __init__(self):
        self.client = boto3.client(
            'polly',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        self.voice_id = settings.POLLY_VOICE_ID
        self.engine = settings.POLLY_ENGINE
        self.audio_dir = Path(settings.AUDIO_DIR)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ Polly client initialized with voice: {self.voice_id} ({self.engine})")
    
    async def text_to_speech(self, text: str, cache_key: Optional[str] = None) -> Optional[bytes]:
        """Convert text to speech, with caching"""
        try:
            # Generate cache key if not provided
            if not cache_key:
                cache_key = self._generate_cache_key(text)
            
            # Check cache first
            cached_audio = await self._get_cached_audio(cache_key)
            if cached_audio:
                logger.info(f"🎵 Using cached audio for: {text[:50]}...")
                return cached_audio
            
            # Generate new audio
            logger.info(f"🗣️ Generating speech for: {text[:50]}...")
            
            # Run Polly synthesis in thread pool
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                self._synthesize_speech_sync,
                text
            )
            
            if audio_data:
                # Cache the result
                await self._cache_audio(cache_key, audio_data)
                logger.info(f"✅ Generated and cached audio ({len(audio_data)} bytes)")
                return audio_data
            else:
                logger.error("❌ Failed to generate audio")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error in text-to-speech: {e}")
            return None
    
    def _synthesize_speech_sync(self, text: str) -> Optional[bytes]:
        """Synchronous Polly synthesis (runs in thread pool)"""
        try:
            # Prepare text for Polly
            cleaned_text = self._prepare_text_for_synthesis(text)
            
            # Call Polly
            response = self.client.synthesize_speech(
                Text=cleaned_text,
                OutputFormat='mp3',
                VoiceId=self.voice_id,
                Engine=self.engine,
                SampleRate='8000',  # Optimized for phone calls
                TextType='text'
            )
            
            # Extract audio data
            if 'AudioStream' in response:
                return response['AudioStream'].read()
            else:
                logger.error("❌ No audio stream in Polly response")
                return None
                
        except ClientError as e:
            logger.error(f"❌ Polly API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error synthesizing speech: {e}")
            return None
    
    def _prepare_text_for_synthesis(self, text: str) -> str:
        """Prepare text for optimal Polly synthesis"""
        # Clean up text
        cleaned = text.strip()
        
        # Remove markdown formatting
        cleaned = cleaned.replace('**', '').replace('*', '')
        
        # Handle phone numbers (add pauses)
        import re
        phone_pattern = r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        cleaned = re.sub(phone_pattern, r'+1 \1 \2 \3', cleaned)
        
        # Add pauses for better phone conversation flow
        cleaned = cleaned.replace('.', '.<break time="0.5s"/>')
        cleaned = cleaned.replace('!', '!<break time="0.5s"/>')
        cleaned = cleaned.replace('?', '?<break time="0.5s"/>')
        cleaned = cleaned.replace(',', ',<break time="0.3s"/>')
        
        # Wrap in SSML if needed
        if '<break' in cleaned or '<speak>' not in cleaned:
            cleaned = f'<speak>{cleaned}</speak>'
        
        return cleaned
    
    def _generate_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Include voice settings in cache key
        cache_input = f"{text}_{self.voice_id}_{self.engine}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    async def _get_cached_audio(self, cache_key: str) -> Optional[bytes]:
        """Get cached audio file"""
        try:
            cache_file = self.audio_dir / f"{cache_key}.mp3"
            if cache_file.exists():
                async with aiofiles.open(cache_file, 'rb') as f:
                    return await f.read()
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error reading cache: {e}")
            return None
    
    async def _cache_audio(self, cache_key: str, audio_data: bytes):
        """Cache audio file"""
        try:
            cache_file = self.audio_dir / f"{cache_key}.mp3"
            async with aiofiles.open(cache_file, 'wb') as f:
                await f.write(audio_data)
            logger.debug(f"💾 Cached audio: {cache_file}")
        except Exception as e:
            logger.warning(f"⚠️ Error caching audio: {e}")
    
    async def get_cached_audio_path(self, text: str) -> Optional[str]:
        """Get path to cached audio file (useful for serving via HTTP)"""
        cache_key = self._generate_cache_key(text)
        cache_file = self.audio_dir / f"{cache_key}.mp3"
        
        if cache_file.exists():
            return str(cache_file)
        
        # Generate audio if not cached
        audio_data = await self.text_to_speech(text, cache_key)
        if audio_data:
            return str(cache_file)
        
        return None
    
    async def preload_common_phrases(self):
        """Preload common phrases for faster response"""
        common_phrases = [
            "Hello! I'm your business directory assistant. What type of business are you looking for and in which area?",
            "Let me search for that for you.",
            "I found several options for you.",
            "Would you like me to connect you to one of these businesses?",
            "Connecting you now. Please hold.",
            "I'm sorry, I couldn't find any businesses matching your request.",
            "Could you repeat that please?",
            "Thank you for calling. Have a great day!",
            "I'm having trouble understanding. Could you speak more clearly?",
            "I'm sorry, that business appears to be unavailable."
        ]
        
        logger.info("🔄 Preloading common phrases...")
        
        tasks = []
        for phrase in common_phrases:
            tasks.append(self.text_to_speech(phrase))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if isinstance(r, bytes))
        
        logger.info(f"✅ Preloaded {successful}/{len(common_phrases)} common phrases")
    
    def clear_cache(self, older_than_days: int = 7):
        """Clear cached audio files older than specified days"""
        try:
            import time
            cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
            cleared_count = 0
            
            for audio_file in self.audio_dir.glob("*.mp3"):
                if audio_file.stat().st_mtime < cutoff_time:
                    audio_file.unlink()
                    cleared_count += 1
            
            logger.info(f"🧹 Cleared {cleared_count} cached audio files older than {older_than_days} days")
            
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            audio_files = list(self.audio_dir.glob("*.mp3"))
            total_files = len(audio_files)
            total_size = sum(f.stat().st_size for f in audio_files)
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "cache_directory": str(self.audio_dir)
            }
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return {"error": str(e)}
    
    async def test_synthesis(self) -> bool:
        """Test Polly synthesis with a simple phrase"""
        try:
            test_text = "This is a test of the text to speech system."
            result = await self.text_to_speech(test_text)
            success = result is not None and len(result) > 0
            
            if success:
                logger.info("✅ Polly synthesis test successful")
            else:
                logger.error("❌ Polly synthesis test failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Polly test error: {e}")
            return False

# Create global instance
polly_client = PollyClient() 