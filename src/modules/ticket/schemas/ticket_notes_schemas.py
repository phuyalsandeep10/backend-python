from pydantic import BaseModel

from src.modules.auth.schema import UserOutSchema


class CreateTicketNotesSchema(BaseModel):
    """
    Schema to validate the payload to create ticket notes
    """

    notes: str


class TicketNotesOut(BaseModel):
    """
    Schema to structure the ticket notes when going outside the application
    """

    updated_at: str
    id: int
    created_at: str
    created_by: UserOutSchema
    content: str
