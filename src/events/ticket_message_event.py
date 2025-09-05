import asyncio
import logging

from sqlalchemy import event

from src.models import TicketMessage
from src.tasks.ticket_task import broadcast_ticket_message

logger = logging.getLogger(__name__)


def do_async_task(func, *args, **kwargs):
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(func(*args, **kwargs))
    except Exception as e:
        print(f"Error updating conversation last message: {e}")


def broadcast_messages(target):
    try:
        broadcast_ticket_message.send(
            user_email=target.sender,
            message=target.content,
            ticket_id=target.ticket_id,
        )
        logger.info("Enqueued async broadcast job for TicketMessage")
    except Exception as e:
        logger.exception(f"Failed to enqueue broadcast job for TicketMessage {e}")


# Example: log when a ticket message is created
@event.listens_for(TicketMessage, "after_insert")
def after_insert_message(mapper, connection, target):
    broadcast_messages(target)
