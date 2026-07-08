from llmtools import daily


def test_weather_formats(monkeypatch):
    seq = [
        {"results": [{"latitude": 1, "longitude": 2, "country": "X"}]},
        {
            "current": {"temperature_2m": 20, "wind_speed_10m": 5},
            "current_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"},
        },
    ]
    monkeypatch.setattr(daily, "_get_json", lambda url: seq.pop(0))
    out = daily.get_current_weather("Madrid")
    assert "20" in out and "Madrid" in out
