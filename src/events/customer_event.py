from src.utils.common import do_async_task
from src.models import Customer,CustomerVisitLogs
from sqlalchemy import event



async def update_customer_last_log(log:CustomerVisitLogs):
    await Customer.update(log.customer_id, attributes={"log":log.to_json()})

@event.listens_for(CustomerVisitLogs, "after_insert")
def after_insert_message(mapper, connection, target):
    do_async_task(update_customer_last_log, target)

@event.listens_for(CustomerVisitLogs, "after_update")
def after_update_message(mapper, connection, target):
    if target.left_at:
        do_async_task(update_customer_last_log, target)