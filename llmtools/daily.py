import json
import urllib.parse
import urllib.request

from .core import tool


def _get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Gemma4Tools/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
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
    from google_news_api import GoogleNewsClient
    from google_news_api.exceptions import HTTPError, ParsingError, RateLimitError, ValidationError

    try:
        with GoogleNewsClient(language="es", country="ES") as client:
            if topic.strip():
                articles = client.search(topic, when="24h", max_results=5)
            else:
                articles = client.top_news(topic="NATION", max_results=5)
    except (HTTPError, RateLimitError, ParsingError, ValidationError) as e:
        return f"Error fetching news: {e}"

    if not articles:
        return "No articles found."

    return "\n".join(
        f"{i}. {a['title']} ({a['source']}, {a['published']})"
        for i, a in enumerate(articles, 1)
    )


@tool
def get_current_time(timezone: str = "") -> str:
    """Get the current time for a timezone (offline). Empty = the system's own timezone.

    Args:
        timezone: IANA timezone name, e.g. 'Europe/Madrid'. Leave empty to use the OS timezone.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    if not timezone:
        try:  # resolve the OS timezone to an IANA name
            from tzlocal import get_localzone_name
            timezone = get_localzone_name() or ""
        except Exception:
            timezone = ""
        if not timezone:  # fall back to the local offset without a name
            now = datetime.now().astimezone()
            return f"Time (system local): {now:%H:%M:%S} on {now:%Y-%m-%d} ({now:%Z%z})."
    try:
        now = datetime.now(ZoneInfo(timezone))
    except (ZoneInfoNotFoundError, ValueError):
        return f"Unknown timezone: '{timezone}'. Use an IANA name like 'Europe/Madrid'."
    return f"Time in {timezone}: {now:%H:%M:%S} on {now:%Y-%m-%d} ({now:%Z%z})."


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
