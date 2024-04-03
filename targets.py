from abc import ABC, abstractmethod, abstractproperty
import sys
import json
import logging
from bs4 import BeautifulSoup
import re
import requests
from pprint import pformat

from hestia import Home
import hestia


class Target(ABC):  
  agency: str

  @abstractmethod
  def retrieve(self) -> list[Home]:
    pass

  async def execute(self):
    homes = self.retrieve()
    for home in homes:
      try:
        home.validate()
      except AssertionError:
        logging.error(f"Home validate error for home: {home}", exc_info=True)
    logging.debug(f"Homes found: {len(homes)}: {homes}")
    new_homes = self.filterOld(homes)
    self.save_homes(new_homes)
    logging.debug(f"For target {self.agency}: scraped {len(new_homes)} new homes")
    await self.broadcast(new_homes)

  def testScrape(self):
    logging.info(f"Testing scrape for target \"{self.agency}\"")
    homes = self.retrieve()
    for home in homes:
      try:
        home.validate()
      except AssertionError:
        logging.error(f"Home validate error for home: {home}", exc_info=True)

    logging.debug(f"Homes found: {len(homes)}: \n{pformat(homes)}")
    return homes

  async def broadcast(self, homes):
    subs = set()
    
    if hestia.check_dev_mode():
        subs = hestia.query_db("SELECT * FROM subscribers WHERE subscription_expiry IS NOT NULL AND telegram_enabled = true AND user_level > 1")
    else:
        subs = hestia.query_db("SELECT * FROM subscribers WHERE subscription_expiry IS NOT NULL AND telegram_enabled = true")
    
    messagesSent = 0

    for home in homes:
        for sub in subs:
            if home.price < sub["filter_min_price"] or home.price > sub["filter_max_price"]:
                continue
            
            if home.city.lower() not in sub["filter_cities"]:
                continue
            
            message = f"{hestia.HOUSE_EMOJI} {home.address}, {home.city}\n"
            message += f"{hestia.EURO_EMOJI} €{home.price}/m\n"
            if home.distance_to_center:
              message += f"Dist to center {home.distance_to_center} km\n\n"
            
            message = hestia.escape_markdownv2(message)
            
            message += f"{hestia.LINK_EMOJI} [{self.agency}]({home.url})"
            
            # If a user blocks the bot, this would throw an error and kill the entire broadcast
            try:
                await hestia.BOT.send_message(text=message, chat_id=sub["telegram_id"], parse_mode="MarkdownV2")
                messagesSent += 1
            except:
                pass
    
    logging.debug(f"Broadcast {messagesSent} messages to {len(subs)} people")

  def post(self, url, body, headers):
    r = requests.post(url, data=body, headers=headers)

    if not r.status_code == 200:
      raise ConnectionError(f"Got a non-OK status code: {r.status_code}")

    return r
  
  def parseFailSingleHome(self, res):
    logging.info(f"{self.agency} failed to parse a home {res}", exc_info=True)

  def get(self, url, headers):
    r = requests.get(url, headers=headers)

    if not r.status_code == 200:
      raise ConnectionError(f"Got a non-OK status code: {r.status_code}")

    return r
  
  def save_homes(self, homes: list[Home]):
    for home in homes:
      home.save()


  def filterOld(self, homes: list[Home]) -> list[Home]:
    prev_homes = []
    new_homes = []
    
    # Check retrieved homes against previously scraped homes (of the last 6 months)
    for home in hestia.query_db("SELECT address, city FROM homes WHERE date_added > now() - interval '180 day'"):
        prev_homes.append(hestia.Home(home["address"], home["city"]))
    
    for home in homes:
        if home not in prev_homes:
            new_homes.append(home)

    return new_homes

class Funda(Target):
  agency = "funda"

  def retrieve(self) -> list[Home]:
    url = "https://listing-search-wonen-arc.funda.io/listings-wonen-searcher-alias-prod/_reactivesearch?preference=_local&filter_path=-responses.aggregations.results.grid.buckets.global_ids.hits.hits._source%2C-responses._shards%2C-responses.aggregations.results.doc_count%2C-responses.**._index%2C-responses.**._score%2C-responses.**.doc_count_error_upper_bound%2C-responses.**.sum_other_doc_count%2C-responses.**._source.address.identifiers"
    headers = {
      "Authorization": "Basic ZjVhMjQyZGIxZmUwOjM5ZDYxMjI3LWQ1YTgtNDIxMi04NDY4LWU1NWQ0MjhjMmM2Zg=="
    }
    post_data = '''{
        "query": [
          {
            "id": "search_result",
            "from": 0,
            "size": 150,
            "type": "search",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "map_results",
                "object_type",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "search_result__internal"
              ]
            },
            "execute": true,
            "dataField": [
              "availability"
            ],
            "defaultQuery": {
              "sort": [
                {
                  "publish_date": "desc"
                },
                {
                  "placement_type": "asc"
                },
                {
                  "relevancy_sort_order": "desc"
                },
                {
                  "id.number": "desc"
                }
              ],
              "track_total_hits": true
            }
          },
          {
            "id": "selected_area",
            "type": "term",
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "customQuery": {
              "id": "location-query-v2",
              "params": {
                "location": [
                  "nl"
                ]
              }
            }
          },
          {
            "id": "offering_type",
            "type": "term",
            "value": "rent",
            "execute": false,
            "dataField": [
              "offering_type"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "sort",
            "type": "term",
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "customQuery": {}
          },
          {
            "id": "price",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id"
              ]
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "customQuery": {}
          },
          {
            "id": "floor_area",
            "type": "term",
            "react": {
              "and": "floor_area__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "plot_area",
            "type": "term",
            "react": {
              "and": "plot_area__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "bedrooms",
            "type": "term",
            "react": {
              "and": "bedrooms__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "rooms",
            "type": "term",
            "react": {
              "and": "rooms__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "exterior_space_garden_size",
            "type": "term",
            "react": {
              "and": "exterior_space_garden_size__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "garage_capacity",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "garage_capacity__internal"
              ]
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "publication_date",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "publication_date__internal"
              ]
            },
            "value": "no_preference",
            "execute": false,
            "dataField": [
              "publish_date_utc"
            ],
            "customQuery": {
              "id": "publish-date-query-v2",
              "params": {
                "date_to": null,
                "date_from": null
              }
            },
            "defaultQuery": {
              "id": "publish-date-aggs-v3",
              "params": {
                "timeout": "500ms",
                "date_1_to": "now",
                "date_2_to": "now",
                "date_3_to": "now",
                "date_4_to": "now",
                "date_5_to": "now",
                "date_6_to": null,
                "date_1_key": "1",
                "date_2_key": "3",
                "date_3_key": "5",
                "date_4_key": "10",
                "date_5_key": "30",
                "date_6_key": "no_preference",
                "date_1_from": "now-1d",
                "date_2_from": "now-3d",
                "date_3_from": "now-5d",
                "date_4_from": "now-10d",
                "date_5_from": "now-30d",
                "date_6_from": null
              }
            }
          },
          {
            "id": "object_type",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type"
            ],
            "defaultQuery": {
              "id": "object-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "availability",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "availability__internal"
              ]
            },
            "value": [
              "available",
              "negotiations"
            ],
            "execute": false,
            "dataField": [
              "availability"
            ],
            "defaultQuery": {
              "id": "availability-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "construction_type",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "construction_type__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "construction_type"
            ],
            "defaultQuery": {
              "id": "construction-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "construction_period",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "construction_period__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "construction_period"
            ],
            "defaultQuery": {
              "id": "construction-period-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "surrounding",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "surrounding__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "surrounding"
            ],
            "defaultQuery": {
              "id": "surrounding-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "garage_type",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "garage_type__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "garage.type"
            ],
            "defaultQuery": {
              "id": "garage-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "exterior_space_type",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "exterior_space_type__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "exterior_space.type"
            ],
            "defaultQuery": {
              "id": "exterior-space-type-aggs-v3",
              "params": {
                "value": {},
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "exterior_space_garden_orientation",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "exterior_space_garden_orientation__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "exterior_space.garden_orientation"
            ],
            "defaultQuery": {
              "id": "garden-orientation-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "energy_label",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "energy_label__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "energy_label"
            ],
            "defaultQuery": {
              "id": "energy-label-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "zoning",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "zoning__internal"
              ]
            },
            "value": [
              "residential"
            ],
            "execute": false,
            "dataField": [
              "zoning"
            ],
            "defaultQuery": {
              "id": "zoning-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "amenities",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "amenities__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "amenities"
            ],
            "defaultQuery": {
              "id": "amenities-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "type",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "type__internal"
              ]
            },
            "value": [
              "single"
            ],
            "execute": false,
            "dataField": [
              "type"
            ],
            "defaultQuery": {
              "id": "type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "nvm_open_house_day",
            "type": "term",
            "react": {
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "object_type",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house",
                "object_type_apartment_orientation",
                "object_type_apartment",
                "object_type_parking",
                "object_type_parking_capacity",
                "nvm_open_house_day__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "open_house_datetime_slot.is_nvm_open_house_day"
            ],
            "defaultQuery": {
              "id": "nvm-open-house-day-aggs-v1",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "free_text_search",
            "type": "search",
            "react": {
              "and": "free_text_search__internal"
            },
            "execute": false,
            "dataField": [
              "description.dutch"
            ],
            "customQuery": {}
          },
          {
            "id": "agent_id",
            "type": "term",
            "react": {
              "and": "agent_id__internal"
            },
            "execute": false,
            "dataField": [
              "reactive_component_field"
            ],
            "customQuery": {},
            "defaultQuery": {
              "timeout": "500ms"
            }
          },
          {
            "id": "object_type_house_orientation",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house",
                "object_type_house_orientation__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.house.orientation"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "house-orientation-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "object_type_house",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_house_orientation",
                "object_type_house__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.house.type"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "house-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "object_type_apartment_orientation",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_apartment",
                "object_type_apartment_orientation__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.apartment.orientation"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "apartment-orientation-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "object_type_apartment",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_apartment_orientation",
                "object_type_apartment__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.apartment.type"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "apartment-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "object_type_parking",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_parking_capacity",
                "object_type_parking__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.parking.type"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "parking-type-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          },
          {
            "id": "object_type_parking_capacity",
            "type": "term",
            "react": {
              "or": [
                "object_type"
              ],
              "and": [
                "selected_area",
                "offering_type",
                "sort",
                "price",
                "floor_area",
                "plot_area",
                "bedrooms",
                "rooms",
                "exterior_space_garden_size",
                "garage_capacity",
                "publication_date",
                "availability",
                "construction_type",
                "construction_period",
                "surrounding",
                "garage_type",
                "exterior_space_type",
                "exterior_space_garden_orientation",
                "energy_label",
                "zoning",
                "amenities",
                "type",
                "nvm_open_house_day",
                "free_text_search",
                "agent_id",
                "object_type_parking",
                "object_type_parking_capacity__internal"
              ]
            },
            "value": [],
            "execute": false,
            "dataField": [
              "object_type_specifications.parking.capacity"
            ],
            "customQuery": {},
            "defaultQuery": {
              "id": "parking-capacity-aggs-v3",
              "params": {
                "timeout": "500ms"
              }
            }
          }
        ],
        "settings": {
          "emptyQuery": true,
          "queryParams": {
            "preference": "_local",
            "filter_path": "-responses.aggregations.results.grid.buckets.global_ids.hits.hits._source,-responses._shards,-responses.aggregations.results.doc_count,-responses.**._index,-responses.**._score,-responses.**.doc_count_error_upper_bound,-responses.**.sum_other_doc_count,-responses.**._source.address.identifiers"
          },
          "recordAnalytics": false,
          "enableQueryRules": true,
          "suggestionAnalytics": true
        }
      }'''
    
    r = self.post(url, post_data, headers)
    results = json.loads(r.content)["search_result"]["hits"]["hits"]
    
    homes: list[Home] = []

    for res in results:
      try:
        # Some listings don't have house numbers, so skip
        if "house_number" not in res["_source"]["address"].keys():
            logging.warning("Skipping a house without house number")
            continue
        # Some listings don't have a rent_price, skip as well
        if "rent_price" not in res["_source"]["price"].keys():
            logging.warning("Skipping a house without price")
            continue
    
        home = Home(agency=self.agency)
        
        home.address = f"{res['_source']['address']['street_name']} {res['_source']['address']['house_number']}"
        if "house_number_suffix" in res["_source"]["address"].keys():
            suffix = res["_source"]["address"]["house_number_suffix"]
            if '-' not in suffix and '+' not in suffix:
                suffix = f" {suffix}"
            home.address += f"{suffix}"
        
        home.city = res["_source"]["address"]["city"]
        home.url = "https://funda.nl" + res["_source"]["object_detail_page_relative_url"]
        home.price = float(res["_source"]["price"]["rent_price"][0])
        
        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Spotmakelaardij(Target):
  agency = "spot"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.spotmakelaardij.nl"
    url = base_url + "/aanbod/woningaanbod/huur/"
    headers = {}
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find_all("li", class_="aanbodEntry")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        home.address = str(res.find(class_="street-address").get_text())
        home.city = str(res.find("span", class_="locality").get_text())
        home.price = float(res.find(class_="kenmerkValue").get_text().split(' ')[1].split(',')[0].replace('.', ''))
        home.url = base_url + res.find("a", class_="aanbodEntryLink")["href"]
        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue


    return homes
  
class Vbtverhuurmakelaars(Target):
  agency = "vbt"

  def retrieve(self) -> list[Home]:
    base_url = "https://vbtverhuurmakelaars.nl"
    url = base_url + "/api/properties/12/1?search=true"
    headers = {}
    r = self.get(url, headers)
    results = json.loads(r.content)["houses"]

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        home.address = str(res["address"]["house"])
        home.city = str(res["address"]["city"])
        home.price = float(res["prices"]["rental"]["price"])
        home.url = base_url + res["url"]
        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue


    return homes
  
class Huurwoningennl(Target):
  agency = "huurwoningennl"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.huurwoningen.nl"
    url = base_url + "/aanbod-huurwoningen/?interior=kaal"
    headers = {}
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find_all("li", class_="search-list__item search-list__item--listing")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        home.address = str(res.find(class_="listing-search-item__link listing-search-item__link--title").get_text()).strip() # Only street name
        home.city = str(' '.join(res.find("div", "listing-search-item__sub-title'").get_text() # 4205 ET Gorinchem (Haarwijk West)
                          .split(" (")[0] # 4205 ET Gorinchem
                          .strip()
                          .split(" ")[2:] # Gorinchem
                          ))
        home.price = float(res.find(class_="listing-search-item__price").get_text()
                          .split('\xa0')[1]
                          .split(" ")[0]
                          .replace(".", ""))
        home.url = base_url + res.find(class_="listing-search-item__link")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue
    return homes

class DeKeizer(Target):
  agency = "dekeizer"

  def retrieve(self) -> list[Home]:
    url = "https://www.dekeizer.nl/woningen/"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    r = self.post(url, "__hash=q1Yqzs8vKlGyUsooLS1S0lHKScxLAfLyUlNSi8BsHaX8IiA7qRIompJYkmqVklqcrFQLAA&__live=1&__templates%5B%5D=search&__templates%5B%5D=loop&__maps=all", headers)
    r = json.loads(r.content)["templates"]["loop"]
    results = BeautifulSoup(r, "html.parser").find_all(id="entity-items")

    homes  = []
    for res in results:
      # logging.debug(res)
      try:
        home = Home(agency=self.agency)
        card = res.find(class_="card-body")
        home.address = str(card.find_all("h2")[0].get_text()).strip()
        home.city = str(card.find_all("h3")[0].get_text().split(", ")[-1]).strip()
        home.price = float(card.find_all("h3")[2].get_text().split(" ")[1].split(",")[0].replace(".",""))
        home.url = res.find("a")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class RosVerhuurMakelaar(Target):
  agency = "rosverhuurmakelaar"

  def retrieve(self) -> list[Home]:
    link_base_url = "https://www.rosverhuurmakelaar.nl/woning"
    url = "https://cdn.eazlee.com/eazlee/api/query_functions.php"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "action=all_houses&api=dc331598ff92f156d3567affae4641bf&filter=status%3Drent&offsetRow=0&numberRows=100&leased_wr_last=true&leased_last=true&sold_wr_last=true&sold_last=true&path=%2Fwoning-aanbod%3Fstatus%3Drent&html_lang=nl"
    r = self.post(url, body, headers)
    results = json.loads(r.content)

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        if (res["forrent"] != "1"):
          continue

        home.address = f"{res['street']} {res['number']}"
        home.city = res['city']
        home.price = float(res['price'])
        home.url = f"{link_base_url}?{home.city}/{res['street'].replace(' ', '-')}/{res['house_id']}" # this is the stupidest design I have seen....

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes
  
class YourHouseNl(Target):
  agency = "yourhousenl"

  def retrieve(self) -> list[Home]:
    base_url = "https://your-house.nl"
    url = base_url + "/0-2ac6/aanbod-pagina"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "moveunavailablelistingstothebottom=true&orderby=10&orderdescending=true&take=50&availability=Available"
    r = self.post(url, body, headers)
    # results = json.loads(r.content)
    results = BeautifulSoup(r.content, "html.parser").find_all("article", class_="objectcontainer")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        home.address = res.find("span", class_="street").get_text().strip()
        home.city = res.find("span", class_="location").get_text().strip()
        home.price = float(res.find("span", class_="obj_price").get_text()
                          .strip()
                          .split(" ")[1]
                          .split(",")[0]
                          .replace(".", "")
                          )
        home.url = base_url + res.find("a", class_="obj_price")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

# Zelfde CMS als YourHouseNl
class VgwGroup(Target):
  agency = "vgwgroup"

  def retrieve(self) -> list[Home]:
    base_url = "https://vgwgroup.nl"
    url = base_url + "/0-2ac6/aanbod-pagina"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "forsaleorrent=FOR_RENT&pricerange.minprice=400&take=40&typegroups%5B0%5D=19&typegroups%5B1%5D=18"
    r = self.post(url, body, headers)
    # results = json.loads(r.content)
    results = BeautifulSoup(r.content, "html.parser").find_all("article", class_="objectcontainer")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        if (res.find(class_="object_status rented")):
          continue

        home.address = res.find("span", class_="street").get_text().strip()
        home.city = res.find("span", class_="location").get_text().strip()
        home.price = float(res.find("span", class_="obj_price").get_text()
                          .strip()
                          .split(" ")[1]
                          .split(",")[0]
                          .replace(".", "")
                          )
        home.url = base_url + res.find("a", class_="obj_price")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

# Zelfde CMS als Huurwoningennl
class Pararius(Target):
  agency = "pararius"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.pararius.nl"
    url = base_url + "/huurwoningen/nederland"
    headers = {
       'Cookie': "fl_mgc=SwSmlsNcYOXCeQrtyhjfKlRqMnzmeQVAEJRDeLKehwAEsEEj; fl_ctx=eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0..theMRGPOt0IJMAxDdIg-og.tWZBc9xdK0EBYyHk_Lu7nGjiIJtWZgAQKoYyIASbDnb3Y5f1Gq93sx-c4fEqoqSC6XI2nFvgOsALZtOfXqPvs59bwV_zRqmd5wOngLplCTjjb97tWe785jUwUsM1s9LTvle4faGWom84FkKUTINccjjof-rnNJv0DQxPpKEuqZc8jAhW-F2yq5qi-6NHHBov0e-ya-NwPkt9Q6EiO95W7DYjjqqYZaQ-5y3ATaygVp4IuhxDIReokqQZY4CTqymCipHJJPjVCZGMngvgG5EfCAa-uZpN2KAn-kYc7d13Ti9wBg9lSKO8wA3Ao5e-YdQHsrdU5QffrPkAi9nCbhBBQRw530GFrVnYfSJtjxEjHIQwTtNyEzWOCDITGrDQp1Qqx8K3VE9NlzvHDEhiajsYEOilvmxAcYyaKfW3BBQ8s9_kppIQ-PvlFemW-fde9D0ah5IqyURagyDW3yRPoZBEpg.40dDiPC0EtGK5dfNJ3d8_w"
    }
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find_all("section", class_="listing-search-item listing-search-item--list listing-search-item--for-rent")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        raw_address = str(res.find("a", class_="listing-search-item__link--title").get_text().strip())
        # A lot of properties on Pararius don't include house numbers, so it's impossible to keep track of them because
        # right now homes are tracked by address, not by URL (which has its own downsides).
        # This is probably not 100% reliable either, but it's close enough.
        if not re.search("[0-9]", raw_address):
            continue
        if re.search("^[0-9]", raw_address): # Filter "1e Foobarstraat", etc.
            continue

        home.address = ' '.join(raw_address.split(' ')[1:]) # All items start with one of ["Appartement", "Huis", "Studio", "Kamer"]
        home.city = ' '.join(res.find("div", "listing-search-item__sub-title'").get_text() # 4205 ET Gorinchem (Haarwijk West)
                          .split(" (")[0] # 4205 ET Gorinchem
                          .strip()
                          .split(" ")[2:] # Gorinchem
                          )
        priceText = res.find(class_="listing-search-item__price").get_text().strip()
        if "op aanvraag" in priceText:
          continue
        home.price = float(priceText.split('\xa0')[1]
                          .split(" ")[0]
                          .replace(".", ""))
        home.url = base_url + res.find("a", class_="listing-search-item__link")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Interhouse(Target):
  agency = "interhouse"

  def retrieve(self) -> list[Home]:
    url = "https://interhouse.nl/wp-admin/admin-ajax.php"
    headers = {
       'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8"
    }
    body = "action=building_results_action&query=%3Fnumber_of_results%3D20%26sort%3Ddate-desc%26display%3Dlist%26paging%3D1%26language%3Dnl_NL"
    r = self.post(url, body, headers)
    results = BeautifulSoup(r.content, "html.parser").find_all("div", class_="c-result-item building-result c-result-item--horizontal")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        home.address = res.find("span", class_="c-result-item__title-address").get_text()
        home.city = res.find("p", class_="c-result-item__location-label").get_text()
        home.price = float(res.find(class_="c-result-item__price-label").get_text().split(" ")[1].replace(".", ""))
        home.url = res.find("a")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes
   
# Similar to dekeizer cms
class Domvast(Target):
  agency = "domvast"

  def retrieve(self) -> list[Home]:
    url = "https://domvast.nl/woningen/huur/"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    r = self.post(url, "__live=1&__templates%5B%5D=search&__templates%5B%5D=loop&adres=&plaats=&status%5B%5D=beschikbaar&status%5B%5D=&prijs=&orderby=status%3Aasc", headers)
    r = json.loads(r.content)["templates"]["loop"]
    results = BeautifulSoup(r, "html.parser").find_all("article")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        card = res.find(class_="item-content")
        home.address = str(card.find_all("h2")[1].get_text()).strip()
        home.city = str(card.find_all("h2")[0].get_text().split(", ")[-1]).strip()
        home.price = float(card.find_all("dd")[0].get_text().split(" ")[1].split(",")[0].replace(".",""))
        home.url = res.find("a")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes
  
class Coverswonen(Target):
  agency = "coverswonen"

  def retrieve(self) -> list[Home]:
    base_url = "https://coverswonen.nl"
    url = base_url + "/aanbod/huur"
    headers = {
      #  "Content-Type": "application/x-www-form-urlencoded"
    }
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find_all(class_="thumbs-item")

    homes  = []
    for res in results:
      try:
        res = res.find(class_="text-wr wow fadeInUp")
        home = Home(agency=self.agency)
        if "Te huur" not in res.find(class_="bordered-bottom").get_text():
          continue

        # In the address name they append the city. To make easier, only allow utrecht for now...
        if res.find("a").get_text().strip().split(" ")[-1] != "Utrecht":
          continue

        home.address = ' '.join(res.find("a").get_text().strip().split(" ")[:-1])
        home.city = "Utrecht"
        home.price = float(res.find_all("p")[0].get_text().strip().split(" ")[1].replace(".", ""))
        home.url = base_url + res.find("a")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Starthousing(Target):
  agency = "starthousing"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.starthousing.nl"
    url = base_url + "/0-2ac6/aanbod-pagina"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "forsaleorrent=FOR_RENT&moveunavailablelistingstothebottom=true&take=50&minarea=0"
    r = self.post(url, body, headers)
    results = BeautifulSoup(r.content, "html.parser").find("div", class_="object_list")
    results = results.find_all(class_="object")
      

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        # Vagueness where the adres is inserted into the title, we are going to make it easier here...
        title = res.find(class_="object_header").find("h2").get_text().strip() # Te huur: Gestoffeerd 2-kamerappartment op toplocatie met tuin!
        if "Utrecht" not in title:
          continue

        home.address = title.split(": ")[1].split(", ")[0]
        home.city = "Utrecht"
        home.price = float(res.find(class_="object_price").get_text().strip().split(" ")[1].split(",")[0].replace(".", ""))
        home.url = base_url + res.find("a", class_="sys-property-link")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Rotsvast(Target):
  agency = "rotsvast"

  def retrieve(self) -> list[Home]:
    url = "https://www.rotsvast.nl/ajax.php?f=search&m=Properties"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    r = self.post(url, "type=2&office=0&count=30", headers)
    r = json.loads(r.content)["html"]
    results = BeautifulSoup(r, "html.parser").find_all(class_="residence-gallery")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        home.address = res.find(class_="residence-street").get_text().strip()
        home.city = ' '.join(res.find(class_="residence-zipcode-place").get_text().strip().split(" ")[1:])
        home.price = float(res.find(class_="residence-price").get_text().strip().split(" ")[1].replace(".","").replace(",",".")) # &euro;2.100,00 p/mnd excl.
        home.url = res.find(class_="clickable-block")['href']

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Makelaardijstek(Target):
  agency = "makelaardijstek"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.makelaardijstek.nl"
    url = base_url + "/woningaanbod/huur?moveunavailablelistingstothebottom=true"
    headers = {}
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find("div", class_="object_list")
    results = results.find_all(class_="object")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        if "Nieuw in verhuur" not in res.find(class_="object_status").get_text():
          continue
        
        title = res.find(class_="object_address").find("h2").get_text().strip() # Te huur: Lauwerhof 25, 3512VD Utrecht
        title = title.split(": ")[1] # Lauwerhof 25, 3512VD Utrecht

        # Title is sometimes BEZICHTIGEN VOL - VIEWINGS FULL
        if "vol" in title.lower():
          continue

        home.address = title.split(", ")[0]
        home.city = ' '.join(title.split(", ")[1].split(" ")[1:])
        home.price = float(res.find(class_="obj_price").get_text().strip().split(" ")[1].split(",")[0].replace(".", ""))
        home.url = base_url + res.find(class_="object_address").find("a")['href']

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Vbo(Target):
  agency = "vbo"

  def retrieve(self) -> list[Home]:
    url = "https://www.vbo.nl/huurwoningen"
    headers = {}
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find("div", class_="properties")
    results = results.find_all("figure", class_="property")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        home.address = res.find(class_="street").get_text().strip()
        home.city = res.find(class_="city").get_text().strip()
        home.price = float(res.find(class_="price").get_text().strip().split(" ")[1].split(",")[0].replace(".", ""))
        home.url = res.parent['href']

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

class Rebohuurwoning(Target):
  agency = "rebohuurwoning"

  def retrieve(self) -> list[Home]:
    base_url = "https://www.rebohuurwoning.nl"
    url = base_url + "/nl/aanbod/"
    headers = {}
    r = self.get(url, headers)
    results = BeautifulSoup(r.content, "html.parser").find(id="properties_list").find_all("div", class_="property")

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)

        t = res.find(class_="text")

        home.address = t.find("p").get_text().strip()
        home.city = t.find("h4").get_text().strip()
        try: # <div class="price">€  </div></div>
          home.price = float(res.find(class_="price").get_text().strip().split(" ")[1].replace(".", ""))
        except:
          continue
        home.url = base_url + res.find("a")["href"]

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes
  

  # Same CMS as RosVerhuurMakelaar
class SelectAHouse(Target):
  agency = "selectahouse"

  def retrieve(self) -> list[Home]:
    link_base_url = "https://www.rosverhuurmakelaar.nl/woning"
    url = "https://cdn.eazlee.com/eazlee/api/query_functions.php"
    headers = {
       "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "action=all_houses&api=54d6755fb4708e526f3c1cf8feff51af&filter=status%3Drent%26sort%3Dnew&offsetRow=0&numberRows=99&leased_wr_last=true&leased_last=true&sold_wr_last=true&sold_last=true&path=%2Fwoningaanbod%3Fstatus%3Drent%26sort%3Dnew&html_lang=nl"
    r = self.post(url, body, headers)
    results = json.loads(r.content)

    homes  = []
    for res in results:
      try:
        home = Home(agency=self.agency)
        if (res["forrent"] != "1"):
          continue

        home.address = f"{res['street']} {res['number']}"
        home.city = res['city']
        home.price = float(res['price'])
        home.url = f"{link_base_url}?{home.city}/{res['street'].replace(' ', '-')}/{res['house_id']}" # this is the stupidest design I have seen....

        homes.append(home)
      except:
        self.parseFailSingleHome(res)
        continue

    return homes

targets = [
  Funda(),
  Spotmakelaardij(),
  Vbtverhuurmakelaars(),
  Huurwoningennl(),
  DeKeizer(),
  RosVerhuurMakelaar(),
  YourHouseNl(),
  VgwGroup(),
  Pararius(),
  Interhouse(),
  Domvast(),
  Coverswonen(),
  Starthousing(),
  Rotsvast(),
  Makelaardijstek(),
  Vbo(),
  Rebohuurwoning(),
  SelectAHouse(),
]

async def scrapeAllTargets():
  for target in targets:
    try:
      await target.execute()
    except Exception as e:
      logging.error(f"Target {target.agency} failed to scrape", exc_info=e)