import os
from datetime import datetime, timedelta

from llmtools import config
from llmtools.core import backup_file, resolve_safe_path, tool

_HEADER = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//llmtools//EN\n"
_FOOTER = "END:VCALENDAR\n"


@tool
def add_event(title: str, date: str, time: str = "09:00", duration_min: int = 60) -> str:
    """Add an event to the local .ics calendar file.

    Args:
        title: Event title.
        date: Date as YYYY-MM-DD.
        time: Start time HH:MM.
        duration_min: Duration in minutes.
    """
    p = resolve_safe_path(config.CALENDAR_FILE)
    start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=duration_min)
    uid = f"{start:%Y%m%dT%H%M%S}-{abs(hash(title)) % 10000}@llmtools"
    vevent = (
        f"BEGIN:VEVENT\nUID:{uid}\nDTSTART:{start:%Y%m%dT%H%M%S}\n"
        f"DTEND:{end:%Y%m%dT%H%M%S}\nSUMMARY:{title}\nEND:VEVENT\n"
    )
    if os.path.exists(p):
        backup_file(p)
        with open(p, encoding="utf-8") as f:
            body = f.read().replace(_FOOTER, "")
    else:
        body = _HEADER
    with open(p, "w", encoding="utf-8") as f:
        f.write(body + vevent + _FOOTER)
    return f"Added event '{title}' on {date} {time}."


@tool
def list_events() -> str:
    """List events in the local calendar file."""
    p = resolve_safe_path(config.CALENDAR_FILE)
    if not os.path.exists(p):
        return "No calendar file yet."
    out, dt = [], ""
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DTSTART:"):
                dt = line[8:]
            elif line.startswith("SUMMARY:"):
                out.append(f"{dt}: {line[8:]}")
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
