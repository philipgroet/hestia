import logging
from pprint import pformat
import time
import traceback
from city_centers import city_centers

from retry import retry
logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: %(message)s",
    level=logging.DEBUG,
)


# latitude, longitude = get_coordinate_location("Kromme Nieuwegracht", "Utrecht")
# print(f"Lattitude {latitude}, Longitude {longitude}")
# print(f"{latitude}, {longitude}")

# distance = distance_to_city_center(latitude, longitude, "Utrecht")
# print(f"Distance to city center: {distance:.2f} km")


from targets import Makelaardijstek
target = Makelaardijstek()
homes = target.testScrape()
for home in homes:
  # try:
  #   home.geocode()
  # except:
  #   print("Error geocoding home")
  print(home)


  
# homes[0].geocode()
# homes[0].geocode()