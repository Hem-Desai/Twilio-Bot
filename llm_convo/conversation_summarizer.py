"""
Conversation Summarization Service using Groq LLM

This module provides functionality to generate AI-powered summaries
of phone conversations using the free Groq API.
"""

import logging
import os
from typing import Optional, List, Dict
from llm_convo.database import DatabaseManager, Conversation, Message

try:
    from groq import Groq
except ImportError:
    print("⚠️ Groq library not installed. Install with: pip install groq")
    Groq = None


class GroqConversationSummarizer:
    """Generate conversation summaries using Groq LLM"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama3-8b-8192"):
        """
        Initialize the conversation summarizer
        
        Args:
            api_key: Groq API key (or use GROQ_API_KEY env var)
            model: Groq model to use for summarization
        """
        if Groq is None:
            raise ImportError("Groq library not installed. Install with: pip install groq")
        
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable or api_key parameter required")
        
        self.client = Groq(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def generate_summary(self, messages: List[Message]) -> str:
        """
        Generate a conversation summary from messages
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Generated summary string
        """
        if not messages:
            return "No conversation content available."
        
        # Format conversation for summarization
        conversation_text = self._format_conversation(messages)
        
        # Create summarization prompt
        system_prompt = """You are an expert conversation summarizer. Your job is to create concise, informative summaries of phone conversations between customers and AI assistants.

Focus on:
1. Main topics discussed
2. Customer's primary needs or requests
3. Key information provided
4. Resolution status or next steps
5. Overall tone and outcome

Keep the summary professional, clear, and under 150 words. Use bullet points for clarity when appropriate."""

        user_prompt = f"""Please summarize this phone conversation:

{conversation_text}

Provide a clear, professional summary that captures the key points and outcome of the conversation."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            self.logger.info(f"Generated summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary with Groq: {e}")
            return f"Error generating summary: {str(e)}"
    
    def _format_conversation(self, messages: List[Message]) -> str:
        """Format messages into readable conversation text"""
        formatted_lines = []
        
        for message in messages:
            speaker = "Customer" if message.speaker == "user" else "AI Assistant"
            timestamp = message.timestamp.strftime("%H:%M:%S") if message.timestamp else "N/A"
            formatted_lines.append(f"[{timestamp}] {speaker}: {message.content}")
        
        return "\n".join(formatted_lines)


class ConversationSummaryService:
    """Service for managing conversation summaries with database integration"""
    
    def __init__(self, db_manager: DatabaseManager, summarizer: GroqConversationSummarizer):
        """
        Initialize the summary service
        
        Args:
            db_manager: Database manager instance
            summarizer: Groq conversation summarizer instance
        """
        self.db_manager = db_manager
        self.summarizer = summarizer
        self.logger = logging.getLogger(__name__)
    
    def generate_and_save_summary(self, conversation_id: int) -> Optional[str]:
        """
        Generate and save a summary for a conversation
        
        Args:
            conversation_id: ID of the conversation to summarize
            
        Returns:
            Generated summary or None if failed
        """
        try:
            # Get conversation with messages
            conversation = self.db_manager.get_conversation_with_messages(conversation_id)
            if not conversation:
                self.logger.error(f"Conversation {conversation_id} not found")
                return None
            
            # Only summarize completed conversations
            if conversation.status != 'completed':
                self.logger.warning(f"Conversation {conversation_id} is not completed, skipping summary")
                return None
            
            # Check if summary already exists
            if conversation.summary:
                self.logger.info(f"Conversation {conversation_id} already has a summary")
                return conversation.summary
            
            # Generate summary
            summary = self.summarizer.generate_summary(conversation.messages)
            
            # Save summary to database
            self.db_manager.update_conversation_summary(conversation_id, summary)
            self.logger.info(f"Saved summary for conversation {conversation_id}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary for conversation {conversation_id}: {e}")
            return None
    
    def get_summary(self, conversation_id: int) -> Optional[str]:
        """
        Get existing summary for a conversation
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Existing summary or None if not found
        """
        conversation = self.db_manager.get_conversation_with_messages(conversation_id)
        return conversation.summary if conversation else None
    
    def batch_generate_summaries(self, limit: int = 50) -> Dict[str, int]:
        """
        Generate summaries for all completed conversations without summaries
        
        Args:
            limit: Maximum number of conversations to process
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {"processed": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        try:
            # Get completed conversations without summaries
            conversations = self.db_manager.get_all_conversations(limit=limit)
            
            for conversation in conversations:
                if conversation.status == 'completed' and not conversation.summary:
                    stats["processed"] += 1
                    
                    summary = self.generate_and_save_summary(conversation.id)
                    if summary:
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    stats["skipped"] += 1
            
            self.logger.info(f"Batch summary generation complete: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error in batch summary generation: {e}")
            return stats


def create_summary_service(database_url: Optional[str] = None, groq_api_key: Optional[str] = None) -> ConversationSummaryService:
    """
    Create a conversation summary service with default configuration
    
    Args:
        database_url: Database URL (defaults to SQLite)
        groq_api_key: Groq API key (defaults to env var)
        
    Returns:
        Configured ConversationSummaryService instance
    """
    # Initialize database manager
    db_manager = DatabaseManager(database_url)
    
    # Initialize Groq summarizer
    summarizer = GroqConversationSummarizer(api_key=groq_api_key)
    
    # Create and return service
    return ConversationSummaryService(db_manager, summarizer) 