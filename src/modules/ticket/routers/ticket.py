from typing import List

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from src.common.context import TenantContext
from src.common.dependencies import get_current_user
from src.modules.ticket.schemas import (
    CreateTicketNotesSchema,
    CreateTicketSchema,
    EditTicketSchema,
    TicketByStatusSchema,
    TicketOut,
)
from src.modules.ticket.services.ticket import ticket_services
from src.utils.response import CustomResponse as cr
from src.utils.response import CustomResponseSchema
from src.common.context import TenantContext
from src.utils.response import CustomResponse as cr

from ..deps import request_ticket_access

router = APIRouter()


@router.post("/", summary="Creates new ticket", response_model=CustomResponseSchema)
async def register_ticket(payload: CreateTicketSchema):
    """
    Register new ticket to the organization
    """
    return await ticket_services.create_ticket(payload)


@router.get("/customers")
async def get_customers():
    """
    Lists all the customers
    """
    organization_id = TenantContext.get()
    from src.models import Customer

    records = await Customer.filter({"organization_id": organization_id})
    return cr.success(data=[record.to_json() for record in records])

@router.get('/customers')
async def get_customers():
    organizationId = TenantContext.get()
    from src.models import Customer
    records = await Customer.filter({"organization_id": organizationId})
    return cr.success(data=[record.to_json() for record in records])


@router.get(
    "/",
    summary="List all tickets",
    response_model=CustomResponseSchema[List[TicketOut]],
)
async def list_tickets():
    """
    List all the tickets of the organization
    """
    return await ticket_services.list_tickets()


@router.post(
    "/by-status",
    summary="List tickets by status",
    response_model=CustomResponseSchema[List[TicketOut]],
)
async def list_tickets_by_status(payload: TicketByStatusSchema):
    """
    List all the tickets of the organization by id
    """
    return await ticket_services.list_tickets_by_status(payload)


@router.get(
    "/{ticket_id:int}",
    summary="Get a ticket",
    response_model=CustomResponseSchema[TicketOut],
)
async def get_ticket(ticket_id: int, _: None = Depends(request_ticket_access)):
    """
    Get ticket of the organization by id
    """
    return await ticket_services.get_ticket(ticket_id)


@router.patch(
    "/{ticket_id:int}",
    summary="Get a ticket",
    response_model=CustomResponseSchema[TicketOut],
)
async def edit_ticket(ticket_id: int, payload: EditTicketSchema):
    """
    Edit ticket of the organization by id
    """
    return await ticket_services.edit_ticket(ticket_id, payload)


@router.delete(
    "/{ticket_id:int}", summary="Delete a ticket", response_model=CustomResponseSchema
)
async def delete_ticket(ticket_id: int):
    """
    Delete ticket of the organiation by id
    """
    return await ticket_services.delete_ticket(ticket_id)


@router.get(
    "/confirm/{organization_id:int}/{ticket_id:int}/{confirmation_token:str}",
    response_model=CustomResponseSchema,
)
async def confirm_ticket(organization_id: int, ticket_id: int, confirmation_token: str):
    """
    Confirmt the ticket and set status to open defined by the organization
    """
    return await ticket_services.confirm_ticket(
        organization_id, ticket_id, token=confirmation_token
    )


@router.post("/notes/{ticket_id:int}")
async def add_notes(ticket_id: int, payload: CreateTicketNotesSchema):
    """
    Add notes to the ticket
    """
    try:
        await ticket_services.handle_ticket_notes(
            payload.model_dump(), ticket_id=ticket_id
        )
        return cr.success(
            status_code=HTTP_201_CREATED, message="Successfully created a ticket note"
        )
    except Exception as e:
        return cr.error(message=f"{str(e)}")
