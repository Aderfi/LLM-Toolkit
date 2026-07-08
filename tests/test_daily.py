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


def test_current_time_offline():
    out = daily.get_current_time("Europe/Madrid")
    assert "Europe/Madrid" in out and ":" in out


def test_current_time_bad_zone():
    out = daily.get_current_time("Not/AZone")
    assert "Unknown timezone" in out


def test_current_time_system_default():
    out = daily.get_current_time()
    assert "Time" in out and ":" in out
