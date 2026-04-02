# tasks/email_tasks.py
from .celery_app import celery_app
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation(self, buyer_id: int, order_id: int, total: float):
    try:
        logger.info("sending_order_confirmation", order_id=order_id, buyer_id=buyer_id)
        # Your email provider (SendGrid, SES, etc.) goes here
        # email_client.send(to=buyer_email, template="order_confirmation", data={...})
        logger.info("order_confirmation_sent", order_id=order_id)
        return {"status": "sent", "order_id": order_id}
    except Exception as exc:
        logger.error("order_confirmation_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_vendor_webhook(self, vendor_id: int, order_id: int, items: list):
    """Notify the vendor that one of their products was ordered."""
    try:
        logger.info(
            "dispatching_vendor_webhook", vendor_id=vendor_id, order_id=order_id
        )
        # webhook_service.dispatch(vendor_webhook_url, "order.created", {...})
        return {"status": "dispatched"}
    except Exception as exc:
        raise self.retry(exc=exc)
