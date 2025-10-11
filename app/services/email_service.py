"""Email Service for sending notifications and alerts.

This service provides email functionality using SMTP with support for:
- HTML templates
- Attachments
- Async sending
- Multiple recipients
- Email queuing
"""

import logging
from datetime import UTC, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with templates and attachments."""

    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", self.smtp_user)
        self.from_name = getattr(settings, "FROM_NAME", "MagFlow ERP")

        # Setup Jinja2 for email templates
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        template_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        self._enabled = bool(self.smtp_user and self.smtp_password)
        if not self._enabled:
            logger.warning("Email service disabled: SMTP credentials not configured")

    async def send_email(
        self,
        to_email: str | list[str],
        subject: str,
        body_html: str,
        body_text: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email(s)
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, will be generated from HTML if not provided)
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of attachments with 'filename' and 'content' keys

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self._enabled:
            logger.warning(f"Email service disabled, skipping email to {to_email}")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"

            # Handle recipients
            if isinstance(to_email, str):
                to_email = [to_email]
            message["To"] = ", ".join(to_email)

            if cc:
                message["Cc"] = ", ".join(cc)

            # Add text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, "plain", "utf-8")
                message.attach(part1)

            part2 = MIMEText(body_html, "html", "utf-8")
            message.attach(part2)

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}",
                    )
                    message.attach(part)

            # Send email
            all_recipients = to_email + (cc or []) + (bcc or [])

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
                recipients=all_recipients,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False

    async def send_template_email(
        self,
        to_email: str | list[str],
        subject: str,
        template_name: str,
        context: dict[str, Any],
        **kwargs,
    ) -> bool:
        """Send an email using a Jinja2 template.

        Args:
            to_email: Recipient email(s)
            subject: Email subject
            template_name: Name of the template file (without .html extension)
            context: Template context variables
            **kwargs: Additional arguments passed to send_email()

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Render template
            template = self.jinja_env.get_template(f"{template_name}.html")
            body_html = template.render(**context)

            # Send email
            return await self.send_email(
                to_email=to_email, subject=subject, body_html=body_html, **kwargs
            )

        except Exception as e:
            logger.error(f"Failed to send template email: {e}", exc_info=True)
            return False

    async def send_notification_email(
        self,
        to_email: str | list[str],
        notification_type: str,
        title: str,
        message: str,
        priority: str = "medium",
        action_url: str | None = None,
        action_text: str | None = None,
    ) -> bool:
        """Send a notification email.

        Args:
            to_email: Recipient email(s)
            notification_type: Type of notification (system, emag, orders, etc.)
            title: Notification title
            message: Notification message
            priority: Priority level (low, medium, high, critical)
            action_url: Optional URL for action button
            action_text: Optional text for action button

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        context = {
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "priority": priority,
            "action_url": action_url,
            "action_text": action_text or "View Details",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "app_name": "MagFlow ERP",
            "app_url": getattr(settings, "APP_URL", "http://localhost:8000"),
        }

        # Set priority-based subject prefix
        priority_prefix = {
            "critical": "🚨 URGENT",
            "high": "⚠️ Important",
            "medium": "📢",
            "low": "ℹ️",
        }.get(priority, "📢")

        subject = f"{priority_prefix} {title}"

        return await self.send_template_email(
            to_email=to_email,
            subject=subject,
            template_name="notification",
            context=context,
        )

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        verification_url: str | None = None,
    ) -> bool:
        """Send welcome email to new user.

        Args:
            to_email: User's email
            user_name: User's name
            verification_url: Optional email verification URL

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        context = {
            "user_name": user_name,
            "verification_url": verification_url,
            "app_name": "MagFlow ERP",
            "app_url": getattr(settings, "APP_URL", "http://localhost:8000"),
        }

        return await self.send_template_email(
            to_email=to_email,
            subject="Welcome to MagFlow ERP! 🎉",
            template_name="welcome",
            context=context,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
        expires_in_hours: int = 24,
    ) -> bool:
        """Send password reset email.

        Args:
            to_email: User's email
            user_name: User's name
            reset_url: Password reset URL
            expires_in_hours: Hours until reset link expires

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        context = {
            "user_name": user_name,
            "reset_url": reset_url,
            "expires_in_hours": expires_in_hours,
            "app_name": "MagFlow ERP",
        }

        return await self.send_template_email(
            to_email=to_email,
            subject="Password Reset Request - MagFlow ERP",
            template_name="password_reset",
            context=context,
        )

    async def send_order_confirmation_email(
        self,
        to_email: str,
        order_number: str,
        order_details: dict[str, Any],
    ) -> bool:
        """Send order confirmation email.

        Args:
            to_email: Customer's email
            order_number: Order number
            order_details: Order details dictionary

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        context = {
            "order_number": order_number,
            "order_details": order_details,
            "app_name": "MagFlow ERP",
        }

        return await self.send_template_email(
            to_email=to_email,
            subject=f"Order Confirmation - {order_number}",
            template_name="order_confirmation",
            context=context,
        )


# Global email service instance
email_service = EmailService()
