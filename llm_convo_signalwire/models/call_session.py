from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ConversationState(Enum):
    """States of the conversation flow"""
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    SEARCHING = "searching"
    PRESENTING_RESULTS = "presenting_results"
    AWAITING_SELECTION = "awaiting_selection"
    FORWARDING_CALL = "forwarding_call"
    PROVIDING_INFO = "providing_info"
    ENDING = "ending"
    ERROR = "error"

class ActionType(Enum):
    """Types of actions user can request"""
    SEARCH = "search"
    FORWARD = "forward"
    INFO = "info"
    NEW_SEARCH = "new_search"
    UNCLEAR = "unclear"
    END_CALL = "end_call"

@dataclass
class BusinessSearchIntent:
    """Extracted intent from user's business search request"""
    business_type: str
    location: str
    requirements: List[str] = field(default_factory=list)
    urgency: str = "medium"  # low, medium, high
    action: ActionType = ActionType.SEARCH
    confidence: float = 0.0
    raw_input: str = ""

@dataclass
class BusinessResult:
    """Standardized business search result"""
    place_id: str
    name: str
    rating: Optional[float] = None
    user_ratings_total: int = 0
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    open_now: Optional[bool] = None
    price_level: Optional[int] = None
    types: List[str] = field(default_factory=list)
    location: Optional[Dict[str, float]] = None
    
    # Calculated fields
    display_rating: str = ""
    status: str = ""
    ranking_score: float = 0.0
    
    def __post_init__(self):
        """Calculate display fields after initialization"""
        if not self.display_rating:
            self.display_rating = f"{self.rating} stars" if self.rating else "No rating"
        
        if not self.status:
            if self.open_now is True:
                self.status = "Open now"
            elif self.open_now is False:
                self.status = "Closed"
            else:
                self.status = "Hours unknown"

@dataclass
class UserSelection:
    """User's selection from presented business options"""
    selection_index: int = -1  # 1-based index, -1 if unclear
    selected_business: str = ""
    action: ActionType = ActionType.UNCLEAR
    confidence: str = "low"  # low, medium, high
    raw_input: str = ""

@dataclass
class CallMetrics:
    """Metrics and timing for call performance"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Component timing
    stt_total_time: float = 0.0
    llm_total_time: float = 0.0
    tts_total_time: float = 0.0
    search_total_time: float = 0.0
    
    # Counts
    user_messages: int = 0
    bot_messages: int = 0
    search_requests: int = 0
    forwarding_attempts: int = 0
    
    # Quality metrics
    transcription_accuracy: float = 0.0
    user_satisfaction: Optional[int] = None  # 1-5 scale
    call_completion: bool = False
    
    def calculate_duration(self):
        """Calculate call duration if end_time is set"""
        if self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

@dataclass
class CallSessionData:
    """Complete call session data model"""
    # Basic call info
    call_sid: str
    stream_sid: str
    account_sid: str
    caller_phone: Optional[str] = None
    
    # Session state
    state: ConversationState = ConversationState.GREETING
    created_at: datetime = field(default_factory=datetime.now)
    
    # Conversation data
    current_intent: Optional[BusinessSearchIntent] = None
    search_results: List[BusinessResult] = field(default_factory=list)
    last_user_input: str = ""
    last_bot_response: str = ""
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Active components
    deepgram_connection: Optional[Any] = None
    audio_buffer_transcriber: Optional[Any] = None
    
    # Performance metrics
    metrics: CallMetrics = field(default_factory=CallMetrics)
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    
    def add_message(self, speaker: str, content: str, timestamp: Optional[datetime] = None):
        """Add a message to conversation history"""
        if timestamp is None:
            timestamp = datetime.now()
        
        message = {
            "speaker": speaker,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "state": self.state.value
        }
        
        self.conversation_history.append(message)
        
        # Update counters
        if speaker == "user":
            self.metrics.user_messages += 1
            self.last_user_input = content
        elif speaker == "bot":
            self.metrics.bot_messages += 1
            self.last_bot_response = content
    
    def update_state(self, new_state: ConversationState):
        """Update conversation state with logging"""
        old_state = self.state
        self.state = new_state
        
        # Log state transition
        self.add_message("system", f"State transition: {old_state.value} → {new_state.value}")
    
    def record_error(self, error_message: str):
        """Record an error in the session"""
        self.error_count += 1
        self.last_error = error_message
        self.add_message("system", f"Error: {error_message}")
    
    def set_search_intent(self, intent: BusinessSearchIntent):
        """Set the current business search intent"""
        self.current_intent = intent
        self.metrics.search_requests += 1
    
    def set_search_results(self, results: List[BusinessResult]):
        """Set the business search results"""
        self.search_results = results
        if results:
            self.update_state(ConversationState.PRESENTING_RESULTS)
        else:
            self.add_message("system", "No search results found")
    
    def get_conversation_context(self, last_n_messages: int = 5) -> str:
        """Get recent conversation context as text"""
        recent_messages = self.conversation_history[-last_n_messages:]
        context_parts = []
        
        for msg in recent_messages:
            if msg["speaker"] in ["user", "bot"]:
                context_parts.append(f"{msg['speaker']}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the session"""
        self.metrics.calculate_duration()
        
        return {
            "call_sid": self.call_sid,
            "caller_phone": self.caller_phone,
            "state": self.state.value,
            "duration_seconds": self.metrics.duration_seconds,
            "messages": {
                "user": self.metrics.user_messages,
                "bot": self.metrics.bot_messages,
                "total": len(self.conversation_history)
            },
            "search_requests": self.metrics.search_requests,
            "forwarding_attempts": self.metrics.forwarding_attempts,
            "error_count": self.error_count,
            "completion": self.metrics.call_completion,
            "created_at": self.created_at.isoformat()
        }

@dataclass
class AudioChunk:
    """Audio data chunk for processing"""
    data: bytes
    timestamp: datetime = field(default_factory=datetime.now)
    sequence: int = 0
    sample_rate: int = 8000
    format: str = "mulaw"
    
    def size_mb(self) -> float:
        """Get size in megabytes"""
        return len(self.data) / 1024 / 1024

@dataclass
class TranscriptionResult:
    """Result from speech-to-text processing"""
    transcript: str
    confidence: float = 0.0
    is_final: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if transcription is valid and useful"""
        return (
            bool(self.transcript.strip()) and
            len(self.transcript.strip()) > 2 and
            self.confidence > 0.5
        ) 