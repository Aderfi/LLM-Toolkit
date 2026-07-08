import smtplib
import ssl
from email.message import EmailMessage

from llmtools import config
from llmtools.core import tool


def _creds_ok():
    return bool(config.EMAIL_ADDRESS and config.EMAIL_PASSWORD)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email via SMTP (STARTTLS).

    Args:
        to: Recipient address.
        subject: Subject line.
        body: Plain-text body.
    """
    if not _creds_ok():
        return "Error: set EMAIL_ADDRESS and EMAIL_PASSWORD."
    msg = EmailMessage()
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls(context=ctx)
        s.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        s.send_message(msg)
    return f"Sent email to {to}."


@tool
def read_emails(count: int = 5, folder: str = "INBOX", unread_only: bool = False) -> str:
    """Read recent emails via IMAP (subject, sender, date, snippet).

    Args:
        count: How many recent emails to show.
        folder: Mailbox folder, e.g. 'INBOX'.
        unread_only: Only unread messages.
    """
    if not _creds_ok():
        return "Error: set EMAIL_ADDRESS and EMAIL_PASSWORD."
    from imap_tools import AND, MailBox
    criteria = AND(seen=False) if unread_only else AND(all=True)
    out = []
    with MailBox(config.IMAP_HOST).login(
            config.EMAIL_ADDRESS, config.EMAIL_PASSWORD, initial_folder=folder) as mb:
        for msg in mb.fetch(criteria, limit=count, reverse=True, mark_seen=False):
            snippet = (msg.text or msg.html or "").strip().replace("\n", " ")[:200]
            out.append(f"From: {msg.from_}\nDate: {msg.date_str}\n"
                       f"Subject: {msg.subject}\n{snippet}")
    return "\n\n".join(out) if out else "No emails."
