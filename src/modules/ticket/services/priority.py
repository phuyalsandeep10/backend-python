import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_409_CONFLICT,
)

from src.utils.common import extract_subset_from_dict
from src.utils.exceptions.ticket import TicketPriorityExists, TicketPriorityNotFound
from src.utils.response import CustomResponse as cr

from ..enums import TicketLogActionEnum
from ..models import Ticket, TicketPriority
from ..schemas import EditTicketPrioritySchema, PriorityOut

logger = logging.getLogger(__name__)


class TicketPriorityService:
    """
    List of methods and attributes to contain core logic of ticket priority
    """

    async def list_priorities(self):
        """
        List all the priorites on the basis of the organization
        """
        try:
            priorities = await TicketPriority.filter()
            payload = [priority.to_json(PriorityOut) for priority in priorities]
            return cr.success(message="Successfully listed priorities", data=payload)
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while listing priorities", data=str(e))

    async def create_priorities(self, payload):
        """
        create single priority or list of priorities at the same time
        Raises :
            IntegrityError if priority with the same name and level already exists within the organization
        """
        try:
            for d in payload:
                data = d.model_dump()
                same_name = await TicketPriority.find_one(
                    where={
                        "name": {"mode": "insensitive", "value": data["name"]},
                    }
                )
                same_name_and_level = await TicketPriority.find_one(
                    where={
                        "name": {"mode": "insensitive", "value": data["name"]},
                        "level": data["level"],
                    }
                )
                if same_name or same_name_and_level:
                    raise TicketPriorityExists(
                        detail="Ticket priority with this name or level already exists"
                    )

                # saving and logging
                priority = await TicketPriority.create(**data)
                await priority.save_to_log(
                    action=TicketLogActionEnum.PRIORITY_CREATED,
                    new_value=priority.to_json(),
                )

            return cr.success(
                message="Successfully created priorities", status_code=HTTP_201_CREATED
            )
        except IntegrityError as e:
            logger.exception(e)
            return cr.error(
                message="Priority with this name or level already exists",
                status_code=HTTP_409_CONFLICT,
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(message=f"{str(e)}", data=str(e))

    async def get_priority(self, priority_id: int):
        """
        List particular priority of the organization
        Raises :
            TicketPriorityNotFound if priority not found of that priority_id
        """
        try:
            priority = await TicketPriority.find_one(where={"id": priority_id})
            if priority is None:
                raise TicketPriorityNotFound()
            return cr.success(
                message="Successfully listed priority",
                data=priority.to_json(PriorityOut) if priority else None,
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                message=f"{str(e)}",
                status_code=getattr(e, "status_code", HTTP_400_BAD_REQUEST),
            )

    async def delete_priority(self, priority_id: int):
        """
        soft delete particular priority of the organization
        Raises :
            TicketPriorityNotFound if priority not found of that priority_id
        """
        try:
            priority = await TicketPriority.find_one(where={"id": priority_id})
            if not priority:
                raise TicketPriorityNotFound()
            # before deleting finding if there is any tickets with this priority
            ticket_exists = await self.find_ticket_by_priority(priority_id)
            if ticket_exists:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail="Tickets with this priority exists, hence cannot be deleted",
                )
            # deleting and logging
            await TicketPriority.delete(where={"id": priority_id})
            await priority.save_to_log(
                action=TicketLogActionEnum.PRIORITY_DELETED,
                previous_value=priority.to_json(),
            )

            return cr.success(message="Successfully deleted priority", data=None)
        except Exception as e:
            logger.exception(e)
            return cr.error(
                message=f"{str(e)}",
                data=str(e),
                status_code=getattr(e, "status_code", HTTP_400_BAD_REQUEST),
            )

    async def edit_priority(self, priority_id: int, payload: EditTicketPrioritySchema):
        """
        Edit priority of the organization
        Raises :
            TicketPriorityNotFound if priority not found of that priority_id
        """
        try:
            priority = await TicketPriority.find_one(
                where={
                    "id": priority_id,
                }
            )
            if priority is None:
                raise TicketPriorityNotFound()

            # updating and logging
            updated_priority = await TicketPriority.update(
                priority.id, **payload.model_dump(exclude_none=True)
            )
            await priority.save_to_log(
                action=TicketLogActionEnum.PRIORITY_UPDATED,
                previous_value=extract_subset_from_dict(
                    priority.to_json(), payload.model_dump(exclude_none=True)
                ),
                new_value=payload.model_dump(exclude_none=True),
            )

            return cr.success(
                message="Successfully updated  prioirty",
                data=(
                    updated_priority.to_json(PriorityOut) if updated_priority else None
                ),
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(
                message=f"{str(e)}",
                data=str(e),
                status_code=getattr(e, "status_code", HTTP_400_BAD_REQUEST),
            )

    async def find_ticket_by_priority(self, priority_id: int):
        """
        Returns the list of tickets by priority
        """
        try:
            tickets = await Ticket.filter(where={"priority_id": priority_id})
            return tickets
        except Exception:
            return None


priority_service = TicketPriorityService()
