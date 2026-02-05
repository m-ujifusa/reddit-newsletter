"""Email delivery (deferred — stub for future implementation)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from newsletter.config import get_settings

logger = logging.getLogger(__name__)


def send_newsletter_email(
    subject: str, html_content: str, recipients: List[str]
) -> None:
    settings = get_settings()

    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email delivery")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, recipients, msg.as_string())

    logger.info(f"Email sent to {len(recipients)} recipients")
