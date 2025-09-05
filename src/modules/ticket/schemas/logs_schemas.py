from typing import Optional

from pydantic import BaseModel

from ..enums import TicketLogActionEnum, TicketLogEntityEnum


class TicketLogSchema(BaseModel):
    """
    Schemas to validate the payload while creating ticket log
    """

    organization_id: Optional[int] = None
    ticket_id: Optional[int] = None
    entity_type: TicketLogEntityEnum
    action: TicketLogActionEnum
    description: Optional[str] = None
    previous_value: Optional[dict] = None
    new_value: Optional[dict] = None
