


from src.websocket.constants.channel_names import (
    CUSTOMER_NOTIFICATION_CHANNEL,
    MESSAGE_CHANNEL,
    AGENT_ONLINE_CHANNEL

)
from .base_chat_namespace import BaseChatNamespace
from src.websocket.constants.chat_namespace_constants import AGENT_CHAT_NAMESPACE



# Redis keys


# Redis helper


class AgentChatNamespace(BaseChatNamespace):

    def __init__(self):
        super().__init__(AGENT_CHAT_NAMESPACE)

    async def _notify_to_user_customers(self, org_id: int, user_id: int,sid:str):
        print("notify users in the same workspace that an agent has connected")
        from src.models import User
        user = await User.update(user_id,is_online=True)

        await self.redis_publish(
            channel=AGENT_ONLINE_CHANNEL,
            message={
                    "event": self.agent_connected,
                    "mode": "online",
                    "organization_id": org_id,
                    "user_id": user_id,
                    "sid": sid,
                    "user": user.to_json()
                }
            
        )
    

    async def on_connect(self, sid, environ, auth):
        from src.common.dependencies import get_user_by_token
        
        
        print(f"🔌Agent Socket connection attempt: {sid}")
        if not auth:
            print("No auth data provided")
            return False
        token = auth.get("token")
        user = await get_user_by_token(token)

        if not user:
            print("Invalid token provided")
            return False

        organization_id = user.attributes.get("organization_id")

        if not organization_id:
            print("User has no organization_id")
            return False

        await self.conversation_service.join_agent_group(sid, organization_id, user.id)
        await self._notify_to_user_customers(organization_id, user.id,sid)
        
        


        print(
            f"\n User {user.id} connected with sid {sid} in workspace {organization_id}"
        )
        return True



