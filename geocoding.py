import requests
import time
from math import radians, sin, cos, sqrt, atan2
import datetime
from city_centers import city_centers
from retry import retry

from db import query_db

API_KEY = "660bfd768a466267341390xki1f15c5"

@retry(waitTime=1.1, times=2, exceptions=(RuntimeError))
def get_cached_city_center(city: str):
    print(f"get_cached_city_center: {city}")
    if city in city_centers:
        return city_centers[city]
    
    location = get_coordinate_location(city)
    if location is not None:
        # Squeak
        print(f"get_cached_city_center: {city} not in cache, but did find it at {location}")
        return location

    return (None, None)

    
@retry(waitTime=1.1, times=2, exceptions=(RuntimeError))
def get_coordinate_location(address, city=None):
    """
    Get the coordinates (latitude, longitude) of a given address using the Maps.co Geocoding API.
    API Example: https://geocode.maps.co/search?q=Kromme%20Nieuwegracht&api_key=660bfd768a466267341390xki1f15c5
    """

    # If city is provided, append it to the address
    if city:
        address = f"{address}%20{city}"

    # Replace spaces with %20 in address
    address = address.replace(' ', '%20')

    # Construct the API URL
    url = f"https://geocode.maps.co/search?q={address}&api_key={API_KEY}"
    
    print(f"Getting coordinates for: {address}, url: {url}")

    # Send the GET request to the API
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Check if the response contains any results
        if data:
            # Get the coordinates from the first result
            result = data[0]
            latitude = result['lat']
            longitude = result['lon']

            # Return the coordinates as a tuple
            return latitude, longitude
        else:
            print("No results found for the given address.")
    else:
        print(f"Error: {response.status_code}")
        raise RuntimeError(response.status_code)
        

    # # Return None if no coordinates were found
    # return None

def distance_to_city_center(latitude: str, longitude: str, city: str):
    """
    Calculate the distance (km) between a given address and the city center of a given city.
    https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    """
    def haversine(lat1, lon1, lat2, lon2):
      """
      Calculate the great circle distance between two points
      on the earth (specified in decimal degrees)
      """
      # Convert decimal degrees to radians
      lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

      # Haversine formula
      dlat = lat2 - lat1
      dlon = lon2 - lon1
      a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
      c = 2 * atan2(sqrt(a), sqrt(1-a))
      r = 6371  # Radius of the earth in kilometers. Use 3956 for miles.
      distance = r * c

      return distance

    # if city not in city_center_coordinates:
    #     print(f"Error: City '{city}' not found in the city center coordinates.")
    #     return None
    
    if not latitude or not longitude:
        print("Error: Invalid coordinates.")
        return None

    # Get the coordinates of the city center
    city_latitude, city_longitude = get_cached_city_center(city)
    if city_latitude is None:
        raise RuntimeError(f"Could not get_cached_city_center for {city}") 

    print(f"Address coordinates: {float(latitude)}, {float(longitude)}")
    print(f"City ({city}) coordinates: {city_latitude}, {city_longitude}")

    # Calculate the distance using the Haversine formula
    distance = haversine(float(latitude), float(longitude), float(city_latitude), float(city_longitude))

    return distance
