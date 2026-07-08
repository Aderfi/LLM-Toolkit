import json
import urllib.parse
import urllib.request

from llmtools import config
from llmtools.core import tool


def _get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Gemma4Tools/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


@tool
def get_current_weather(city: str, unit: str = "celsius") -> str:
    """Get current weather for a city.

    Args:
        city: City name.
        unit: 'celsius' or 'fahrenheit'.
    """
    geo = _get_json(
        f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
    )
    if not geo.get("results"):
        return f"Could not find city: {city}."
    loc = geo["results"][0]
    tu = "fahrenheit" if unit.lower() == "fahrenheit" else "celsius"
    w = _get_json(
        f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}"
        f"&longitude={loc['longitude']}&current=temperature_2m,wind_speed_10m"
        f"&temperature_unit={tu}"
    )
    c = w["current"]
    return (
        f"Weather in {city.title()} ({loc.get('country', '')}): "
        f"{c['temperature_2m']}{w['current_units']['temperature_2m']}, "
        f"wind {c['wind_speed_10m']}{w['current_units']['wind_speed_10m']}."
    )


@tool
def get_current_news(topic: str = "") -> str:
    """Fetch latest news headlines, optionally by topic.

    Args:
        topic: Optional search topic.
    """
    key = config.NEWS_API_KEY
    if key in ("YOUR_NEWS_API_KEY", "YOUR_API_KEY", ""):
        return "Error: set NEWS_API_KEY env var or config value."
    if topic.strip():
        url = (
            f"https://newsapi.org/v2/everything?q={urllib.parse.quote(topic)}"
            f"&sortBy=publishedAt&pageSize=5&apiKey={key}"
        )
    else:
        url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=5&apiKey={key}"
    data = _get_json(url)
    if data.get("status") != "ok":
        return f"Error: {data.get('message', 'unknown')}"
    arts = data.get("articles", [])
    if not arts:
        return "No articles found."
    return "\n".join(
        f"{i}. {a.get('title', '')} ({a.get('source', {}).get('name', '')})"
        for i, a in enumerate(arts, 1)
    )


@tool
def get_current_time(timezone: str) -> str:
    """Get current time for a timezone.

    Args:
        timezone: e.g. 'Europe/Madrid'.
    """
    d = _get_json(
        f"https://timeapi.io/api/Time/current/zone?timeZone={urllib.parse.quote(timezone)}"
    )
    if d.get("time") and d.get("date"):
        return f"Time in {timezone}: {d['time']} on {d['date']}."
    return f"Could not fetch time for {timezone}."


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between currencies.

    Args:
        amount: Amount to convert.
        from_currency: 3-letter source code.
        to_currency: 3-letter target code.
    """
    fc, tc = from_currency.upper(), to_currency.upper()
    data = _get_json(f"https://api.exchangerate-api.com/v4/latest/{fc}")
    rates = data.get("rates", {})
    if tc not in rates:
        return f"Error: unsupported currency '{tc}'."
    return f"{amount} {fc} = {float(amount) * rates[tc]:.2f} {tc} (rate {rates[tc]})."
