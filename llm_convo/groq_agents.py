"""
groq ai agents for llm_convo
"""
import os
import logging
from typing import Optional, List
from llm_convo.agents import ChatAgent

try:
    from groq import Groq
except ImportError:
    print("⚠️ Groq library not installed. Install with: pip install groq")
    Groq = None


def get_recommended_model(use_case: str = "general") -> str:
    """get recommended groq model for different use cases"""
    models = {
        "phone": "llama3-8b-8192",
        "general": "llama3-8b-8192",
        "creative": "mixtral-8x7b-32768",
        "fast": "llama3-8b-8192",
    }
    return models.get(use_case, "llama3-8b-8192")


class GroqChatWithHistory(ChatAgent):
    """groq ai chat agent with conversation history"""
    
    def __init__(self, system_prompt: str, init_phrase: Optional[str] = None, 
                 model: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__()
        
        if Groq is None:
            raise ImportError("Groq library not installed. Install with: pip install groq")
        
        self.system_prompt = system_prompt
        self.init_phrase = init_phrase or "Hello! How can I help you?"
        self.model = model or get_recommended_model("general")
        
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable or api_key parameter required")
        
        self.client = Groq(api_key=api_key)
        self.conversation_history = []
        self.logger = logging.getLogger(__name__)
        
        self.conversation_history.append({
            "role": "system",
            "content": self.system_prompt
        })
    
    def start(self):
        """start the agent and return initial phrase"""
        self.logger.info(f"Started Groq chat agent with model: {self.model}")
        return self.init_phrase
    
    def get_response(self, transcript: List[str]) -> str:
        """get ai response based on conversation transcript"""
        try:
            self.logger.info(f"get_response called with transcript: {transcript}")
            self.logger.info(f"Current conversation history length: {len(self.conversation_history)}")
            
            if transcript:
                latest_message = transcript[-1].strip() if transcript[-1] else ""
                self.logger.info(f"Latest message from transcript: '{latest_message}'")
                
                if latest_message and latest_message != "OK":
                    last_user_msg = None
                    for msg in reversed(self.conversation_history):
                        if msg["role"] == "user":
                            last_user_msg = msg["content"]
                            break
                    
                    self.logger.info(f"Last user message in history: '{last_user_msg}'")
                    
                    if last_user_msg != latest_message:
                        self.conversation_history.append({
                            "role": "user", 
                            "content": latest_message
                        })
                        self.logger.info(f"Added new user message to history: '{latest_message}'")
                    else:
                        self.logger.info("Message already in history, skipping")
            
            if len(self.conversation_history) == 1:
                self.logger.info("Returning initial phrase - only system message in history")
                return self.init_phrase
            
            self.logger.info(f"Sending to Groq with {len(self.conversation_history)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response
            })
            
            if len(self.conversation_history) > 21:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-20:]
            
            self.logger.info(f"Groq response: {ai_response[:50]}...")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error getting Groq response: {e}")
            return "I'm sorry, I'm having trouble understanding. Could you please repeat that?" 