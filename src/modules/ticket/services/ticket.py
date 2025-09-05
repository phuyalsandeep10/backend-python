import logging
import secrets
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_400_BAD_REQUEST

from src.common.context import TenantContext, UserContext
from src.config.settings import settings
from src.db.config import async_session
from src.factory.notification import NotificationFactory
from src.modules.auth.models import User
from src.modules.organizations.models import Organization
from src.modules.team.models import Team
from src.utils.common import extract_subset_from_dict
from src.utils.exceptions.ticket import (
    TicketAlreadyConfirmed,
    TicketNotFound,
    TicketSLANotFound,
    TicketStatusNotFound,
)
from src.utils.get_templates import get_templates
from src.utils.response import CustomResponse as cr
from src.utils.validations import TenantEntityValidator

from ..enums import TicketLogActionEnum, TicketStatusEnum
from ..models import (
    Ticket,
    TicketAttachment,
    TicketNotes,
    TicketPriority,
    TicketSLA,
    TicketStatus,
)
from ..schemas import CreateTicketSchema, EditTicketSchema, TicketByStatusSchema
from ..services.status import ticket_status_service

logger = logging.getLogger(__name__)


class TicketServices:
    """
    List of all methods and attributes
    """

    async def create_ticket(self, payload: CreateTicketSchema):
        """
        Create ticket for the organization
        """
        try:
            # for getting the default ticket status set by the organization
            sts = await self.get_default_ticket_status()
            sla = await self.get_default_ticket_sla(priority_id=payload.priority_id)

            if not sts:
                raise TicketStatusNotFound(detail="Default ticket status not found")

            if not sla:
                raise TicketSLANotFound(detail="Ticket SLA not found for this priority")

            data = payload.model_dump(exclude_none=True)
            data["status_id"] = sts.id
            data["sla_id"] = sla.id

            if "assignees" in data:
                data["assignees"] = await self.get_assigned_members_by_id(
                    data["assignees"]
                )

            await self.validate_foreign_restrictions(data)

            # generating the confirmation token using secrets
            data["confirmation_token"] = await self.generate_secret_tokens()
            # attachments are needed after creating ticket
            attachments = data.pop("attachments", None)

            # creating the ticket and saving in the log
            ticket = await Ticket.create(**data)
            await ticket.save_to_log(
                action=TicketLogActionEnum.TICKET_CREATED,
            )
            # handling ticket notes
            await self.handle_ticket_notes(data, ticket_id=ticket.id)

            if attachments:
                for attachment in attachments:
                    await TicketAttachment.create(
                        ticket_id=ticket.id, attachment=attachment
                    )

            # sending the confirmation email
            await self.send_confirmation_email(ticket)

            return cr.success(
                status_code=status.HTTP_201_CREATED,
                message="Successfully created a ticket",
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                status_code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
                message=f"{str(e)}",
                data=str(e),
            )

    async def list_tickets(self):
        """
        List all the tickets of the user organization
        """
        try:
            user_id = UserContext.get()
            all_tickets = await self.fetch_user_tickets(user_id)
            tickets = [ticket.to_dict() for ticket in all_tickets]
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully listed all tickets",
                data=tickets,
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while listing  tickets",
            )

    async def get_ticket(self, ticket_id: int):
        """
        List the particular ticket of the organization by id
        """
        try:
            ticket = await Ticket.find_one(
                where={"id": ticket_id},
                options=[
                    selectinload(Ticket.sla),
                    selectinload(Ticket.assignees),
                    selectinload(Ticket.priority),
                    selectinload(Ticket.status),
                    selectinload(Ticket.customer),
                    selectinload(Ticket.created_by),
                    selectinload(Ticket.department),
                    selectinload(Ticket.attachments),
                    selectinload(Ticket.all_notes),
                    selectinload(Ticket.all_notes).selectinload(TicketNotes.created_by),
                ],
            )
            if not ticket:
                raise TicketNotFound()

            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully listed the ticket",
                data=ticket.to_dict() if ticket else [],
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                status_code=getattr(e, "status_code", HTTP_400_BAD_REQUEST),
                message="Error while listing ticket",
                data=f"{str(e)}",
            )

    async def delete_ticket(self, ticket_id: int):
        """
        Deletes the ticket by id
        Raises:
            TicketNotFound if ticket not found
        """
        try:
            ticket = await Ticket.find_one(where={"id": ticket_id})
            if not ticket:
                raise TicketNotFound()
            await Ticket.soft_delete(
                where={
                    "id": ticket_id,
                }
            )

            # saving to the log
            await ticket.save_to_log(action=TicketLogActionEnum.TICKET_SOFT_DELETED)
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully deleted the ticket",
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                status_code=getattr(e, "status_code", HTTP_400_BAD_REQUEST),
                message="Error while deleting the tickets",
            )

    async def confirm_ticket(self, organization_id: int, ticket_id: int, token: str):
        """
        Confirms and activates the ticket by confirmation token
        Raises:
            TicketNotFound if ticket not found or invalid credentials
        """
        try:
            ticket = await Ticket.find_one(
                where={
                    "id": ticket_id,
                    "confirmation_token": token,
                    "organization_id": organization_id,
                }
            )
            if ticket is None:
                raise TicketNotFound("Invalid credentials")

            already_opened = await Ticket.find_one(
                where={
                    "id": ticket_id,
                    "confirmation_token": token,
                    "organization_id": organization_id,
                    "opened_at": {"ne": None},
                }
            )

            if already_opened:
                raise TicketAlreadyConfirmed()

            # to find which is the open status category status defined the organization it could be in-progress, or open,ongoing
            open_status_category = (
                await ticket_status_service.get_status_category_by_name(
                    name="open", organization_id=organization_id
                )
            )
            payload = {
                "status_id": open_status_category.id,
                "organization_id": organization_id,
                "opened_at": datetime.utcnow(),
            }
            # updating and saving to the log
            await Ticket.update(id=ticket.id, **payload)
            await ticket.save_to_log(
                action=TicketLogActionEnum.TICKET_CONFIRMED,
                previous_value=extract_subset_from_dict(ticket.to_json(), payload),
                new_value={**payload, "opened_at": payload["opened_at"].isoformat()},
            )
            return cr.success(
                message="Your ticket has been activated.", data={"id": ticket.id}
            )

        except Exception as e:
            logger.exception(e)
            return cr.error(message=f"{str(e)}", data=str(e))

    async def list_tickets_by_status(self, payload: TicketByStatusSchema):
        """
        List the tickets on the basis of status id
        """
        try:
            # validator so that it doesn't fetch other organization status tickets
            tenant = TenantEntityValidator()
            await tenant.validate(TicketStatus, payload.status_id)

            tickets = await Ticket.filter(
                where={"status_id": payload.status_id},
                related_items=[
                    selectinload(Ticket.sla),
                    selectinload(Ticket.assignees),
                    selectinload(Ticket.priority),
                    selectinload(Ticket.status),
                    selectinload(Ticket.customer),
                    selectinload(Ticket.created_by),
                    selectinload(Ticket.department),
                    selectinload(Ticket.attachments),
                    selectinload(Ticket.all_notes),
                ],
            )

            # return empty list if there is none, instead of throwing error
            if not tickets:
                return cr.success(
                    message="Successfully fetched tickets by the status", data=[]
                )

            return cr.success(
                message="Successfully fetched tickets by the status",
                data=[ticket.to_dict() for ticket in tickets],
            )

        except Exception as e:
            return cr.error(
                message="Error while listing the tickets by status", data=str(e)
            )

    async def edit_ticket(self, ticket_id: int, payload: EditTicketSchema):
        """
        Edit ticket on the basis of the id
        """
        try:
            ticket = await Ticket.find_one(
                where={
                    "id": ticket_id,
                },
                related_items=[
                    selectinload(Ticket.sla),
                    selectinload(Ticket.assignees),
                    selectinload(Ticket.priority),
                    selectinload(Ticket.status),
                    selectinload(Ticket.customer),
                    selectinload(Ticket.created_by),
                    selectinload(Ticket.department),
                    selectinload(Ticket.attachments),
                    selectinload(Ticket.all_notes),
                ],
            )
            if ticket is None:
                raise TicketNotFound()

            # checking if the foreignkeys don't belong to the other organization
            tenant = TenantEntityValidator()
            data = dict(payload.model_dump(exclude_none=True))

            if "priority_id" in data:
                await tenant.validate(
                    TicketPriority, data["priority_id"], check_default=True
                )
                # we need to change sla as well
                new_sla = await self.get_default_ticket_sla(data["priority_id"])
                print("The new sla", new_sla.id)
                data["sla_id"] = new_sla.id
                print("The data sla_id", data["sla_id"])
            if "status_id" in data:
                await tenant.validate(
                    TicketStatus, data["status_id"], check_default=True
                )
            if "department_id" in data:
                await tenant.validate(Team, data["department_id"])

            if "assignees" in data:
                assignees = await self.get_assigned_members_by_id(data["assignees"])

                async with async_session() as session:
                    ticket.assignees = assignees
                    await session.merge(ticket)
                    await session.commit()
                    del data["assignees"]

            # updating and logging
            await Ticket.update(ticket.id, **data)
            await ticket.save_to_log(
                action=TicketLogActionEnum.TICKET_UPDATED,
                previous_value=extract_subset_from_dict(ticket.to_json(), data),
                new_value=data,
            )

            return cr.success(
                message="Successfully updated the ticket",
            )

        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while editing the ticket", data=str(e))

    async def get_default_ticket_status(self):
        """
        Returns the default tiket status set by the organization else move to default ticket status
        """
        sts = await TicketStatus.find_one(
            where={"status_category": TicketStatusEnum.PENDING}
        )
        if not sts:
            raise TicketStatusNotFound(detail="Pending status has not been set")

        return sts

    async def get_default_ticket_sla(self, priority_id: int):
        """
        Returns the default tiket status set by the organization else move to default ticket status
        """
        sla = await TicketSLA.find_one(where={"priority_id": priority_id})
        if not sla:
            raise TicketSLANotFound(
                detail="SLA with this priority has not been defined"
            )

        return sla

    async def get_assigned_members_by_id(self, user_ids: list[int]):
        """
        Returns the list of users by users id
        """
        users = []
        for assigne_id in user_ids:
            usr = await User.find_one(where={"id": assigne_id})
            users.append(usr)
        return users

    async def validate_foreign_restrictions(self, data):
        """
        Validates foreign restriction to secure data leaks
        """
        # validating the data
        tenant = TenantEntityValidator()

        await tenant.validate(TicketPriority, data["priority_id"], check_default=True)
        await tenant.validate(TicketStatus, data["status_id"], check_default=True)
        await tenant.validate(TicketSLA, data["sla_id"], check_default=True)
        await tenant.validate(Team, data["department_id"])

    async def generate_secret_tokens(self):
        """
        Returns the 32 character secret token
        """
        return secrets.token_hex(32)

    async def send_confirmation_email(self, ticket: Ticket):
        """
        Sends email for the confirmation
        """

        tick = await Ticket.find_one(
            where={"id": ticket.id},
            related_items=[
                selectinload(Ticket.organization),
                selectinload(Ticket.customer),
            ],
        )
        if not tick:
            raise TicketNotFound()
        receiver = tick.customer.email if tick.customer_id else tick.customer_email
        name = tick.customer.name if tick.customer_id else tick.customer_name
        html_content = {
            "name": name,
            "ticket": tick,
            "settings": settings,
        }
        template = await get_templates(
            name="ticket/ticket-confirmation-email.html", content=html_content
        )
        email = NotificationFactory.create("email")
        await email.send_ticket_email(
            from_email=(tick.sender_domain, tick.organization.name),
            subject="Ticket confirmation",
            recipients=receiver,
            body_html=template,
            ticket=tick,
            mail_type=TicketLogActionEnum.CONFIRMATION_EMAIL_SENT,
        )

    async def fetch_user_tickets(self, user_id: int):
        """
        List all the user tickets
        """
        # checking if user is admin or not
        organization_id = TenantContext().get()
        organization = await Organization.find_one(where={"id": organization_id})
        if not organization:
            raise HTTPException(
                detail="Couldnot find organization", status_code=HTTP_400_BAD_REQUEST
            )
        all_tickets = await Ticket.filter(
            related_items=[
                selectinload(Ticket.sla),
                selectinload(Ticket.assignees),
                selectinload(Ticket.priority),
                selectinload(Ticket.status),
                selectinload(Ticket.customer),
                selectinload(Ticket.created_by),
                selectinload(Ticket.department),
                selectinload(Ticket.attachments),
                selectinload(Ticket.all_notes).selectinload(TicketNotes.created_by),
            ],
        )
        if organization.owner_id == user_id:
            return all_tickets

        # returning tickets that belongs to you
        user_tickets = [
            ticket
            for ticket in all_tickets
            for user in ticket.assignees
            if user.id == user_id
        ]

        return user_tickets

    async def handle_ticket_notes(self, data: dict[str, Any], ticket_id: int):
        """
        Handles ticket notes, creates ticket notes
        """
        if "notes" not in data:
            return data

        ticket = await Ticket.filter(where={"id": ticket_id})
        if not ticket:
            raise TicketNotFound()

        user_id = UserContext().get()
        note_payload = {
            "created_by_id": user_id,
            "ticket_id": ticket_id,
            "content": data["notes"],
        }

        await TicketNotes.create(**note_payload)


ticket_services = TicketServices()
