"""
base agent classes for llm_convo
"""
import logging
from typing import Optional
from llm_convo.audio_output import GoogleTTS
import os


class ChatAgent:
    """base class for chat agents"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """start the agent"""
        pass
    
    def get_response(self, transcript: list) -> str:
        """get response from the agent"""
        raise NotImplementedError("Subclasses must implement get_response")


class TwilioCaller(ChatAgent):
    """agent that handles twilio phone calls"""
    
    def __init__(self, session, tts: Optional[GoogleTTS] = None, thinking_phrase: str = "OK"):
        super().__init__()
        self.session = session
        self.tts = tts or GoogleTTS()
        self.thinking_phrase = thinking_phrase
    
    def _say(self, text: str):
        """convert text to speech and play via twilio"""
        try:
            key, path = self.session.get_audio_fn_and_key(text)
            if not os.path.exists(path):
                self.tts.text_to_speech(text, path)
            
            duration = self.tts.get_audio_duration(path)
            self.session.play(key, duration)
            
        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {e}")
    
    def get_response(self, transcript: list) -> str:
        """get user response via speech-to-text"""
        if len(transcript) > 0:
            self._say(transcript[-1])
        
        user_response = self.session.sst_stream.get_transcription()
        
        self._say(self.thinking_phrase)
        
        return user_response 