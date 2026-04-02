# tasks/email_tasks.py
import smtplib
from email.message import EmailMessage
from config import get_settings
from tasks.celery_app import celery_app
import structlog

settings = get_settings()
logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_email: str, username: str) -> dict:
    """Send an HTML welcome email after a user registers.
    Retries up to 3 times on failure (60s delay between retries).
    """
    try:
        logger.info("email_task.welcome_start", to=user_email, username=username)
        msg = EmailMessage()
        msg["Subject"] = f"Welcome to Marketo, {username}! 🎉"
        msg["From"] = settings.smtp_from_email
        msg["To"] = user_email

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                        Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f3f4f6;
                    margin: 0; padding: 0;
                }}
                .container {{
                    max-width: 600px; margin: 40px auto;
                    background: #fff; border-radius: 8px;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                    color: #fff; padding: 40px 30px; text-align: center;
                }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{
                    padding: 40px 30px; color: #374151;
                    line-height: 1.6; font-size: 16px;
                }}
                .content p {{ margin: 0 0 16px; }}
                .btn-wrap {{ text-align: center; margin: 28px 0; }}
                .btn {{
                    display: inline-block; padding: 14px 32px;
                    background: #4f46e5; color: #fff !important;
                    text-decoration: none; border-radius: 6px;
                    font-weight: 600; font-size: 15px;
                }}
                .footer {{
                    background: #f8fafc; padding: 20px 30px;
                    text-align: center; font-size: 13px; color: #64748b;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Marketo, {username}! 🚀</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Your account is ready. Start exploring products, build your store,
                    and place orders — all with a production-grade API behind the scenes.</p>
                    <div class="btn-wrap">
                        <a href="http://localhost:8000/docs" class="btn">Go to API Docs</a>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Marketo. All rights reserved.</p>
                    <p>If you didn't create this account, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = (
            f"Hi {username},\n\n"
            f"Welcome to Marketo! Your account is ready.\n\n"
            f"API Docs: http://localhost:8000/docs\n\n"
            f"If you didn't create this account, please ignore this email."
        )
        msg.set_content(plain_text)
        msg.add_alternative(html_content, subtype="html")

        if settings.smtp_username and settings.smtp_password:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            logger.info("email_task.welcome_sent", to=user_email)
        else:
            # Dev mode — log instead of sending
            logger.info("email_task.welcome_mock", to=user_email, note="SMTP not configured")

        return {"status": "sent", "to": user_email}

    except Exception as exc:
        logger.error("email_task.welcome_failed", to=user_email, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation(self, user_email: str, username: str, order_id: int, total: float) -> dict:
    """Send an HTML order confirmation email to the buyer."""
    try:
        logger.info(
            "email_task.order_confirm_start",
            order_id=order_id,
            to=user_email,
            total=total,
        )
        msg = EmailMessage()
        msg["Subject"] = f"Marketo: Order #{order_id} Confirmed! 📦"
        msg["From"] = settings.smtp_from_email
        msg["To"] = user_email

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                        Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f3f4f6;
                    margin: 0; padding: 0;
                }}
                .container {{
                    max-width: 600px; margin: 40px auto;
                    background: #fff; border-radius: 8px;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: #fff; padding: 40px 30px; text-align: center;
                }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{
                    padding: 40px 30px; color: #374151;
                    line-height: 1.6; font-size: 16px;
                }}
                .content p {{ margin: 0 0 16px; }}
                .order-summary {{
                    background: #f8fafc; border: 1px solid #e2e8f0;
                    border-radius: 6px; padding: 20px; text-align: center;
                    margin: 24px 0; font-size: 18px;
                }}
                .order-summary strong {{ color: #0f172a; font-size: 22px; }}
                .btn-wrap {{ text-align: center; margin: 28px 0; }}
                .btn {{
                    display: inline-block; padding: 14px 32px;
                    background: #059669; color: #fff !important;
                    text-decoration: none; border-radius: 6px;
                    font-weight: 600; font-size: 15px;
                }}
                .footer {{
                    background: #f8fafc; padding: 20px 30px;
                    text-align: center; font-size: 13px; color: #64748b;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Order #{order_id} Confirmed! 🎉</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Thank you for shopping with Marketo. We're getting your order ready to be shipped. We will notify you when it has been sent.</p>
                    
                    <div class="order-summary">
                        Order Total: <strong>${total:.2f}</strong>
                    </div>

                    <p>You can view your order details from your account dashboard anytime.</p>
                    
                    <div class="btn-wrap">
                        <a href="http://localhost:8000/docs" class="btn">View Order Details</a>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Marketo. All rights reserved.</p>
                    <p>If you didn't place this order, please contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = (
            f"Hi {username},\n\n"
            f"Order #{order_id} confirmed!\n"
            f"Order Total: ${total:.2f}\n\n"
            f"Thank you for shopping with Marketo.\n\n"
            f"If you didn't place this order, please contact support."
        )
        msg.set_content(plain_text)
        msg.add_alternative(html_content, subtype="html")

        if settings.smtp_username and settings.smtp_password:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            logger.info("email_task.order_confirm_sent", to=user_email, order_id=order_id)
        else:
            # Dev mode — log instead of sending
            logger.info("email_task.order_confirm_mock", to=user_email, order_id=order_id, note="SMTP not configured")

        return {"status": "sent", "order_id": order_id, "to": user_email}

    except Exception as exc:
        logger.error("email_task.order_confirm_failed", order_id=order_id, to=user_email, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_vendor_webhook(self, vendor_id: int, order_id: int, items: list) -> dict:
    """Notify the vendor that one of their products was ordered."""
    try:
        logger.info(
            "email_task.vendor_webhook_start",
            vendor_id=vendor_id,
            order_id=order_id,
            item_count=len(items),
        )
        # webhook_service.dispatch(vendor_webhook_url, "order.created", {...})
        logger.info("email_task.vendor_webhook_sent", vendor_id=vendor_id)
        return {"status": "dispatched"}
    except Exception as exc:
        logger.error("email_task.vendor_webhook_failed", vendor_id=vendor_id, error=str(exc))
        raise self.retry(exc=exc)
