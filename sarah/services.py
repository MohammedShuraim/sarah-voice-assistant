"""Optional third-party lookups: weather and news headlines.

Both features degrade to a spoken explanation when their API key is absent, so
Sarah stays usable with only a Groq key configured.
"""

from __future__ import annotations

import os

import requests

from . import config

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Hyderabad")
NEWS_COUNTRY = os.getenv("NEWS_COUNTRY", "in")

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
NEWS_URL = "https://newsapi.org/v2/top-headlines"


def weather_report(city: str = "") -> str:
    """Describe current conditions for a city."""
    city = (city or DEFAULT_CITY).strip()
    if not config.WEATHER_API_KEY:
        return (
            "Weather needs an OpenWeatherMap key. Add WEATHER_API_KEY to your "
            ".env file to switch it on."
        )

    try:
        response = requests.get(
            WEATHER_URL,
            params={"q": city, "appid": config.WEATHER_API_KEY, "units": "metric"},
            timeout=config.HTTP_TIMEOUT,
        )
    except requests.RequestException:
        return "I could not reach the weather service just now."

    if response.status_code == 404:
        return f"I could not find a city called {city}."
    if response.status_code == 401:
        return "The weather service rejected my API key."
    if response.status_code != 200:
        return "The weather service returned an error."

    data = response.json()
    temperature = round(data["main"]["temp"])
    feels_like = round(data["main"]["feels_like"])
    description = data["weather"][0]["description"]
    return (
        f"It's {temperature} degrees in {data.get('name', city)} with "
        f"{description}, feeling like {feels_like}."
    )


def news_report(limit: int = 5) -> str:
    """Read out the current top headlines."""
    if not config.NEWS_API_KEY:
        return "Headlines need a NewsAPI key. Add NEWS_API_KEY to your .env file to switch it on."

    try:
        response = requests.get(
            NEWS_URL,
            params={"country": NEWS_COUNTRY, "apiKey": config.NEWS_API_KEY, "pageSize": limit},
            timeout=config.HTTP_TIMEOUT,
        )
    except requests.RequestException:
        return "I could not reach the news service just now."

    if response.status_code != 200:
        return "The news service returned an error."

    articles = response.json().get("articles", [])[:limit]
    if not articles:
        return "I could not find any headlines right now."

    headlines = [article["title"] for article in articles if article.get("title")]
    return "Here are the top headlines. " + " ... ".join(headlines)
