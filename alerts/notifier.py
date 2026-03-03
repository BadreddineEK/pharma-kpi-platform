"""Notification dispatchers — Slack and email."""

import logging
import smtplib
import os
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)


def send_slack_alert(alert: dict, webhook_url: str) -> bool:
    """Send a Slack notification for a KPI breach."""
    operator_label = "below" if alert.get("operator") == "lt" else "above"
    message = (
        f"🚨 *KPI Alert* — `{alert['metric']}` is {operator_label} threshold\n"
        f"> Site: *{alert['site']}* | Value: `{alert['value']}` | Threshold: `{alert['threshold']}`\n"
        f"> Date: {alert['date']}"
    )
    try:
        response = httpx.post(webhook_url, json={"text": message}, timeout=5)
        response.raise_for_status()
        logger.info(f"Slack alert sent for {alert['metric']} @ {alert['site']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False


def send_email_alert(alert: dict) -> bool:
    """Send an email notification for a KPI breach."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_to = os.getenv("ALERT_EMAIL_TO")

    if not all([smtp_user, smtp_password, email_to]):
        logger.warning("Email config incomplete, skipping email alert")
        return False

    subject = f"[KPI Alert] {alert['metric']} breach at {alert['site']}"
    body = f"Metric: {alert['metric']}\nSite: {alert['site']}\nValue: {alert['value']}\nThreshold: {alert['threshold']}\nDate: {alert['date']}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = email_to

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Email alert sent for {alert['metric']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
