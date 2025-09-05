from pydantic import BaseModel, EmailStr
from pydantic.functional_validators import field_validator
from pydantic_core import PydanticCustomError


class CreateTicketMessageSchema(BaseModel):
    """
    Schema to validate the payload while creating ticket message
    """

    ticket_id: int
    receiver: EmailStr
    content: str

    @field_validator("content")
    def content_cannot_be_empty_string(cls, value):
        """
        Ensures the content cannot be empty string
        Raises:
            PydanticCustomError if the provided content is empty
        """
        if value.strip() == "":
            raise PydanticCustomError(
                "invalid content",
                "Content cannot be empty string",
            )
        return value


class EditTicketMessageSchema(BaseModel):
    """
    Schemas to validate the payload while editing ticket message schema
    """

    content: str

    @field_validator("content")
    def content_cannot_be_empty_string(cls, value):
        """
        Ensures the content cannot be empty string
        Raises:
            PydanticCustomError if the provided content is empty
        """
        if value.strip() == "":
            raise PydanticCustomError(
                "invalid content",
                "Content cannot be empty string",
            )
        return value


class TicketMessageOutSchema(BaseModel):
    """
    Schemas to structure the ticket message data when going outside the application
    """

    id: int
    receiver: EmailStr
    sender: EmailStr
    content: str
    direction: str
    created_at: str
