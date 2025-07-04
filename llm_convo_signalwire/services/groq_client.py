import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from groq import AsyncGroq
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class GroqClient:
    """Client for Groq API with business search intent extraction"""
    
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        logger.info(f"✅ Groq client initialized with model: {self.model}")
    
    async def extract_business_intent(self, user_input: str) -> Dict[str, Any]:
        """Extract business search intent from user input"""
        try:
            system_prompt = """You are a business directory assistant. Extract business search parameters from user input.

Respond ONLY with valid JSON in this exact format:
{
    "business_type": "specific business category (e.g., restaurant, dentist, mechanic)",
    "location": "city or area name", 
    "requirements": ["list", "of", "specific", "requirements"],
    "urgency": "low|medium|high",
    "action": "search|forward|info|unclear"
}

Examples:
User: "I need a dentist in Mumbai" 
Response: {"business_type": "dentist", "location": "Mumbai", "requirements": [], "urgency": "medium", "action": "search"}

User: "Connect me to the first restaurant"
Response: {"business_type": "restaurant", "location": "", "requirements": [], "urgency": "high", "action": "forward"}

User: "Find an open pizza place near me"
Response: {"business_type": "pizza restaurant", "location": "near me", "requirements": ["open now"], "urgency": "medium", "action": "search"}

User: "I need a dentist"
Response: {"business_type": "dentist", "location": "", "requirements": [], "urgency": "medium", "action": "search"}"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                temperature=0.1,  # Low temperature for consistent parsing
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🎯 Extracted intent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extracting business intent: {e}")
            return {
                "business_type": "",
                "location": "",
                "requirements": [],
                "urgency": "low",
                "action": "unclear"
            }
    
    async def generate_business_presentation(self, search_results: List[Dict], user_query: str) -> str:
        """Generate natural presentation of business search results"""
        try:
            if not search_results:
                return "I'm sorry, I couldn't find any businesses matching your request. Could you try a different search or location?"
            
            # Format results for the prompt
            results_text = ""
            for i, business in enumerate(search_results[:5], 1):
                rating = business.get('rating', 'N/A')
                status = "open now" if business.get('open_now') else "closed"
                address = business.get('vicinity', business.get('formatted_address', ''))
                
                results_text += f"{i}. {business['name']} - {rating} stars - {status} - {address}\n"
            
            system_prompt = """You are a helpful business directory assistant. Present search results in a conversational, natural way for a phone call.

Rules:
1. Be concise but informative
2. Mention top 3-5 results maximum
3. Include key details: name, rating, open status
4. Ask if they want to be connected or need more info
5. Use natural phone conversation tone
6. Keep response under 100 words"""

            user_prompt = f"""User searched for: "{user_query}"

Search results:
{results_text}

Present these results naturally and ask what they'd like to do next."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"📢 Generated presentation: {result[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating business presentation: {e}")
            return "I found some businesses for you, but I'm having trouble presenting them right now. Let me try again."
    
    async def handle_user_selection(self, user_input: str, available_businesses: List[Dict]) -> Dict[str, Any]:
        """Handle user selection from presented business options"""
        try:
            business_list = ""
            for i, business in enumerate(available_businesses, 1):
                business_list += f"{i}. {business['name']}\n"
            
            system_prompt = """You are helping a user select from a list of businesses. Parse their selection and determine their intent.

Respond ONLY with valid JSON:
{
    "selection_index": number (1-based index, or -1 if unclear),
    "selected_business": "business name if clear",
    "action": "forward|info|unclear|new_search",
    "confidence": "low|medium|high"
}

Examples:
- "Connect me to number 1" → {"selection_index": 1, "selected_business": "", "action": "forward", "confidence": "high"}
- "Tell me more about the dentist" → {"selection_index": -1, "selected_business": "", "action": "info", "confidence": "medium"}
- "The second one please" → {"selection_index": 2, "selected_business": "", "action": "forward", "confidence": "high"}
- "Actually, find restaurants instead" → {"selection_index": -1, "selected_business": "", "action": "new_search", "confidence": "high"}"""

            user_prompt = f"""Available businesses:
{business_list}

User said: "{user_input}"

Parse their selection:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🎯 Parsed selection: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error handling user selection: {e}")
            return {
                "selection_index": -1,
                "selected_business": "",
                "action": "unclear",
                "confidence": "low"
            }
    
    async def generate_conversation_response(self, context: str, user_input: str) -> str:
        """Generate conversational response for general chat"""
        try:
            system_prompt = """You are a friendly business directory assistant on a phone call. 

Guidelines:
1. Be helpful and conversational
2. Keep responses short (under 50 words for phone calls)
3. Guide users toward business searches or call forwarding
4. If unclear, ask clarifying questions
5. Be natural and professional"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\nUser: {user_input}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"💬 Generated response: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating conversation response: {e}")
            return "I'm sorry, could you repeat that? I'm here to help you find businesses and connect calls."
    
    async def generate_error_response(self, error_type: str) -> str:
        """Generate appropriate error responses"""
        error_responses = {
            "no_results": "I couldn't find any businesses matching your request. Could you try a different search term or location?",
            "call_failed": "I'm sorry, I couldn't connect your call. The business might be busy or unavailable. You can try calling them directly.",
            "unclear_request": "I didn't quite understand that. Could you tell me what type of business you're looking for and in which area?",
            "system_error": "I'm experiencing some technical difficulties. Please try again in a moment.",
            "timeout": "I didn't hear anything. What type of business are you looking for?"
        }
        
        return error_responses.get(error_type, error_responses["system_error"])

# Create global instance
groq_client = GroqClient() 