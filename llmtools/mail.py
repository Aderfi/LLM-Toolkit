import email
import imaplib
import smtplib
import ssl
from email.header import decode_header
from email.message import EmailMessage

from llmtools import config
from llmtools.core import tool


def _creds_ok():
    return bool(config.EMAIL_ADDRESS and config.EMAIL_PASSWORD)


def _decode(value):
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


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
    """Read recent email headers via IMAP.

    Args:
        count: How many recent emails to show.
        folder: Mailbox folder, e.g. 'INBOX'.
        unread_only: Only unread messages.
    """
    if not _creds_ok():
        return "Error: set EMAIL_ADDRESS and EMAIL_PASSWORD."
    M = imaplib.IMAP4_SSL(config.IMAP_HOST)
    try:
        M.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        M.select(folder)
        _, data = M.search(None, "UNSEEN" if unread_only else "ALL")
        ids = data[0].split()[-count:]
        out = []
        for i in reversed(ids):
            _, msg_data = M.fetch(i, "(RFC822)")
            m = email.message_from_bytes(msg_data[0][1])
            out.append(
                f"From: {_decode(m.get('From'))}\n"
                f"Date: {m.get('Date', '')}\n"
                f"Subject: {_decode(m.get('Subject'))}"
            )
        return "\n\n".join(out) if out else "No emails."
    finally:
        try:
            M.logout()
        except Exception:
            pass
