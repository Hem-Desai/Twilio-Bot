"""
Business Search and Call Forwarding Service

This module provides real-time business search using Google Places API
and call forwarding capabilities for the voice AI system.
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
import googlemaps
from datetime import datetime
import json

try:
    from groq import Groq
except ImportError:
    print("⚠️ Groq library not installed. Install with: pip install groq")
    Groq = None


class BusinessSearchService:
    """Real-time business search using Google Places API"""
    
    def __init__(self, google_api_key: Optional[str] = None):
        """
        Initialize business search service
        
        Args:
            google_api_key: Google Places API key (or use GOOGLE_PLACES_API_KEY env var)
        """
        self.google_key = google_api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self.gmaps = googlemaps.Client(key=self.google_key) if self.google_key else None
        self.logger = logging.getLogger(__name__)
        
        # Track usage to stay in free tier
        self.monthly_usage = 0
        self.max_free_searches = 4000  # Conservative estimate for $200 credit
        
        if not self.google_key:
            self.logger.warning("Google Places API key not found. Search functionality limited.")
    
    async def search_businesses(self, service_type: str, location: str, max_results: int = 3) -> List[Dict]:
        """
        Search for businesses with cost optimization
        
        Args:
            service_type: Type of service (e.g., "dentist", "restaurant")
            location: Location to search in (e.g., "Ahmedabad", "Mumbai")
            max_results: Maximum number of results to return
            
        Returns:
            List of business dictionaries with name, phone, address, rating
        """
        if not self.gmaps:
            return await self._fallback_search(service_type, location)
        
        # Check if we're approaching free tier limit
        if self.monthly_usage >= self.max_free_searches:
            self.logger.warning("Approaching Google Places API limit, using fallback")
            return await self._fallback_search(service_type, location)
        
        try:
            # Google Places Text Search
            query = f"{service_type} in {location}"
            self.logger.info(f"Searching for: {query}")
            
            results = self.gmaps.places(
                query=query,
                type='establishment',
                language='en'
            )
            
            businesses = []
            for place in results['results'][:max_results]:
                try:
                    # Get detailed information including phone number
                    details = self.gmaps.place(
                        place_id=place['place_id'],
                        fields=['name', 'formatted_phone_number', 'formatted_address', 'rating', 'opening_hours', 'website']
                    )
                    
                    result = details['result']
                    
                    # Only include businesses with phone numbers
                    if 'formatted_phone_number' in result:
                        business = {
                            'name': result['name'],
                            'phone': result['formatted_phone_number'],
                            'address': result.get('formatted_address', 'Address not available'),
                            'rating': result.get('rating', 'No rating'),
                            'website': result.get('website', 'No website'),
                            'open_now': self._check_if_open(result.get('opening_hours', {}))
                        }
                        businesses.append(business)
                    
                    self.monthly_usage += 2  # Text search + Place details
                    
                except Exception as e:
                    self.logger.error(f"Error processing place {place.get('name', 'Unknown')}: {e}")
                    continue
            
            self.logger.info(f"Found {len(businesses)} businesses with phone numbers")
            return businesses
            
        except Exception as e:
            self.logger.error(f"Google Places search failed: {e}")
            return await self._fallback_search(service_type, location)
    
    def _check_if_open(self, opening_hours: Dict) -> str:
        """Check if business is currently open"""
        if not opening_hours:
            return "Hours unknown"
        
        open_now = opening_hours.get('open_now', None)
        if open_now is True:
            return "Open now"
        elif open_now is False:
            return "Closed now"
        else:
            return "Hours unknown"
    
    async def _fallback_search(self, service_type: str, location: str) -> List[Dict]:
        """Fallback when API limits exceeded or unavailable"""
        self.logger.info("Using fallback search (directory assistance)")
        return [{
            'name': f'Directory Assistance for {service_type.title()}',
            'phone': '411',
            'address': f'Call directory assistance for {service_type} in {location}',
            'rating': 'N/A',
            'website': 'N/A',
            'open_now': 'Call to check'
        }]


class IntentExtractor:
    """Extract business search intent from user speech using Groq"""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize intent extractor
        
        Args:
            groq_api_key: Groq API key (or use GROQ_API_KEY env var)
        """
        if Groq is None:
            raise ImportError("Groq library not installed. Install with: pip install groq")
        
        api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable or api_key parameter required")
        
        self.client = Groq(api_key=api_key)
        self.logger = logging.getLogger(__name__)
    
    async def extract_intent(self, user_message: str) -> Dict:
        """
        Extract business search intent from user message
        
        Args:
            user_message: What the user said
            
        Returns:
            Dict with service_type, location, and confidence
        """
        try:
            prompt = f"""
Extract business search information from this user request: "{user_message}"

Return a JSON response with:
- service_type: the type of business/service they want (e.g., "dentist", "restaurant", "mechanic")
- location: the location they mentioned (e.g., "Ahmedabad", "Mumbai", "near me")
- confidence: how confident you are (0.0 to 1.0)
- is_business_request: true if this is asking for a business, false otherwise

Examples:
"I need a dentist in Ahmedabad" -> {{"service_type": "dentist", "location": "Ahmedabad", "confidence": 0.95, "is_business_request": true}}
"Find me a good restaurant near me" -> {{"service_type": "restaurant", "location": "near me", "confidence": 0.85, "is_business_request": true}}
"What's the weather like?" -> {{"service_type": "", "location": "", "confidence": 0.0, "is_business_request": false}}

User request: "{user_message}"

Respond with ONLY the JSON, no other text:
"""

            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(result_text)
                self.logger.info(f"Extracted intent: {result}")
                return result
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse JSON response: {result_text}")
                return {
                    "service_type": "",
                    "location": "",
                    "confidence": 0.0,
                    "is_business_request": False
                }
                
        except Exception as e:
            self.logger.error(f"Intent extraction failed: {e}")
            return {
                "service_type": "",
                "location": "",
                "confidence": 0.0,
                "is_business_request": False
            }


class CallForwardingService:
    """Handle call forwarding to businesses"""
    
    def __init__(self, twilio_client):
        """
        Initialize call forwarding service
        
        Args:
            twilio_client: Twilio client instance
        """
        self.twilio_client = twilio_client
        self.logger = logging.getLogger(__name__)
    
    def forward_call(self, call_sid: str, target_phone: str) -> bool:
        """
        Forward active call to target phone number
        
        Args:
            call_sid: Twilio call SID
            target_phone: Phone number to forward to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the call to dial the target number
            call = self.twilio_client.calls(call_sid).update(
                url=f'http://twimlets.com/forward?PhoneNumber={target_phone}',
                method='POST'
            )
            
            self.logger.info(f"Call {call_sid} forwarded to {target_phone}")
            return True
            
        except Exception as e:
            self.logger.error(f"Call forwarding failed: {e}")
            return False
    
    def create_forward_twiml(self, target_phone: str, message: str = None) -> str:
        """
        Create TwiML for call forwarding
        
        Args:
            target_phone: Phone number to forward to
            message: Optional message to play before forwarding
            
        Returns:
            TwiML string
        """
        twiml_parts = ['<Response>']
        
        if message:
            twiml_parts.append(f'<Say>{message}</Say>')
        
        twiml_parts.extend([
            f'<Dial>{target_phone}</Dial>',
            '</Response>'
        ])
        
        return ''.join(twiml_parts)


class BusinessDirectoryBot:
    """Complete business directory bot with search and forwarding"""
    
    def __init__(self, groq_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        """
        Initialize business directory bot
        
        Args:
            groq_api_key: Groq API key
            google_api_key: Google Places API key
        """
        self.search_service = BusinessSearchService(google_api_key)
        self.intent_extractor = IntentExtractor(groq_api_key)
        self.logger = logging.getLogger(__name__)
    
    async def process_request(self, user_message: str) -> Tuple[str, List[Dict], bool]:
        """
        Process user request for business search
        
        Args:
            user_message: What the user said
            
        Returns:
            Tuple of (response_message, businesses_found, should_forward)
        """
        # Extract intent
        intent = await self.intent_extractor.extract_intent(user_message)
        
        if not intent['is_business_request'] or intent['confidence'] < 0.5:
            return (
                "I can help you find local businesses and connect you to them. "
                "Just tell me what service you need and in which area. "
                "For example, 'I need a dentist in Ahmedabad' or 'Find me a good restaurant nearby'.",
                [],
                False
            )
        
        service_type = intent['service_type']
        location = intent['location']
        
        if not service_type:
            return (
                "I'd be happy to help you find a business. "
                "Could you tell me what type of service you're looking for?",
                [],
                False
            )
        
        if not location or location.lower() in ['near me', 'nearby']:
            return (
                f"I can help you find a {service_type}. "
                "Could you tell me which city or area you'd like me to search in?",
                [],
                False
            )
        
        # Search for businesses
        businesses = await self.search_service.search_businesses(service_type, location)
        
        if not businesses:
            return (
                f"I'm sorry, I couldn't find any {service_type} listings in {location} right now. "
                "You might want to try calling directory assistance at 411 or search online.",
                [],
                False
            )
        
        # Format response
        response_parts = [f"I found {len(businesses)} {service_type} options in {location}:"]
        
        for i, business in enumerate(businesses, 1):
            rating_text = f" (rated {business['rating']} stars)" if business['rating'] != 'No rating' else ""
            status_text = f" - {business['open_now']}" if business['open_now'] != 'Hours unknown' else ""
            
            response_parts.append(
                f"{i}. {business['name']}{rating_text}{status_text}"
            )
        
        if len(businesses) == 1:
            response_parts.append(
                f"Would you like me to connect you to {businesses[0]['name']} at {businesses[0]['phone']}?"
            )
        else:
            response_parts.append(
                "Which one would you like me to connect you to? "
                "Just say the number or the name of the business."
            )
        
        return ('\n'.join(response_parts), businesses, True)
    
    def select_business(self, user_choice: str, available_businesses: List[Dict]) -> Optional[Dict]:
        """
        Select business based on user choice
        
        Args:
            user_choice: User's selection (number or name)
            available_businesses: List of available businesses
            
        Returns:
            Selected business dict or None
        """
        if not available_businesses:
            return None
        
        user_choice = user_choice.strip().lower()
        
        # Try to match by number
        if user_choice.isdigit():
            choice_num = int(user_choice)
            if 1 <= choice_num <= len(available_businesses):
                return available_businesses[choice_num - 1]
        
        # Try to match by name
        for business in available_businesses:
            if user_choice in business['name'].lower():
                return business
        
        # If only one option, return it
        if len(available_businesses) == 1:
            return available_businesses[0]
        
        return None


# Factory function for easy integration
def create_business_directory_service(groq_api_key: Optional[str] = None, 
                                    google_api_key: Optional[str] = None) -> BusinessDirectoryBot:
    """
    Create a business directory service with default configuration
    
    Args:
        groq_api_key: Groq API key (defaults to env var)
        google_api_key: Google Places API key (defaults to env var)
        
    Returns:
        Configured BusinessDirectoryBot instance
    """
    return BusinessDirectoryBot(groq_api_key, google_api_key) 