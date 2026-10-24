"""Email sending. ALL mail goes to DEMO_SUPPLIER_INBOX (never to real suppliers).

Transport is chosen from env:
  RESEND_API_KEY (+ RFQ_FROM_EMAIL)            -> Resend HTTP API
  SMTP_HOST + SMTP_USER + SMTP_PASS (+SMTP_PORT, default 587) -> SMTP (e.g. Gmail app password)
Nothing configured, or DEMO_SUPPLIER_INBOX unset -> status "draft" (copy-ready text, nothing sent).
"""
import json
import os
import smtplib
import time
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable

Transport = Callable[[EmailMessage], None]


@dataclass
class SendResult:
    status: str  # "done" | "draft" | "failed"
    detail: str


def _resend_transport(api_key: str) -> Transport:
    def send(msg: EmailMessage) -> None:
        payload = {"from": msg["From"], "to": [msg["To"]], "subject": msg["Subject"],
                   "text": msg.get_content()}
        req = urllib.request.Request(
            "https://api.resend.com/emails", data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                     "User-Agent": "supplyshock/0.1"})  # Resend's CDN rejects the default urllib agent
        urllib.request.urlopen(req, timeout=15).read()
    return send


def _smtp_transport(host: str, port: int, user: str, password: str) -> Transport:
    def send(msg: EmailMessage) -> None:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
    return send


def default_transport() -> Transport | None:
    if os.getenv("RESEND_API_KEY"):
        return _resend_transport(os.environ["RESEND_API_KEY"])
    if os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"):
        return _smtp_transport(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")),
                               os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
    return None


def sender_address() -> str:
    return os.getenv("RFQ_FROM_EMAIL") or os.getenv("SMTP_USER") or "onboarding@resend.dev"


def send(subject: str, body: str, intended_to: str | None, intended_name: str,
         transport: Transport | None = None, retries: int = 1, backoff_s: float = 1.0) -> SendResult:
    inbox = os.getenv("DEMO_SUPPLIER_INBOX", "").strip()
    transport = transport or default_transport()
    if not inbox:
        return SendResult("draft", "DEMO_SUPPLIER_INBOX is not set, so nothing was sent")
    if transport is None:
        return SendResult("draft", "no email transport configured (set RESEND_API_KEY or SMTP_*), nothing sent")
    msg = EmailMessage()
    msg["From"], msg["To"] = sender_address(), inbox
    msg["Subject"] = f"[DEMO -> {intended_name}] {subject}"
    msg.set_content(f"[DEMO MODE] Redirected here. Real recipient would be: "
                    f"{intended_name} <{intended_to or 'unknown'}>\n\n{body}")
    last = None
    for attempt in range(retries + 1):
        try:
            transport(msg)
            time.sleep(float(os.getenv("EMAIL_GAP_S", "0.6")))  # stay under Resend free-tier 2 requests/second
            return SendResult("done", f"sent to {inbox} (demo inbox) for {intended_name}")
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < retries:
                time.sleep(backoff_s)
    return SendResult("failed", f"email failed after {retries + 1} attempts: {last!r}")
