import psycopg2
import telegram
import logging
import json
import requests
import re
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from secrets import TOKEN
from datetime import datetime, timedelta

import re
from db import query_db
import hestia
import geocoding
from retry import retry

class Home:
    def __init__(self, address='', city='', url='', agency='', price=-1, location=(-1, -1), distance_to_center=None):
        self.address = address
        self.city = city
        self.url = url
        self.agency = agency
        self.price = price
        self.location = location
        self.distance_to_center = distance_to_center
        
    def __repr__(self):
        return str(self)
        
    def __str__(self):
        return f"Home({self.address}, {self.city}, {self.agency.title()}, {self.price}, {self.url}, distance_center=({self.distance_to_center}))"
        
    def __eq__(self, other):
        if self.address.lower() == other.address.lower():
            if self.city.lower() == other.city.lower():
                return True
        return False
    
    def validate(self):
        assert type(self.address) is str
        assert len(self.address) > 2

        assert type(self.city) is str
        assert len(self.city) > 2
        
        assert type(self.price) is float
        assert self.price > 1
        
        # # TODO: Not tested
        # assert type(self.location) is tuple
        # assert len(self.location) == 2
        # assert type(self.location[0]) is float
        # assert type(self.location[1]) is float
        # assert type(self.distance_to_center) is float
        

        assert "https://" in self.url

    def save(self):
        # TODO: Add location and distance_to_center to the database
        # hestia.query_db("INSERT INTO homes VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        hestia.query_db("INSERT INTO homes VALUES (%s, %s, %s, %s, %s, %s)",
            (self.url,
            self.address,
            self.city,
            self.price,
            self.agency,
            # self.location,
            # self.distance_to_center
            datetime.now().isoformat()))

    def geocode(self):
        latitude, longitude = geocoding.get_coordinate_location(self.address, self.city)
        self.location = (latitude, longitude)
        
        self.distance_to_center = geocoding.distance_to_city_center(latitude, longitude, self.city)

    @property
    def address(self):
        return self._address
        
    @address.setter
    def address(self, address):
        self._address = address
        
    @property
    def city(self):
        return self._parsed_city
        
    @city.setter
    def city(self, city):
        # Strip the trailing province if present
        if re.search(" \([a-zA-Z]{2}\)$", city):
            city = ' '.join(city.split(' ')[:-1])
    
        # Handle cities with two names and other edge cases
        if city.lower() in ["'s-gravenhage", "s-gravenhage"]:
            city = "Den Haag"
        elif city.lower() in ["'s-hertogenbosch", "s-hertogenbosch"]:
            city = "Den Bosch"
        elif city.lower() in ["alphen aan den rijn", "alphen a/d rijn"]:
            city = "Alphen aan den Rijn"
        elif city.lower() in ["koog aan de zaan", "koog a/d zaan"]:
            city = "Koog aan de Zaan"
        elif city.lower() in ["capelle aan den ijssel", "capelle a/d ijssel"]:
            city = "Capelle aan den IJssel"
        elif city.lower() in ["berkel-enschot", "berkel enschot"]:
            city = "Berkel-Enschot"
        elif city.lower() in ["oud-beijerland", "oud beijerland"]:
            city = "Oud-Beijerland"
        elif city.lower() in ["etten-leur", "etten leur"]:
            city = "Etten-Leur"
        elif city.lower() == "son en breugel":
            city = "Son en Breugel"
        elif city.lower() == "bergen op zoom":
            city = "Bergen op Zoom"
        elif city.lower() == "berkel en rodenrijs":
            city = "Berkel en Rodenrijs"
        elif city.lower() == "wijk bij duurstede":
            city = "Wijk bij Duurstede"
            
        self._parsed_city = city

    @property
    def location(self):
        return self._location
    
    @location.setter
    def location(self, location):
        self._location = location
    
    @property
    def distance_to_center(self):
        return self._distance_to_center
    
    @distance_to_center.setter
    def distance_to_center(self, distance_to_center):
        self._distance_to_center = distance_to_center


def escape_markdownv2(text):
    text = text.replace('.', '\.')
    text = text.replace('!', '\!')
    text = text.replace('+', '\+')
    text = text.replace('-', '\-')
    text = text.replace('*', '\*')
    return text

# WORKDIR = query_db("SELECT workdir FROM meta", fetchOne=True)["workdir"]

logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: %(message)s",
    level=logging.DEBUG,
    # filename=WORKDIR + "hestia.log"
)

BOT = telegram.Bot(TOKEN)

HOUSE_EMOJI = "\U0001F3E0"
LINK_EMOJI = "\U0001F517"
EURO_EMOJI = "\U0001F4B6"
LOVE_EMOJI = "\U0001F970"
CHECK_EMOJI = "\U00002705"
CROSS_EMOJI = "\U0000274C"

# The identifier of the used settings in the database (default = default)
SETTINGS_ID = "default"

# The Dockerfile replaces this with the git commit id
APP_VERSION = ''

def check_dev_mode():
    return query_db("SELECT devmode_enabled FROM meta", fetchOne=True)["devmode_enabled"]

def check_scraper_halted():
    return query_db("SELECT scraper_halted FROM meta", fetchOne=True)["scraper_halted"]
