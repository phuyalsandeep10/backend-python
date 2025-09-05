from typing import List, Optional

from pydantic import BaseModel, EmailStr, model_validator
from pydantic_core import PydanticCustomError

from .sla_schemas import SLAOut


class CreateTicketSchema(BaseModel):
    """
    Schema to validate payload when creating ticket
    """

    title: str
    description: str
    sender_domain: EmailStr
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None
    priority_id: int
    department_id: int
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_location: Optional[str] = None
    assignees: Optional[List[int]] = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def check_customer_anonymousness(self):
        """
        Checks customer anonymousness
        Raises:
            PydanticCustomError if validation fails
        """
        customer_id = self.customer_id
        customer_name = self.customer_name
        customer_email = self.customer_email
        customer_phone = self.customer_phone
        customer_location = self.customer_location

        result = [
            field
            for field in [
                customer_name,
                customer_email,
                customer_phone,
                customer_location,
            ]
        ]

        # ensures either customer_id or [customer_name,customer_email,customer_phone] are provided
        if customer_id is None and any(res is None for res in result):
            raise PydanticCustomError(
                "missing_customer_info",
                "Either provide customer_id or anonymous customer information (name/email/phone/location)",
            )

        # ensures both customer_id or [customer_name,customer_email,customer_phone] are not provided
        if customer_id is not None and not any(res is not None for res in result):
            raise PydanticCustomError(
                "invalid_customer_info",
                "Either send customer id or other customer information but not both",
            )

        # ensures if customer id is not provided all other email ,name, phone numbers are provided
        if customer_id is None and not all(res is not None for res in result):
            raise PydanticCustomError(
                "invalid_customer_info",
                "All customer details should be provided",
            )

        return self


class EditTicketSchema(BaseModel):
    """
    Schema to validate the payload when editing the ticket
    """

    title: Optional[str] = None
    description: Optional[str] = None
    sender_domain: Optional[str] = None
    attachments: Optional[List[str]] = None
    priority_id: Optional[int] = None
    status_id: Optional[int] = None
    department_id: Optional[int] = None
    sla_id: Optional[str] = None
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_location: Optional[str] = None
    assignees: Optional[List[int]] = None
    is_spam: Optional[bool] = None

    model_config = {"extra": "forbid"}


class AssigneeOut(BaseModel):
    """
    Schema to structure the assignees detail
    """

    id: int
    email: EmailStr
    name: str
    address: str
    country: str
    language: str
    image: str
    mobile: str


class TicketOut(BaseModel):
    """
    Schema to use to send ticket details outside the application
    """

    id: int
    title: str
    description: str

    sla: SLAOut
    assignees: AssigneeOut


class TicketAttachmentOut(BaseModel):
    """
    Schema to send ticket attachment
    """

    attachment: List[str]
