import smtplib
import ssl
from email.message import EmailMessage

from .config import get_settings
from .core import tool


def _creds():
    s = get_settings()
    if not (s.email_address and s.email_password):
        raise ValueError("set EMAIL_ADDRESS and EMAIL_PASSWORD.")
    return s, s.email_address, s.email_password.get_secret_value()


@tool(confirm=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email via SMTP (STARTTLS).

    Args:
        to: Recipient address.
        subject: Subject line.
        body: Plain-text body.
    """
    s, address, password = _creds()
    msg = EmailMessage()
    msg["From"] = address
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
        smtp.starttls(context=ctx)
        smtp.login(address, password)
        smtp.send_message(msg)
    return f"Sent email to {to}."


@tool
def read_emails(count: int = 5, folder: str = "INBOX", unread_only: bool = False) -> str:
    """Read recent emails via IMAP (subject, sender, date, snippet).

    Args:
        count: How many recent emails to show.
        folder: Mailbox folder, e.g. 'INBOX'.
        unread_only: Only unread messages.
    """
    s, address, password = _creds()
    from imap_tools import AND, MailBox
    criteria = AND(seen=False) if unread_only else AND(all=True)
    out = []
    with MailBox(s.imap_host).login(address, password, initial_folder=folder) as mb:
        for msg in mb.fetch(criteria, limit=count, reverse=True, mark_seen=False):
            snippet = (msg.text or msg.html or "").strip().replace("\n", " ")[:200]
            out.append(f"From: {msg.from_}\nDate: {msg.date_str}\n"
                       f"Subject: {msg.subject}\n{snippet}")
    return "\n\n".join(out) if out else "No emails."
