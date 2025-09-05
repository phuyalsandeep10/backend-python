from typing import Optional

from pydantic import BaseModel


class CreatePrioriySchema(BaseModel):
    """
    Schema to validate the payload while creating ticket priority
    """

    name: str
    level: int
    bg_color: str
    fg_color: str

    model_config = {"extra": "forbid"}


class EditTicketPrioritySchema(BaseModel):
    """
    Schema to validate the payload while editing ticket priority
    """

    name: Optional[str] = None
    level: Optional[int] = None
    fg_color: Optional[str] = None
    bg_color: Optional[str] = None


class PriorityOut(CreatePrioriySchema):
    """
    Schema to validate the priority data being sent outside the application
    """

    id: int
