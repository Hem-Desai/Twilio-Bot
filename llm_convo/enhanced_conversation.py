import logging
import time
from typing import Optional
from llm_convo.agents import ChatAgent
from llm_convo.database import DatabaseManager


class ConversationLogger:
    """Handles logging conversations to database with real-time updates"""
    
    def __init__(self, db_manager: DatabaseManager, auto_summarize: bool = True):
        self.db_manager = db_manager
        self.current_conversation = None
        self.logger = logging.getLogger(__name__)
        self.auto_summarize = auto_summarize
        self.summary_service = None
        
        # Initialize summary service if auto_summarize is enabled
        if self.auto_summarize:
            try:
                from llm_convo.conversation_summarizer import create_summary_service
                self.summary_service = create_summary_service(database_url=None)
                self.logger.info("Summary service initialized for auto-summarization")
            except Exception as e:
                self.logger.warning(f"Could not initialize summary service: {e}")
                self.auto_summarize = False
    
    def start_conversation(self, call_sid: str, caller_phone: Optional[str] = None):
        """Start a new conversation and create database record"""
        try:
            self.current_conversation = self.db_manager.create_conversation(
                call_sid=call_sid,
                caller_phone=caller_phone
            )
            self.logger.info(f"Started conversation {self.current_conversation.id} for call {call_sid}")
            return self.current_conversation
        except Exception as e:
            self.logger.error(f"Failed to start conversation: {e}")
            return None
    
    def log_message(self, speaker: str, content: str, audio_duration: Optional[float] = None):
        """Log a message to the current conversation"""
        if not self.current_conversation:
            self.logger.warning("No active conversation to log message to")
            return None
        
        try:
            message = self.db_manager.add_message(
                conversation_id=self.current_conversation.id,
                speaker=speaker,
                content=content,
                audio_duration=audio_duration
            )
            self.logger.info(f"Logged {speaker} message: {content[:50]}...")
            return message
        except Exception as e:
            self.logger.error(f"Failed to log message: {e}")
            return None
    
    def end_conversation(self, status: str = 'completed'):
        """End the current conversation"""
        if not self.current_conversation:
            self.logger.warning("No active conversation to end")
            return None
        
        try:
            conversation = self.db_manager.end_conversation(
                conversation_id=self.current_conversation.id,
                status=status
            )
            self.logger.info(f"Ended conversation {self.current_conversation.id} with status {status}")
            self.current_conversation = None
            
            # Generate summary if auto_summarize is enabled and status is completed
            if self.auto_summarize and self.summary_service and status == 'completed':
                try:
                    summary = self.summary_service.generate_and_save_summary(conversation.id)
                    if summary:
                        self.logger.info(f"Summary generated and saved for conversation {conversation.id}")
                    else:
                        self.logger.warning(f"Failed to generate summary for conversation {conversation.id}")
                except Exception as e:
                    self.logger.error(f"Failed to generate summary: {e}")
            
            return conversation
        except Exception as e:
            self.logger.error(f"Failed to end conversation: {e}")
            return None


def run_enhanced_conversation(agent_a: ChatAgent, agent_b: ChatAgent, 
                            conversation_logger: ConversationLogger,
                            max_turns: int = 50):
    """
    Run a conversation between two agents with database logging and live transcription
    
    Args:
        agent_a: First agent (typically the AI bot)
        agent_b: Second agent (typically the human caller via Twilio)
        conversation_logger: Logger for database storage
        max_turns: Maximum number of conversation turns
    """
    transcript = []
    turn_count = 0
    
    try:
        # Start both agents
        agent_a.start()
        agent_b.start()
        
        # First, get the initial greeting from the bot
        start_time = time.time()
        initial_greeting = agent_a.get_response([])  # Empty transcript for first greeting
        audio_duration = time.time() - start_time
        
        if initial_greeting and initial_greeting.strip():
            transcript.append(initial_greeting)
            conversation_logger.log_message('bot', initial_greeting, audio_duration)
            logging.info(f"Bot: {initial_greeting}")
        
        while turn_count < max_turns:
            try:
                # Agent B responds (human)
                start_time = time.time()
                text_b = agent_b.get_response(transcript)
                response_time = time.time() - start_time
                
                if text_b and text_b.strip():
                    transcript.append(text_b)
                    conversation_logger.log_message('user', text_b, response_time)
                    logging.info(f"User: {text_b}")
                    
                    # Check for conversation ending phrases
                    if any(phrase in text_b.lower() for phrase in ['goodbye', 'bye', 'hang up', 'end call']):
                        logging.info("User indicated end of conversation")
                        break
                        
                    # Now get bot response to the user's input
                    start_time = time.time()
                    text_a = agent_a.get_response([text_b])  # Only pass the user's latest message
                    audio_duration = time.time() - start_time
                    
                    if text_a and text_a.strip():
                        transcript.append(text_a)
                        conversation_logger.log_message('bot', text_a, audio_duration)
                        logging.info(f"Bot: {text_a}")
                        
                else:
                    # If no response, might indicate call ended
                    logging.info("No user response received, ending conversation")
                    break
                
                turn_count += 1
                
            except Exception as e:
                logging.error(f"Error during conversation turn {turn_count}: {e}")
                conversation_logger.end_conversation('failed')
                break
        
        # End conversation normally
        if turn_count >= max_turns:
            logging.info(f"Conversation ended after {max_turns} turns")
            conversation_logger.end_conversation('max_turns_reached')
        else:
            conversation_logger.end_conversation('completed')
            
    except Exception as e:
        logging.error(f"Critical error in conversation: {e}")
        conversation_logger.end_conversation('failed')


class LiveTranscriptionTracker:
    """Tracks live transcription updates for real-time dashboard updates"""
    
    def __init__(self):
        self.active_transcriptions = {}
        self.listeners = []
    
    def add_listener(self, callback):
        """Add a callback function to receive transcription updates"""
        self.listeners.append(callback)
    
    def update_transcription(self, call_sid: str, speaker: str, partial_text: str, is_final: bool = False):
        """Update live transcription for a call"""
        if call_sid not in self.active_transcriptions:
            self.active_transcriptions[call_sid] = {'user': '', 'bot': ''}
        
        self.active_transcriptions[call_sid][speaker] = partial_text
        
        # Notify all listeners
        for callback in self.listeners:
            try:
                callback(call_sid, speaker, partial_text, is_final)
            except Exception as e:
                logging.error(f"Error in transcription listener: {e}")
    
    def clear_transcription(self, call_sid: str):
        """Clear transcription for a completed call"""
        if call_sid in self.active_transcriptions:
            del self.active_transcriptions[call_sid] 