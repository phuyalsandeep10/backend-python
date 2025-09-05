from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from src.common.context import TenantContext, UserContext
from src.models import Organization
from src.utils.exceptions.ticket import TicketNotFound

from .models import Ticket


async def request_ticket_access(ticket_id: int):
    """
    Checks if the user has the access to the ticket or not
    Raises
        403 Forbidden if user doesnt have any access
    """

    user_id = UserContext().get()
    organization_id = TenantContext().get()

    ticket_exists = await Ticket.find_one(where={"id": ticket_id})
    if not ticket_exists:
        raise TicketNotFound()

    assigned_ids = [assignee.id for assignee in ticket_exists.assignees]
    # checking the user access to the request
    if ticket_exists.created_by_id == user_id or user_id in assigned_ids:
        return

    # if the user is an owner of an organization the access is granted
    organization = await Organization.find_one(where={"id": organization_id})
    if not organization:
        raise HTTPException(
            detail="Organization doesn't exists", status_code=HTTP_400_BAD_REQUEST
        )

    if organization.owner_id == user_id:
        return

    raise HTTPException(
        detail="You are not authorized to access this ticket",
        status_code=HTTP_403_FORBIDDEN,
    )
