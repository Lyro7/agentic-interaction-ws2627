import os
from urllib.parse import quote

import requests

tools = [
    {
        "type": "function",
        "function": {
            "name": "getCalendar",
            "description": "Get calendar events for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Calendar date in YYYY-MM-DD format."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "getWeather",
            "description": "Get the weather forecast for a city and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": 
                             "City slug, e.g. ulm or muenchen (Munich)."},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format."}
                },
                "required": ["city", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "getTransit",
            "description": "Get train connections between two cities on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Departure city slug, e.g. ulm."},
                    "destination": {"type": "string", "description": 
                                    "Arrival city slug, e.g. muenchen (Munich)."},
                    "date": {"type": "string", "description": "Departure date in YYYY-MM-DD format."}
                },
                "required": ["origin", "destination", "date"]
            }
        }
    }
]

def getCalendar(date: str):
    base_url = os.environ["DATA_BASE_URL"].rstrip("/")
    url = f"{base_url}/calendar/{date}.json"

    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return {"message": f"No calendar data available for {date}."}

    response.raise_for_status()

    return response.json()

def getWeather(city: str, date: str):
    base_url = os.environ["DATA_BASE_URL"].rstrip("/")
    url = f"{base_url}/weather/{quote(city, safe='')}/{quote(date, safe='')}.json"
    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return {"message": f"No weather data available for {city} on {date}."}

    response.raise_for_status()
    return response.json()

def getTransit(origin: str, destination: str, date: str):
    base_url = os.environ["DATA_BASE_URL"].rstrip("/")
    route = f"{quote(origin, safe='')}/{quote(destination, safe='')}"
    url = f"{base_url}/transit/{route}/{quote(date, safe='')}.json"
    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return {"message": f"No train data available from {origin} to {destination} on {date}."}

    response.raise_for_status()
    return response.json()

tool_handlers = {
    "getCalendar": getCalendar,
    "getWeather":  getWeather,
    "getTransit":  getTransit,
}
