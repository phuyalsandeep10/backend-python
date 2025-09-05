from .base_namespace import BaseNameSpace
from src.websocket.constants.channel_names import TYPING_CHANNEL, TYPING_STOP_CHANNEL, MESSAGE_SEEN_CHANNEL,CUSTOMER_OFFLINE_CHANNEL,AGENT_OFFLINE_CHANNEL
from src.websocket.services.conversation_service import ConversationService
from src.websocket.constants.chat_event_constants import receive_message,stop_typing,message_seen,message_notification,customer_disconnected,receive_typing,customer_land,agent_connected,agent_disconnected


class BaseChatNamespace(BaseNameSpace):
    receive_message = receive_message
    receive_typing = receive_typing
    stop_typing = stop_typing
    message_seen = message_seen 

    customer_land = customer_land
    message_notification = message_notification
    agent_connected = agent_connected
    agent_disconnected=agent_disconnected
    customer_disconnected=customer_disconnected
    
    is_customer: bool = False

    def __init__(self, namespace: str, is_customer: bool = False):
        super().__init__(namespace)
        self.is_customer = is_customer
        self.conversation_service = ConversationService()
    

    async def on_disconnect(self, sid):
        from src.models import Customer,User
        print("agent disconnected..")
        # on disconnect
        await self.disconnect(sid)
        try:

            if self.is_customer:
                customerId = await self.conversation_service.conversation_utils.get_customer_id(sid)
                await self.conversation_service.customer_leave_conversation(sid)
                print(f'customer_id {customerId} and customer leaving ..')

                customer = await Customer.update(int(customerId), is_online=False)
                await customer.update_log()

                await self.redis_publish(
                    channel=CUSTOMER_OFFLINE_CHANNEL,
                    message={
                        "event":self.customer_disconnected,
                        "customer_id":int(customerId),
                        "sid":sid,
                        "customer":customer.to_json(),
                        "organization_id":customer.organization_id
                    }
                )
            else:
                agentId = await self.conversation_service.conversation_utils.get_agent_id(sid)
                print(f'agentId {agentId} and agent leaving ..')
            
                # await self.conversation_service.agent_leave_conversation(sid)
                user = await User.update(int(agentId),is_online=False)
                print(f'agent id {agentId}')
                
                await self.redis_publish(
                    channel=AGENT_OFFLINE_CHANNEL,
                    message={
                        "event":self.agent_disconnected,
                        "agent_id":int(agentId),
                        "sid":sid,
                        "user":user.to_json(),
                        "organization_id":user.attributes.get('organization_id')
                        
                    }
                )
        except Exception as e:
            print(f"exception as e {e}")
    
    async def on_leave_conversation(self, sid,data):
        print(f"conversation leave sid {sid}")
        if(self.is_customer):
            await self.conversation_service.customer_leave_conversation(sid)
        else:
            await self.conversation_service.agent_leave_conversation(sid,data)


    async def on_typing(self, sid, data: dict):
        conversation_id = data.get('conversation_id')
        organization_id = data.get("organization_id")
        
       
        
        if not conversation_id or not organization_id:
            return False

        await self.redis_publish(
            channel=TYPING_CHANNEL,
            message={
                "event": self.receive_typing,
                "sid": sid,
                "message": data.get("message", ""),
                "mode": data.get("mode", "typing"),
                "conversation_id": conversation_id,
                "organization_id": organization_id,
                "is_customer": self.is_customer,
            },
        )

    async def on_stop_typing(self, sid, data: dict):
        conversation_id = data.get('conversation_id')
        organization_id = data.get("organization_id")
        print(f"conversation id {conversation_id}")

        if not conversation_id:
            return False

        await self.redis_publish(
            channel=TYPING_STOP_CHANNEL,
            message={
                "event": self.stop_typing,
                "sid": sid,
                "conversation_id": conversation_id,
                "is_customer": self.is_customer,
                "organization_id": organization_id,

            },
        )

    async def on_message_seen(self, sid, data: dict):
        print(f"message seen {sid}")
        messageId = data.get("message_id")
        organization_id = data.get('organization_id')
        
        if not messageId:
            return False

        message = await self.conversation_service.chatUtils.save_message_seen(messageId)
        if not message:
            return False
    
        await self.redis_publish(
            channel=MESSAGE_SEEN_CHANNEL,
            message={
                "event": self.message_seen,
                "conversation_id": message.conversation_id,
                "message_id": messageId,
                "is_customer": self.is_customer , # If no user_id, it's a customer message,
                "organization_id":organization_id
            },
        )



