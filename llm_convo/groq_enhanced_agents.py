import logging
import time
from typing import Optional
from llm_convo.agents import TwilioCaller
from llm_convo.groq_agents import GroqChatWithHistory, get_recommended_model
from llm_convo.enhanced_conversation import ConversationLogger
from llm_convo.audio_output import GoogleTTS
from llm_convo.business_search import BusinessDirectoryBot, CallForwardingService


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


class CallForwardingGroqChat(DatabaseLoggingGroqChat):
    """Enhanced Groq Chat agent with business search and call forwarding capabilities"""
    
    def __init__(self, system_prompt: str, conversation_logger: ConversationLogger,
                 twilio_client, init_phrase: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        super().__init__(system_prompt, conversation_logger, init_phrase, model, api_key)
        
        # Initialize business directory and call forwarding services
        self.business_bot = BusinessDirectoryBot(api_key, google_api_key)
        self.call_forwarding = CallForwardingService(twilio_client)
        self.current_businesses = []
        self.current_call_sid = None
        self.awaiting_selection = False
        
    def set_call_info(self, call_sid: str):
        """Set current call information for forwarding"""
        self.current_call_sid = call_sid
        
    async def process_business_request(self, user_message: str) -> str:
        """Process business search requests and handle call forwarding"""
        try:
            # Process the request through business bot
            response, businesses, should_forward = await self.business_bot.process_request(user_message)
            
            if businesses:
                self.current_businesses = businesses
                self.awaiting_selection = should_forward
                
                # If only one business and user wants connection, ask for confirmation
                if len(businesses) == 1 and should_forward:
                    business = businesses[0]
                    response += f"\n\nShould I connect you to {business['name']} at {business['phone']} now?"
                    
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing business request: {e}")
            return "I'm sorry, I'm having trouble with the business search right now. Please try again."
    
    async def handle_business_selection(self, user_choice: str) -> str:
        """Handle business selection and initiate call forwarding"""
        if not self.awaiting_selection or not self.current_businesses:
            return "I don't have any business options ready. Please tell me what service you're looking for."
        
        # Handle confirmation responses
        if any(word in user_choice.lower() for word in ['yes', 'yeah', 'sure', 'ok', 'connect', 'call']):
            if len(self.current_businesses) == 1:
                selected_business = self.current_businesses[0]
            else:
                return "Which business would you like me to connect you to? Please say the number or name."
        elif any(word in user_choice.lower() for word in ['no', 'nope', 'cancel', 'skip']):
            self.awaiting_selection = False
            self.current_businesses = []
            return "Okay, I won't make the connection. Is there anything else I can help you find?"
        else:
            # Try to select business by number or name
            selected_business = self.business_bot.select_business(user_choice, self.current_businesses)
            
            if not selected_business:
                business_list = []
                for i, business in enumerate(self.current_businesses, 1):
                    business_list.append(f"{i}. {business['name']}")
                return f"I didn't understand your choice. Please select from:\n" + "\n".join(business_list)
        
        # Initiate call forwarding
        if selected_business and self.current_call_sid:
            success = self.call_forwarding.forward_call(
                self.current_call_sid, 
                selected_business['phone']
            )
            
            if success:
                self.awaiting_selection = False
                self.current_businesses = []
                return f"Connecting you to {selected_business['name']} at {selected_business['phone']}. Please hold..."
            else:
                return f"I'm sorry, I couldn't connect you to {selected_business['name']}. You can call them directly at {selected_business['phone']}."
        
        return "I'm sorry, I can't forward your call right now. Please call the business directly."
    
    def get_response(self, transcript: list) -> str:
        """Enhanced response handling with business search integration"""
        if not transcript:
            return super().get_response(transcript)
        
        user_message = transcript[-1] if transcript else ""
        
        # Handle business selection if we're awaiting one
        if self.awaiting_selection:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(self.handle_business_selection(user_message))
                loop.close()
                
                # Log the response
                if response and response.strip():
                    self.conversation_logger.log_message('bot', response, 0)
                    self.logger.info(f"Business selection response: {response[:50]}...")
                
                return response
            except Exception as e:
                loop.close()
                self.logger.error(f"Error in business selection: {e}")
                return "I'm sorry, there was an error processing your selection. Please try again."
        
        # Check if this is a business request
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Quick intent check
            intent = loop.run_until_complete(self.business_bot.intent_extractor.extract_intent(user_message))
            
            if intent.get('is_business_request', False) and intent.get('confidence', 0) > 0.5:
                # This is a business request
                response = loop.run_until_complete(self.process_business_request(user_message))
                loop.close()
                
                # Log the response
                if response and response.strip():
                    self.conversation_logger.log_message('bot', response, 0)
                    self.logger.info(f"Business search response: {response[:50]}...")
                
                return response
            else:
                # Regular conversation
                loop.close()
                return super().get_response(transcript)
                
        except Exception as e:
            loop.close()
            self.logger.error(f"Error processing request: {e}")
            return super().get_response(transcript)


class DatabaseLoggingTwilioCaller(TwilioCaller):
    """Enhanced Twilio Caller agent that logs to database (same as before)"""
    
    def __init__(self, session, conversation_logger: ConversationLogger, 
                 tts: Optional[GoogleTTS] = None, thinking_phrase: str = "OK"):
        super().__init__(session, tts, thinking_phrase)
        self.conversation_logger = conversation_logger
        self.logger = logging.getLogger(__name__)
        self.call_sid = None
        
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
            
            # Store call SID for forwarding
            self.call_sid = call_sid
            
            # Extract caller phone if available
            caller_phone = getattr(self.session, '_caller_phone', None)
            
            self.conversation_logger.start_conversation(
                call_sid=call_sid or f"session_{int(time.time())}",
                caller_phone=caller_phone
            )
            self.logger.info(f"Initialized conversation for call {call_sid}")
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation: {e}")
    
    def get_call_sid(self):
        """Get the current call SID for forwarding"""
        return self.call_sid
    
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
                 model: Optional[str] = None, api_key: Optional[str] = None, 
                 enable_call_forwarding: bool = False, google_api_key: Optional[str] = None):
        self.system_prompt = system_prompt
        self.conversation_logger = conversation_logger
        self.init_phrase = init_phrase or "Hello! How can I help you today?"
        self.thinking_phrase = thinking_phrase
        self.model = model or get_recommended_model("phone")
        self.api_key = api_key
        self.enable_call_forwarding = enable_call_forwarding
        self.google_api_key = google_api_key
        self.logger = logging.getLogger(__name__)
    
    def create_agents(self, twilio_session):
        """Create the AI and Twilio agents for a conversation"""
        
        # Create Twilio agent with database logging first
        twilio_agent = DatabaseLoggingTwilioCaller(
            session=twilio_session,
            conversation_logger=self.conversation_logger,
            thinking_phrase=self.thinking_phrase
        )
        
        if self.enable_call_forwarding:
            # Create call forwarding AI agent
            ai_agent = CallForwardingGroqChat(
                system_prompt=self.system_prompt,
                conversation_logger=self.conversation_logger,
                twilio_client=twilio_session.client,
                init_phrase=self.init_phrase,
                model=self.model,
                api_key=self.api_key,
                google_api_key=self.google_api_key
            )
            
            # Set call information for forwarding
            call_sid = twilio_agent.get_call_sid()
            if call_sid:
                ai_agent.set_call_info(call_sid)
        else:
            # Create regular AI agent with Groq and database logging
            ai_agent = DatabaseLoggingGroqChat(
                system_prompt=self.system_prompt,
                conversation_logger=self.conversation_logger,
                init_phrase=self.init_phrase,
                model=self.model,
                api_key=self.api_key
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


def create_groq_pizza_bot(conversation_logger, groq_api_key, model=None):
    """Create a pizza ordering bot using Groq"""
    system_prompt = """You are Tony, a friendly pizza restaurant assistant. You help customers order pizza, check availability, and answer questions about the menu.

Key responsibilities:
- Take pizza orders with all details (size, toppings, delivery address)
- Provide menu information and recommendations
- Handle special dietary requests (vegan, gluten-free, etc.)
- Calculate order totals including tax and delivery
- Confirm delivery times and contact information
- Be enthusiastic about pizza but also professional

Always confirm the complete order before finalizing, including:
- Pizza details (size, crust, toppings)
- Delivery address and contact number
- Estimated delivery time
- Total cost

Keep responses concise but friendly. Ask one question at a time to avoid confusion."""

    return GroqConversationBot(
        system_prompt=system_prompt,
        conversation_logger=conversation_logger,
        init_phrase="Hey there! Welcome to Tony's Pizza! I'm here to help you order some delicious pizza. What can I get started for you today?",
        model=model,
        api_key=groq_api_key
    )


def create_groq_business_directory_bot(conversation_logger, groq_api_key, model=None):
    """Create a business directory bot with real-time search and call forwarding"""
    system_prompt = """You are a business directory assistant that helps users find and connect to local businesses. You can search for businesses in real-time and transfer calls.

Your workflow:
1. Listen for business requests (e.g., "I need a dentist in Ahmedabad")
2. Extract the service type and location
3. Search for relevant businesses with phone numbers
4. Present options with ratings and availability
5. Offer to connect the caller to their chosen business

Key behaviors:
- Always ask for specific location if not provided
- Present businesses with clear numbering (1, 2, 3...)
- Include ratings and current status (open/closed) when available
- Confirm before transferring calls
- Be helpful and professional
- If no businesses found, suggest alternatives or directory assistance

Example interaction:
User: "I need a dentist in Ahmedabad"
You: "I found 3 dentist options in Ahmedabad:
1. City Dental Care (4.5 stars) - Open now
2. Smile Clinic (4.2 stars) - Open now  
3. Perfect Dental (4.0 stars) - Closed now

Which one would you like me to connect you to?"

Keep responses clear and actionable. Always confirm the business choice before initiating transfer."""

    return GroqConversationBot(
        system_prompt=system_prompt,
        conversation_logger=conversation_logger,
        init_phrase="Hello! I'm your business directory assistant. I can help you find local businesses and connect you directly to them. What type of service are you looking for and in which area?",
        model=model,
        api_key=groq_api_key
    )


def create_groq_call_forwarding_bot(conversation_logger: ConversationLogger, groq_api_key: Optional[str] = None, 
                                   google_api_key: Optional[str] = None, model: Optional[str] = None):
    """Create a call forwarding bot with business search and live call transfer"""
    system_prompt = """You are an intelligent call forwarding assistant that helps users find and connect to local businesses instantly.

🔍 Your capabilities:
- Real-time business search using Google Places API
- Live call forwarding to connect users directly to businesses
- Extract service needs and locations from natural speech
- Provide business details including ratings and hours

📞 Your workflow:
1. Listen for business requests (e.g., "I need a dentist in Mumbai")
2. Search for relevant businesses in real-time
3. Present clear options with ratings and status
4. Ask for confirmation and immediately connect calls

💬 Communication style:
- Be helpful, friendly, and efficient
- Keep explanations brief for phone conversations
- Always confirm before transferring calls
- If multiple options, number them clearly (1, 2, 3...)
- Include useful details: ratings, open/closed status

✅ Example interactions:
User: "I need a restaurant in Delhi"
You: "I found 3 restaurants in Delhi:
1. Spice Route (4.5 stars) - Open now
2. Delhi Darbar (4.2 stars) - Open now
3. Mughal Garden (4.0 stars) - Closed now
Which one should I connect you to?"

User: "Connect me to number 1"
You: "Connecting you to Spice Route now. Please hold..."

🚫 If no results found:
- Suggest calling directory assistance (411)
- Offer to search in nearby areas
- Provide helpful alternatives

Always prioritize user safety and verify business legitimacy."""

    return GroqConversationBot(
        system_prompt=system_prompt,
        conversation_logger=conversation_logger,
        init_phrase="Hello! I'm your call forwarding assistant. I can find local businesses and connect you directly to them. What service do you need and in which area?",
        thinking_phrase="Let me search for that business...",
        model=model or get_recommended_model("phone"),
        api_key=groq_api_key,
        enable_call_forwarding=True,
        google_api_key=google_api_key
    ) 