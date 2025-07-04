import asyncio
import logging
from typing import Dict, List, Optional, Any
import googlemaps
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)

class PlacesClient:
    """Client for Google Places API business search"""
    
    def __init__(self):
        api_key = settings.GOOGLE_PLACES_API_KEY
        if not api_key or api_key.startswith("test_") or api_key == "your_google_places_api_key_here":
            logger.warning("⚠️ Using mock Google Places client (no valid API key)")
            self.client = None
            self.mock_mode = True
        else:
            try:
                self.client = googlemaps.Client(key=api_key)
                self.mock_mode = False
                logger.info("✅ Google Places client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Google Places client: {e}. Using mock mode.")
                self.client = None
                self.mock_mode = True
    
    async def search_businesses(self, business_type: str, location: str, requirements: List[str] = None) -> List[Dict[str, Any]]:
        """Search for businesses using Google Places API"""
        try:
            # Handle mock mode
            if self.mock_mode:
                return self._get_mock_search_results(business_type, location)
                
            # Proceed with real API
            # Handle missing or vague location
            if not location or location.lower() in ["near me", "nearby", "close by"]:
                logger.warning("⚠️ No specific location provided for business search")
                return [{
                    "name": "Location Required",
                    "error": "location_required",
                    "message": "I need to know your location to search for businesses. Could you please tell me what city or area you're in?"
                }]
            
            # Build search query
            query = f"{business_type} in {location}"
            if requirements:
                query += f" {' '.join(requirements)}"
            
            logger.info(f"🔍 Searching for: {query}")
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                self._search_places_sync, 
                query, 
                location, 
                requirements
            )
            
            # Filter and rank results
            filtered_results = self._filter_and_rank_results(results, requirements)
            
            logger.info(f"📍 Found {len(filtered_results)} relevant businesses")
            return filtered_results[:settings.MAX_SEARCH_RESULTS]
            
        except Exception as e:
            logger.error(f"❌ Error searching businesses: {e}")
            return []
    
    def _search_places_sync(self, query: str, location: str, requirements: List[str] = None) -> List[Dict]:
        """Synchronous Places API search (runs in thread pool)"""
        try:
            # First try text search
            places_result = self.client.places(
                query=query,
                location=location,
                radius=50000,  # 50km radius
                type='establishment'
            )
            
            results = places_result.get('results', [])
            
            # If not enough results, try nearby search with specific type
            if len(results) < 3:
                # Map business types to Google Places types
                place_type = self._map_business_type_to_google_type(query.split()[0])
                
                if place_type:
                    # Get coordinates for location
                    geocode_result = self.client.geocode(location)
                    if geocode_result:
                        location_coords = geocode_result[0]['geometry']['location']
                        
                        nearby_result = self.client.places_nearby(
                            location=location_coords,
                            radius=25000,  # 25km radius
                            type=place_type
                        )
                        
                        # Combine results, avoiding duplicates
                        existing_place_ids = {place.get('place_id') for place in results}
                        for place in nearby_result.get('results', []):
                            if place.get('place_id') not in existing_place_ids:
                                results.append(place)
            
            # Enhance results with additional details
            enhanced_results = []
            for place in results[:10]:  # Limit to avoid quota issues
                try:
                    # Get place details
                    place_id = place.get('place_id')
                    if place_id:
                        details = self.client.place(
                            place_id=place_id,
                            fields=['name', 'rating', 'formatted_phone_number', 'formatted_address', 
                                   'opening_hours', 'website', 'price_level']
                        )
                        
                        # Merge basic and detailed info
                        enhanced_place = {**place, **details.get('result', {})}
                        enhanced_results.append(enhanced_place)
                    else:
                        enhanced_results.append(place)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not get details for place: {e}")
                    enhanced_results.append(place)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"❌ Places API error: {e}")
            return []
    
    def _map_business_type_to_google_type(self, business_type: str) -> Optional[str]:
        """Map user business type to Google Places type"""
        type_mapping = {
            'restaurant': 'restaurant',
            'food': 'restaurant',
            'pizza': 'restaurant',
            'coffee': 'cafe',
            'cafe': 'cafe',
            'dentist': 'dentist',
            'doctor': 'doctor',
            'hospital': 'hospital',
            'pharmacy': 'pharmacy',
            'bank': 'bank',
            'atm': 'atm',
            'gas': 'gas_station',
            'fuel': 'gas_station',
            'mechanic': 'car_repair',
            'repair': 'car_repair',
            'hotel': 'lodging',
            'gym': 'gym',
            'store': 'store',
            'shopping': 'shopping_mall',
            'mall': 'shopping_mall',
            'beauty': 'beauty_salon',
            'salon': 'beauty_salon',
            'lawyer': 'lawyer',
            'real_estate': 'real_estate_agency'
        }
        
        business_lower = business_type.lower()
        for key, google_type in type_mapping.items():
            if key in business_lower:
                return google_type
        
        return None
    
    def _filter_and_rank_results(self, results: List[Dict], requirements: List[str] = None) -> List[Dict[str, Any]]:
        """Filter and rank search results based on requirements and quality"""
        try:
            if not results:
                return []
            
            filtered_results = []
            requirements = requirements or []
            
            for place in results:
                # Basic filtering
                rating = place.get('rating', 0)
                if rating < settings.MIN_RATING:
                    continue
                
                # Check requirements
                meets_requirements = True
                if requirements:
                    for req in requirements:
                        if not self._check_requirement(place, req):
                            meets_requirements = False
                            break
                
                if not meets_requirements:
                    continue
                
                # Create standardized result format
                standardized = self._standardize_place_result(place)
                filtered_results.append(standardized)
            
            # Sort by ranking score
            filtered_results.sort(key=self._calculate_ranking_score, reverse=True)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ Error filtering results: {e}")
            return results  # Return unfiltered if error
    
    def _check_requirement(self, place: Dict, requirement: str) -> bool:
        """Check if a place meets a specific requirement"""
        req_lower = requirement.lower()
        
        # Check for "open now"
        if 'open' in req_lower:
            opening_hours = place.get('opening_hours', {})
            return opening_hours.get('open_now', True)  # Default to True if unknown
        
        # Check for rating requirements
        if 'highly rated' in req_lower or 'good rating' in req_lower:
            rating = place.get('rating', 0)
            return rating >= 4.5
        
        # Check for price level
        if 'cheap' in req_lower or 'affordable' in req_lower:
            price_level = place.get('price_level', 2)
            return price_level <= 2
        
        if 'expensive' in req_lower or 'upscale' in req_lower:
            price_level = place.get('price_level', 2)
            return price_level >= 3
        
        # Check for specific services/features in types or name
        place_text = f"{place.get('name', '')} {' '.join(place.get('types', []))}".lower()
        return req_lower in place_text
    
    def _standardize_place_result(self, place: Dict) -> Dict[str, Any]:
        """Convert Google Places result to standardized format"""
        return {
            'place_id': place.get('place_id'),
            'name': place.get('name', 'Unknown Business'),
            'rating': place.get('rating'),
            'user_ratings_total': place.get('user_ratings_total', 0),
            'phone': place.get('formatted_phone_number'),
            'address': place.get('formatted_address', place.get('vicinity')),
            'website': place.get('website'),
            'open_now': place.get('opening_hours', {}).get('open_now'),
            'price_level': place.get('price_level'),
            'types': place.get('types', []),
            'location': place.get('geometry', {}).get('location'),
            
            # Calculated fields
            'display_rating': f"{place.get('rating', 'N/A')} stars" if place.get('rating') else "No rating",
            'status': "Open now" if place.get('opening_hours', {}).get('open_now') else "Closed" if place.get('opening_hours', {}).get('open_now') is False else "Hours unknown"
        }
    
    def _calculate_ranking_score(self, place: Dict) -> float:
        """Calculate ranking score for sorting results"""
        score = 0.0
        
        # Rating weight (40% of score)
        rating = place.get('rating', 0)
        if rating:
            score += (rating / 5.0) * 40
        
        # Number of reviews weight (30% of score)
        review_count = place.get('user_ratings_total', 0)
        if review_count:
            # Normalize review count (log scale)
            import math
            normalized_reviews = min(math.log10(review_count + 1) / 3.0, 1.0)
            score += normalized_reviews * 30
        
        # Open status weight (20% of score)
        if place.get('open_now'):
            score += 20
        
        # Has phone number weight (10% of score)
        if place.get('phone'):
            score += 10
        
        return score
    
    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific place"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.place(
                    place_id=place_id,
                    fields=['name', 'rating', 'formatted_phone_number', 'formatted_address',
                           'opening_hours', 'website', 'reviews', 'photos']
                )
            )
            
            return result.get('result')
            
        except Exception as e:
            logger.error(f"❌ Error getting place details: {e}")
            return None
    
    def _get_mock_search_results(self, business_type: str, location: str) -> List[Dict[str, Any]]:
        """Return mock search results for testing"""
        mock_results = [
            {
                'place_id': 'mock_1',
                'name': f'Mock {business_type.title()} #1',
                'rating': 4.5,
                'user_ratings_total': 150,
                'phone': '+1-555-0101',
                'address': f'123 Main St, {location}',
                'website': 'https://example1.com',
                'open_now': True,
                'price_level': 2,
                'types': [business_type.lower()],
                'location': {'lat': 40.7128, 'lng': -74.0060},
                'display_rating': '4.5 stars',
                'status': 'Open now'
            },
            {
                'place_id': 'mock_2', 
                'name': f'Mock {business_type.title()} #2',
                'rating': 4.2,
                'user_ratings_total': 89,
                'phone': '+1-555-0102',
                'address': f'456 Oak Ave, {location}',
                'website': 'https://example2.com',
                'open_now': True,
                'price_level': 1,
                'types': [business_type.lower()],
                'location': {'lat': 40.7580, 'lng': -73.9855},
                'display_rating': '4.2 stars',
                'status': 'Open now'
            },
            {
                'place_id': 'mock_3',
                'name': f'Mock {business_type.title()} #3', 
                'rating': 4.7,
                'user_ratings_total': 203,
                'phone': '+1-555-0103',
                'address': f'789 Pine St, {location}',
                'website': 'https://example3.com',
                'open_now': False,
                'price_level': 3,
                'types': [business_type.lower()],
                'location': {'lat': 40.7589, 'lng': -73.9851},
                'display_rating': '4.7 stars',
                'status': 'Closed'
            }
        ]
        
        logger.info(f"🎭 Returning mock search results for '{business_type}' in '{location}'")
        return mock_results

# Create global instance
places_client = PlacesClient() 