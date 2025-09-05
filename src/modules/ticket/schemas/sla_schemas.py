from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator
from pydantic_core import PydanticCustomError

from .priority_schemas import PriorityOut


class CreateSLASchema(BaseModel):
    """
    Schema to validate the payload when creating the sla
    """

    name: str
    response_time: int
    resolution_time: int
    priority_id: int

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def check_time_negative(self):
        """
        Ensures the sla response and resolution time couldn't be negative
        Raises:
            PydanticCustomError if the provided number is negative
        """
        if self.response_time is not None and self.response_time <= 0:
            raise PydanticCustomError(
                "Cannot be negative",
                "Response time cannot be negative",
            )
        if self.resolution_time is not None and self.resolution_time <= 0:
            raise PydanticCustomError(
                "Cannot be negative",
                "Resolution time cannot be negative",
            )
        return self


class SLAOut(CreateSLASchema):
    """
    Schema to structure sla details when sending outside the application
    """

    id: int
    issued_by: int
    created_at: datetime
    priority: PriorityOut


class EditTicketSLASchema(BaseModel):
    """
    Schema to validate the payload when editing the ticket sla
    """

    name: Optional[str] = None
    response_time: Optional[int] = None
    resolution_time: Optional[int] = None
    priority_id: Optional[int] = None

    @model_validator(mode="after")
    def check_time_negative(self):
        """
        Ensures the sla response and resolution time couldn't be negative
        Raises:
            PydanticCustomError if the provided number is negative
        """

        if self.response_time is not None and self.response_time <= 0:
            raise PydanticCustomError(
                "Cannot be negative",
                "Response time cannot be negative",
            )
        if self.resolution_time is not None and self.resolution_time <= 0:
            raise PydanticCustomError(
                "Cannot be negative",
                "Resolution time cannot be negative",
            )
        return self
