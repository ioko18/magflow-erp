"""Email notification service for MagFlow ERP."""

import asyncio
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import User
from ..services.rbac_service import AuditService

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        """Initialize email service."""
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.SENDER_EMAIL
        self.use_tls = settings.EMAIL_USE_TLS
        self.use_ssl = settings.EMAIL_USE_SSL

    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> MIMEMultipart:
        """Create email message."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = to_email

        # Add text content if provided
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        return message

    def _send_email_sync(self, message: MIMEMultipart) -> bool:
        """Send email synchronously."""
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_server,
                    self.smtp_port,
                    context=context,
                ) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(
                        self.sender_email,
                        message["To"],
                        message.as_string(),
                    )
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(
                        self.sender_email,
                        message["To"],
                        message.as_string(),
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email asynchronously."""
        try:
            message = self._create_message(
                to_email,
                subject,
                html_content,
                text_content,
            )

            # Run SMTP operations in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_email_sync, message)

            if result:
                logger.info(f"Email sent successfully to {to_email}")
            else:
                logger.error(f"Failed to send email to {to_email}")

            return result

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    def render_template(self, template_string: str, **kwargs) -> str:
        """Render Jinja2 template."""
        try:
            template = Template(template_string)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return template_string

    async def send_welcome_email(self, user: User) -> bool:
        """Send welcome email to new user."""
        subject = f"Welcome to {settings.APP_NAME}!"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; background-color: #f9f9f9; }
                .button { background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {{ app_name }}!</h1>
                </div>
                <div class="content">
                    <h2>Hello {{ user_name }}!</h2>
                    <p>Welcome to {{ app_name }}! Your account has been created successfully.</p>

                    <p>Your account details:</p>
                    <ul>
                        <li><strong>Email:</strong> {{ user_email }}</li>
                        <li><strong>Account Type:</strong> {{ account_type }}</li>
                        <li><strong>Registration Date:</strong> {{ registration_date }}</li>
                    </ul>

                    <p>You can now log in to your account and start using all the features available to you.</p>

                    <a href="{{ login_url }}" class="button">Login to Your Account</a>

                    <p>If you have any questions, feel free to contact our support team.</p>

                    <p>Best regards,<br>The {{ app_name }} Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; {{ year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Welcome to {{ app_name }}!

        Hello {{ user_name }}!

        Welcome to {{ app_name }}! Your account has been created successfully.

        Your account details:
        - Email: {{ user_email }}
        - Account Type: {{ account_type }}
        - Registration Date: {{ registration_date }}

        You can now log in to your account at: {{ login_url }}

        If you have any questions, feel free to contact our support team.

        Best regards,
        The {{ app_name }} Team

        This is an automated message. Please do not reply to this email.
        © {{ year }} {{ app_name }}. All rights reserved.
        """

        account_type = "Administrator" if user.is_superuser else "User"

        html_content = self.render_template(
            html_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            user_email=user.email,
            account_type=account_type,
            registration_date=user.created_at.strftime("%Y-%m-%d %H:%M"),
            login_url=(
                f"{settings.FRONTEND_URL}/login"
                if settings.FRONTEND_URL
                else "Login page"
            ),
            year=datetime.now().year,
        )

        text_content = self.render_template(
            text_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            user_email=user.email,
            account_type=account_type,
            registration_date=user.created_at.strftime("%Y-%m-%d %H:%M"),
            login_url=(
                f"{settings.FRONTEND_URL}/login"
                if settings.FRONTEND_URL
                else "Login page"
            ),
            year=datetime.now().year,
        )

        return await self.send_email(user.email, subject, html_content, text_content)

    async def send_password_reset_email(self, user: User, reset_token: str) -> bool:
        """Send password reset email."""
        subject = f"Password Reset - {settings.APP_NAME}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; background-color: #f9f9f9; }
                .button { background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
                .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {{ user_name }}!</h2>

                    <p>You have requested to reset your password for your {{ app_name }} account.</p>

                    <div class="warning">
                        <strong>Security Notice:</strong> This password reset link will expire in 24 hours for your security.
                    </div>

                    <p>To reset your password, click the button below:</p>

                    <a href="{{ reset_url }}" class="button">Reset My Password</a>

                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #007bff;">{{ reset_url }}</p>

                    <p><strong>Important:</strong> If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>

                    <p>If you have any questions, feel free to contact our support team.</p>

                    <p>Best regards,<br>The {{ app_name }} Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; {{ year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Password Reset Request - {{ app_name }}

        Hello {{ user_name }}!

        You have requested to reset your password for your {{ app_name }} account.

        Security Notice: This password reset link will expire in 24 hours for your security.

        To reset your password, click this link: {{ reset_url }}

        If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

        If you have any questions, feel free to contact our support team.

        Best regards,
        The {{ app_name }} Team

        This is an automated message. Please do not reply to this email.
        © {{ year }} {{ app_name }}. All rights reserved.
        """

        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            if settings.FRONTEND_URL
            else f"Reset link: {reset_token}"
        )

        html_content = self.render_template(
            html_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            reset_url=reset_url,
            year=datetime.now().year,
        )

        text_content = self.render_template(
            text_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            reset_url=reset_url,
            year=datetime.now().year,
        )

        return await self.send_email(user.email, subject, html_content, text_content)

    async def send_security_alert(
        self,
        user: User,
        alert_type: str,
        details: Dict[str, Any],
    ) -> bool:
        """Send security alert email."""
        subjects = {
            "login_failed": f"Failed Login Attempt - {settings.APP_NAME}",
            "suspicious_activity": f"Security Alert - {settings.APP_NAME}",
            "password_changed": f"Password Changed - {settings.APP_NAME}",
            "new_device": f"New Device Login - {settings.APP_NAME}",
        }

        subject = subjects.get(alert_type, f"Security Alert - {settings.APP_NAME}")

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #ffc107; color: #212529; padding: 20px; text-align: center; }
                .content { padding: 30px; background-color: #f9f9f9; }
                .alert { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; margin: 20px 0; border-radius: 5px; color: #721c24; }
                .info { background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; margin: 20px 0; border-radius: 5px; color: #0c5460; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Security Alert</h1>
                </div>
                <div class="content">
                    <h2>Hello {{ user_name }}!</h2>

                    <div class="alert">
                        <strong>Security Alert:</strong> {{ alert_type.replace('_', ' ').title() }}
                    </div>

                    <p>We detected some activity on your {{ app_name }} account that requires your attention.</p>

                    <div class="info">
                        <h4>Activity Details:</h4>
                        <ul>
                            {% for key, value in details.items() %}
                            <li><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</li>
                            {% endfor %}
                        </ul>
                    </div>

                    <p><strong>What should you do?</strong></p>
                    <ul>
                        <li>Review the activity details above</li>
                        <li>If this activity was not initiated by you, change your password immediately</li>
                        <li>Contact our security team if you have concerns</li>
                    </ul>

                    <p>This is an automated security notification. Please take appropriate action if needed.</p>

                    <p>Best regards,<br>The {{ app_name }} Security Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated security message. Please do not reply to this email.</p>
                    <p>&copy; {{ year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Security Alert - {{ app_name }}

        Hello {{ user_name }}!

        Security Alert: {{ alert_type.replace('_', ' ').title() }}

        We detected some activity on your {{ app_name }} account that requires your attention.

        Activity Details:
        {% for key, value in details.items() %}
        - {{ key.replace('_', ' ').title() }}: {{ value }}
        {% endfor %}

        What should you do?
        - Review the activity details above
        - If this activity was not initiated by you, change your password immediately
        - Contact our security team if you have concerns

        This is an automated security notification. Please take appropriate action if needed.

        Best regards,
        The {{ app_name }} Security Team

        This is an automated security message. Please do not reply to this email.
        © {{ year }} {{ app_name }}. All rights reserved.
        """

        html_content = self.render_template(
            html_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            alert_type=alert_type,
            details=details,
            year=datetime.now().year,
        )

        text_content = self.render_template(
            text_template,
            app_name=settings.APP_NAME,
            user_name=user.full_name or "User",
            alert_type=alert_type,
            details=details,
            year=datetime.now().year,
        )

        return await self.send_email(user.email, subject, html_content, text_content)

    async def send_notification(
        self,
        db: AsyncSession,
        event_type: str,
        recipients: List[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send notification email based on event type."""
        try:
            success_count = 0
            failed_count = 0

            for recipient_email in recipients:
                # Get user information if needed
                if "user_id" in context:
                    result = await db.execute(
                        select(User).where(User.id == context["user_id"]),
                    )
                    user = result.scalar_one_or_none()
                else:
                    user = None

                # Send appropriate email based on event type
                if event_type == "user_created" and user:
                    success = await self.send_welcome_email(user)
                elif event_type == "password_reset" and user:
                    success = await self.send_password_reset_email(
                        user,
                        context.get("reset_token", ""),
                    )
                elif event_type == "security_alert" and user:
                    success = await self.send_security_alert(
                        user,
                        context.get("alert_type", "general"),
                        context.get("details", {}),
                    )
                else:
                    # Generic notification
                    subject = context.get(
                        "subject",
                        f"Notification - {settings.APP_NAME}",
                    )
                    html_content = context.get(
                        "html_content",
                        "<p>Notification message</p>",
                    )
                    success = await self.send_email(
                        recipient_email,
                        subject,
                        html_content,
                    )

                if success:
                    success_count += 1
                else:
                    failed_count += 1

            return {
                "success": success_count,
                "failed": failed_count,
                "total": len(recipients),
            }

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {
                "success": 0,
                "failed": len(recipients),
                "total": len(recipients),
                "error": str(e),
            }


# Global email service instance
email_service = EmailService()


async def get_email_service() -> EmailService:
    """Get email service instance."""
    return email_service


class NotificationManager:
    """Manager for handling different types of notifications."""

    def __init__(self, db: AsyncSession):
        """Initialize notification manager."""
        self.db = db
        self.email_service = EmailService()
        self.audit_service = AuditService(db)

    async def notify_user_created(self, user: User) -> bool:
        """Notify about new user creation."""
        try:
            success = await self.email_service.send_welcome_email(user)

            # Log the notification
            await self.audit_service.log_action(
                user=None,  # System action
                action="email_notification_sent",
                resource="notifications",
                details={
                    "notification_type": "user_welcome",
                    "recipient": user.email,
                    "success": success,
                },
                success=success,
            )

            return success

        except Exception as e:
            logger.error(f"Error sending user creation notification: {e}")
            return False

    async def notify_security_event(
        self,
        user: User,
        event_type: str,
        details: Dict[str, Any],
    ) -> bool:
        """Notify about security events."""
        try:
            success = await self.email_service.send_security_alert(
                user,
                event_type,
                details,
            )

            # Log the notification
            await self.audit_service.log_action(
                user=None,  # System action
                action="security_notification_sent",
                resource="notifications",
                details={
                    "notification_type": "security_alert",
                    "alert_type": event_type,
                    "recipient": user.email,
                    "success": success,
                },
                success=success,
            )

            return success

        except Exception as e:
            logger.error(f"Error sending security notification: {e}")
            return False

    async def notify_admin_activity(
        self,
        admin_user: User,
        activity: str,
        target: str,
    ) -> bool:
        """Notify admin about important activities."""
        try:
            # This would send notification to admin email
            # Implementation depends on admin email configuration
            return True

        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            return False
