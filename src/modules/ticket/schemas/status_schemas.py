from typing import Optional

from pydantic import BaseModel

from ..enums import TicketStatusEnum


class CreateTicketStatusSchema(BaseModel):
    """
    Schema to validate the payload while creating ticket status
    """

    name: str
    bg_color: str
    fg_color: str
    status_category: TicketStatusEnum
    model_config = {"extra": "forbid"}


class EditTicketStatusSchema(BaseModel):
    """
    Schema to validate the payload while editing ticket status
    """

    name: Optional[str] = None
    fg_color: Optional[str] = None
    bg_color: Optional[str] = None
    status_category: Optional[TicketStatusEnum] = None


class TicketStatusOut(CreateTicketStatusSchema):
    """
    Schema to validate the ticket status data when sending outside the application
    """

    id: int


class TicketByStatusSchema(BaseModel):
    """
    Schema to get ticcket by status
    """

    status_id: int

    model_config = {"extra": "forbid"}
