import logging
from datetime import datetime

import src.socket_config as socket_config
from src.common.dependencies import get_user_by_token
from src.websocket.constants.chat_namespace_constants import TICKET_CHAT_NAMESPACE
from src.websocket.chat_namespaces.base_namespace import BaseNameSpace


logger = logging.getLogger(__name__)


class TicketNameSpace(BaseNameSpace):
    """
    Ticket namespace for socket
    """

    namespace = TICKET_CHAT_NAMESPACE

    def __init__(self):
        self.sio = socket_config.sio
        super().__init__(self.namespace)

    async def on_connect(self, sid, environ, auth):
        """
        This function is triggered whenever socket client connects to the namespace
        """
        print("Connecting ticket socket")
        token = auth.get("token")
        if not token:
            return False  # reject the connection
        user = await get_user_by_token(token)
        if not user:
            return False  # reject the connection
        await self.sio.save_session(sid, {"user": user}, namespace=self.namespace)

        ticket_id = auth.get("ticket_id")
        if not ticket_id:
            print("Not ticket_id")
            return

        room = f"ticket_{ticket_id}"
        await self.sio.enter_room(sid, room, namespace=self.namespace)
        logger.info("User %s has joined %s with %d ticket", user.email, room, ticket_id)

    async def broadcast_message(
        self, message: str, user_email: str, ticket_id: int, created_at: datetime
    ):
        """
        This method broadcasts the message to the entire room
        """
        if not ticket_id or not user_email or not message:
            return

        room = f"ticket_{ticket_id}"
        payload = {"user": user_email, "message": message, "created_at": created_at}
        await self.redis_publish(channel=room, message=payload)

        await self.sio.emit(
            "ticket_broadcast", room=room, namespace=self.namespace, data=payload
        )
        logger.info("User %s sent message in %s : %s", user_email, room, message)
