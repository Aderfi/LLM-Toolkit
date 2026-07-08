import os

from llmtools import calendar_tools, config, knowledge, media, system, utils


def _roots(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])


# --- calendar ---
def test_calendar_add_and_list(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "CALENDAR_FILE", str(tmp_path / "cal.ics"))
    calendar_tools.add_event("Dentist", "2026-08-01", "10:30")
    out = calendar_tools.list_events()
    assert "Dentist" in out and "2026-08-01 10:30" in out


def test_reminders(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "REMINDERS_FILE", str(tmp_path / "rem.md"))
    calendar_tools.add_reminder("buy milk", due="today")
    assert "buy milk" in calendar_tools.list_reminders()


# --- knowledge (no heavy deps needed for this path) ---
def test_semantic_search_no_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAG_INDEX_DIR", str(tmp_path / "empty"))
    out = knowledge.semantic_search("anything")
    assert "no index" in out.lower()


# --- media ---
def test_qr_generate(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    out = media.qr_generate("https://example.com", str(tmp_path / "q.png"))
    assert os.path.exists(tmp_path / "q.png") and "QR" in out


# --- system ---
def test_system_info():
    out = system.system_info()
    assert "CPU" in out and "RAM" in out


# --- utils additions ---
def test_generate_password():
    pw = utils.generate_password(20)
    assert len(pw) == 20


def test_convert_units():
    out = utils.convert_units(1, "meter", "centimeter")
    assert "100" in out
