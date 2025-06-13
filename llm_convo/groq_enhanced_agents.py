import logging
import time
from typing import Optional
from llm_convo.agents import TwilioCaller
from llm_convo.groq_agents import GroqChatWithHistory, get_recommended_model
from llm_convo.enhanced_conversation import ConversationLogger
from llm_convo.audio_output import GoogleTTS


class DatabaseLoggingGroqChat(GroqChatWithHistory):
    """Enhanced Groq Chat agent that logs to database"""
    
    def __init__(self, system_prompt: str, conversation_logger: ConversationLogger, 
                 init_phrase: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None):
        """
        Initialize Groq chat agent with database logging
        
        Args:
            system_prompt: System prompt for the AI
            conversation_logger: Logger for database storage
            init_phrase: Initial phrase to say when starting
            model: Groq model to use (default: optimized for phone calls)
            api_key: Groq API key (or set GROQ_API_KEY env var)
        """
        # Use recommended model for phone calls if not specified
        if model is None:
            model = get_recommended_model("phone")
        
        super().__init__(system_prompt, init_phrase, model, api_key)
        self.conversation_logger = conversation_logger
        self.logger = logging.getLogger(__name__)
    
    def get_response(self, transcript: list) -> str:
        start_time = time.time()
        response = super().get_response(transcript)
        duration = time.time() - start_time
        
        # Log the bot's response to database
        if response and response.strip():
            self.conversation_logger.log_message('bot', response, duration)
            self.logger.info(f"Bot response logged: {response[:50]}...")
        
        return response


class DatabaseLoggingTwilioCaller(TwilioCaller):
    """Enhanced Twilio Caller agent that logs to database (same as before)"""
    
    def __init__(self, session, conversation_logger: ConversationLogger, 
                 tts: Optional[GoogleTTS] = None, thinking_phrase: str = "OK"):
        super().__init__(session, tts, thinking_phrase)
        self.conversation_logger = conversation_logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize conversation in database when session starts
        self._init_conversation()
    
    def _init_conversation(self):
        """Initialize conversation in database"""
        try:
            # Extract call SID from session if available
            call_sid = getattr(self.session, '_call_sid', None)
            if not call_sid and hasattr(self.session, 'ws'):
                # Try to get call SID from websocket data
                call_sid = f"unknown_{int(time.time())}"
            
            # Extract caller phone if available
            caller_phone = getattr(self.session, '_caller_phone', None)
            
            self.conversation_logger.start_conversation(
                call_sid=call_sid or f"session_{int(time.time())}",
                caller_phone=caller_phone
            )
            self.logger.info(f"Initialized conversation for call {call_sid}")
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation: {e}")
    
    def get_response(self, transcript: list) -> str:
        start_time = time.time()
        
        # Play the last message from transcript (bot's message)
        if len(transcript) > 0:
            self._say(transcript[-1])
        
        # Get user's response via speech-to-text
        user_response = self.session.sst_stream.get_transcription()
        response_time = time.time() - start_time
        
        # Log user's response to database
        if user_response and user_response.strip():
            self.conversation_logger.log_message('user', user_response, response_time)
            self.logger.info(f"User response logged: {user_response[:50]}...")
        
        # Play thinking phrase
        self._say(self.thinking_phrase)
        
        return user_response


class GroqConversationBot:
    """Complete conversation bot using Groq with database logging and dashboard integration"""
    
    def __init__(self, system_prompt: str, conversation_logger: ConversationLogger,
                 init_phrase: Optional[str] = None, thinking_phrase: str = "Let me think about that...",
                 model: Optional[str] = None, api_key: Optional[str] = None):
        self.system_prompt = system_prompt
        self.conversation_logger = conversation_logger
        self.init_phrase = init_phrase or "Hello! How can I help you today?"
        self.thinking_phrase = thinking_phrase
        self.model = model or get_recommended_model("phone")
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
    
    def create_agents(self, twilio_session):
        """Create the AI and Twilio agents for a conversation"""
        
        # Create AI agent with Groq and database logging
        ai_agent = DatabaseLoggingGroqChat(
            system_prompt=self.system_prompt,
            conversation_logger=self.conversation_logger,
            init_phrase=self.init_phrase,
            model=self.model,
            api_key=self.api_key
        )
        
        # Create Twilio agent with database logging
        twilio_agent = DatabaseLoggingTwilioCaller(
            session=twilio_session,
            conversation_logger=self.conversation_logger,
            thinking_phrase=self.thinking_phrase
        )
        
        return ai_agent, twilio_agent
    
    def get_conversation_summary(self):
        """Get a summary of the current conversation"""
        if not self.conversation_logger.current_conversation:
            return None
        
        conversation = self.conversation_logger.current_conversation
        return {
            'id': conversation.id,
            'call_sid': conversation.call_sid,
            'caller_phone': conversation.caller_phone,
            'start_time': conversation.start_time,
            'status': conversation.status,
            'message_count': len(conversation.messages)
        }


# Predefined bot configurations using Groq
def create_groq_customer_service_bot(conversation_logger: ConversationLogger, api_key: Optional[str] = None):
    """Create a customer service bot using Groq"""
    return GroqConversationBot(
        system_prompt="""You are a helpful customer service representative. 
        Be polite, professional, and try to resolve customer issues efficiently. 
        Keep responses concise but friendly. Ask clarifying questions when needed.
        If you cannot help with something, politely explain and offer alternatives.
        Keep your responses under 2 sentences for phone conversations.""",
        conversation_logger=conversation_logger,
        init_phrase="Hello! Thank you for calling our customer service. How can I assist you today?",
        thinking_phrase="Let me help you with that...",
        model=get_recommended_model("phone"),
        api_key=api_key
    )


def create_groq_appointment_scheduler_bot(conversation_logger: ConversationLogger, api_key: Optional[str] = None):
    """Create an appointment scheduling bot using Groq"""
    return GroqConversationBot(
        system_prompt="""You are an appointment scheduling assistant. 
        Help customers schedule, reschedule, or cancel appointments. 
        Ask for necessary details like preferred date, time, and type of service.
        Be efficient but thorough in gathering required information.
        Confirm all details before finalizing any appointment.
        Keep responses brief and clear for phone conversations.""",
        conversation_logger=conversation_logger,
        init_phrase="Hi! I'm here to help you schedule an appointment. What type of service are you looking for?",
        thinking_phrase="Let me check the schedule...",
        model=get_recommended_model("phone"),
        api_key=api_key
    )


def create_groq_general_assistant_bot(conversation_logger: ConversationLogger, api_key: Optional[str] = None):
    """Create a general purpose assistant bot using Groq"""
    return GroqConversationBot(
        system_prompt="""You are a friendly and helpful AI assistant speaking on the phone. 
        You RESPOND to what the user says to you. Listen to their questions and provide helpful answers.
        Be conversational but concise. If you don't know something, say so honestly.
        Always respond appropriately to what the user just said.
        Keep your responses short and clear for phone conversations.
        You are the assistant, the caller is the user who needs help.""",
        conversation_logger=conversation_logger,
        init_phrase="Hello! I'm your AI assistant. How can I help you today?",
        thinking_phrase="Let me think about that...",
        model=get_recommended_model("phone"),
        api_key=api_key
    )


def create_groq_pizza_bot(conversation_logger: ConversationLogger, api_key: Optional[str] = None):
    """Create a pizza ordering bot using Groq"""
    return GroqConversationBot(
        system_prompt="""You are a friendly pizza ordering assistant for Tony's Pizza. 
        Help customers place orders by asking about:
        - Pizza size (small, medium, large)
        - Toppings (pepperoni, mushrooms, sausage, etc.)
        - Delivery address
        - Phone number for delivery
        Be enthusiastic about pizza! Keep responses short and clear.
        Always confirm the complete order before finishing.""",
        conversation_logger=conversation_logger,
        init_phrase="Hi! Welcome to Tony's Pizza! What delicious pizza can I make for you today?",
        thinking_phrase="Let me add that to your order...",
        model=get_recommended_model("phone"),
        api_key=api_key
    ) 