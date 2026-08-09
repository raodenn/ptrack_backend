from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from typing import Optional, Dict, Any

geolocator = Nominatim(user_agent="ptrack")

def reverse_geocode_centroid(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Reverse geocodes centroid coordinates to fetch address and location info.
    """
    try:
        location = geolocator.reverse((lat, lon), timeout=5, exactly_one=True)
        
        if location:
            raw_address = location.raw.get("address", {})
            
            venue_name = (
                raw_address.get("amenity") or 
                raw_address.get("building") or 
                raw_address.get("shop") or 
                location.address
            )
            
            return {
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "venue_name": venue_name,
                "raw_address": raw_address
            }
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"[ptrack] Reverse geocoding failed for ({lat}, {lon}): {e}")
        
    return None

centroid_lat, centroid_lng = 37.7749, -122.4194
res = reverse_geocode_centroid(centroid_lat, centroid_lng)

if res:
    print(f"Venue Name: {res['venue_name']}")
    print(f"Address:    {res['address']}")
    print(f"Coords:     {res['latitude']}, {res['longitude']}")