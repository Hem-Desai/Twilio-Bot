"""
llm_convo: ai-powered conversation system with twilio integration

a complete ai phone bot system supporting:
- live transcription and tts
- database storage of conversations  
- web dashboard for monitoring
- multiple ai providers (groq, openai)
- twilio phone integration
"""

__version__ = "0.1.0"

# Import main classes for easy access
from .agents import ChatAgent
from .database import DatabaseManager
from .enhanced_conversation import ConversationLogger

__all__ = [
    "ChatAgent",
    "DatabaseManager", 
    "ConversationLogger"
] 