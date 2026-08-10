import logging
import requests

from jarvis.config import HTTP_TIMEOUT
from jarvis.logging_config import setup_logging


logger = setup_logging()


# ==========================================
# WEATHER TOOL
# ==========================================

def get_weather(city, days=0):
    """
    Get weather forecast for a city.

    days:
        0 = today
        1 = tomorrow
        2 = day after tomorrow
    """

    try:

        # ----------------------------------
        # Normalize input
        # ----------------------------------

        city = str(city).strip()

        if not city:
            return {
                "success": False,
                "error": "City name is missing."
            }

        # ----------------------------------
        # Validate days
        # ----------------------------------

        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 0

        if days < 0:
            days = 0

        # Open-Meteo normally supports forecasts
        # several days into the future.
        if days > 15:
            return {
                "success": False,
                "error": "Weather forecast is limited to 15 days."
            }

        # ==================================
        # GEOCODING
        # ==================================

        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
        )

        geo_params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        geo_response = requests.get(
            geo_url,
            params=geo_params,
            timeout=HTTP_TIMEOUT
        )

        geo_response.raise_for_status()

        geo_data = geo_response.json()

        if not geo_data.get("results"):
            return {
                "success": False,
                "error": f"I could not find {city}."
            }

        location = geo_data["results"][0]

        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location["name"]

        # ==================================
        # WEATHER API
        # ==================================

        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
        )

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,

            "daily": (
                "temperature_2m_max,"
                "temperature_2m_min,"
                "weather_code"
            ),

            "forecast_days": max(
                days + 1,
                1
            ),

            "timezone": "auto"
        }

        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=HTTP_TIMEOUT
        )

        weather_response.raise_for_status()

        weather_data = weather_response.json()

        daily = weather_data.get("daily")

        if not daily:
            return {
                "success": False,
                "error": (
                    "Sorry, I could not get "
                    "the weather forecast."
                )
            }

        dates = daily.get("time", [])

        max_temps = daily.get(
            "temperature_2m_max",
            []
        )

        min_temps = daily.get(
            "temperature_2m_min",
            []
        )

        weather_codes = daily.get(
            "weather_code",
            []
        )

        # ==================================
        # VALIDATE REQUESTED DAY
        # ==================================

        if days >= len(dates):
            return {
                "success": False,
                "error": (
                    "Sorry, the forecast for "
                    "that day is not available."
                )
            }

        # ==================================
        # EXTRACT FORECAST
        # ==================================

        date = dates[days]

        max_temp = max_temps[days]

        min_temp = min_temps[days]

        weather_code = weather_codes[days]

        description = weather_description(
            weather_code
        )

        # ==================================
        # RETURN STRUCTURED DATA
        # ==================================

        return {
            "success": True,
            "city": city_name,
            "date": date,
            "days": days,
            "description": description,
            "high": max_temp,
            "low": min_temp
        }

    # ======================================
    # REQUEST ERROR
    # ======================================

    except requests.RequestException as e:

        print(
            "Weather Request Error:",
            e
        )

        return {
            "success": False,
            "error": (
                "Sorry, I could not connect "
                "to the weather service."
            )
        }

    # ======================================
    # GENERAL ERROR
    # ======================================

    except Exception as e:

        print(
            "Weather Error:",
            e
        )

        return {
            "success": False,
            "error": (
                "Sorry, something went wrong "
                "while getting the weather."
            )
        }


# ==========================================
# WEATHER CODE → DESCRIPTION
# ==========================================

def weather_description(code):

    weather_codes = {

        0: "clear skies",

        1: "mainly clear skies",

        2: "partly cloudy skies",

        3: "overcast skies",

        45: "foggy conditions",

        48: "foggy conditions",

        51: "light drizzle",

        53: "moderate drizzle",

        55: "heavy drizzle",

        56: "light freezing drizzle",

        57: "heavy freezing drizzle",

        61: "light rain",

        63: "moderate rain",

        65: "heavy rain",

        66: "light freezing rain",

        67: "heavy freezing rain",

        71: "light snowfall",

        73: "moderate snowfall",

        75: "heavy snowfall",

        77: "snow grains",

        80: "light rain showers",

        81: "moderate rain showers",

        82: "heavy rain showers",

        85: "light snow showers",

        86: "heavy snow showers",

        95: "a thunderstorm",

        96: "a thunderstorm with light hail",

        99: "a thunderstorm with heavy hail"
    }

    return weather_codes.get(
        code,
        "unknown weather conditions"
    )