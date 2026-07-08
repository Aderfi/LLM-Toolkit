import os
from datetime import datetime, timedelta

from llmtools import config
from llmtools.core import backup_file, resolve_safe_path, tool


@tool
def add_event(title: str, date: str, time: str = "09:00", duration_min: int = 60) -> str:
    """Add an event to the local .ics calendar file.

    Args:
        title: Event title.
        date: Date as YYYY-MM-DD.
        time: Start time HH:MM.
        duration_min: Duration in minutes.
    """
    from icalendar import Calendar, Event
    p = resolve_safe_path(config.CALENDAR_FILE)
    start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    if os.path.exists(p):
        backup_file(p)
        with open(p, "rb") as f:
            cal = Calendar.from_ical(f.read())
    else:
        cal = Calendar()
        cal.add("prodid", "-//llmtools//EN")
        cal.add("version", "2.0")
    ev = Event()
    ev.add("summary", title)
    ev.add("dtstart", start)
    ev.add("dtend", start + timedelta(minutes=duration_min))
    ev.add("uid", f"{start:%Y%m%dT%H%M%S}-{abs(hash(title)) % 10000}@llmtools")
    cal.add_component(ev)
    with open(p, "wb") as f:
        f.write(cal.to_ical())
    return f"Added event '{title}' on {date} {time}."


@tool
def list_events() -> str:
    """List events in the local calendar file."""
    from icalendar import Calendar
    p = resolve_safe_path(config.CALENDAR_FILE)
    if not os.path.exists(p):
        return "No calendar file yet."
    with open(p, "rb") as f:
        cal = Calendar.from_ical(f.read())
    out = []
    for comp in cal.walk("VEVENT"):
        dt = comp.get("dtstart")
        dt = dt.dt if dt else "?"
        out.append(f"{dt}: {comp.get('summary')}")
    return "\n".join(out) if out else "(no events)"


@tool
def add_reminder(text: str, due: str = "") -> str:
    """Add a reminder/todo to the local reminders file.

    Args:
        text: Reminder text.
        due: Optional due date/time.
    """
    p = resolve_safe_path(config.REMINDERS_FILE)
    line = f"- [ ] {text}" + (f" (due: {due})" if due else "")
    if os.path.exists(p):
        backup_file(p)
    with open(p, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return "Reminder added."


@tool
def list_reminders() -> str:
    """List reminders/todos from the local reminders file."""
    p = resolve_safe_path(config.REMINDERS_FILE)
    if not os.path.exists(p):
        return "No reminders yet."
    with open(p, encoding="utf-8") as f:
        return f.read().strip() or "(none)"
