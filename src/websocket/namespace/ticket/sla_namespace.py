import logging
from typing import Any

import src.socket_config as socket_config
from src.common.dependencies import get_user_by_token
from src.modules.ticket.models.ticket import Ticket
from src.websocket.constants.chat_namespace_constants import TICKET_SLA_NAMESPACE
from src.websocket.chat_namespaces.base_namespace import BaseNameSpace


logger = logging.getLogger(__name__)


class TicketSLANameSpace(BaseNameSpace):
    """
    Ticket SLA Namespace
    """

    namespace = TICKET_SLA_NAMESPACE

    def __init__(self):
        self.sio = socket_config.sio
        super().__init__(self.namespace)

    async def on_connect(self, sid, environ, auth):
        """
        This function is triggered whenever socket client connects to the namespace
        """

        token = auth.get("token")
        if not token:
            return False  # reject the connection
        user = await get_user_by_token(token)
        if not user:
            return False  # reject the connection
        await self.sio.save_session(sid, {"user": user}, namespace=self.namespace)

        await self.sio.enter_room(sid, room=f"user:{user.id}", namespace=self.namespace)

    async def broadcast_message(
        self,
        payload: dict[str, Any],
        message: str,
        receivers_id: list[int],
        alert_type: str,
        level: int,
    ):
        """
        This method broadcasts the message to the entire room
        """
        if not receivers_id or not message:
            return

        for uid in receivers_id:
            await self.sio.emit(
                "ticket_sla_alert",
                {
                    "message": message,
                    "payload": payload,
                    "alert_type": alert_type,
                    "level": level,
                },
                room=f"user:{uid}",
                namespace=self.namespace,
            )
