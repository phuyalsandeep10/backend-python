

from src.websocket.constants.channel_names import  CUSTOMER_JOIN_CONVERSATION, AGENT_JOIN_CONVERSATION,CUSTOMER_LEAVE_CONVERSATION,AGENT_LEAVE_CONVERSATION
from src.websocket.utils.conversation_utils import ConversationUtility
from src.websocket.constants.chat_namespace_constants import CUSTOMER_CHAT_NAMESPACE, AGENT_CHAT_NAMESPACE
from src.websocket.constants.chat_event_constants import customer_conversation_join,customer_conversation_leave,agent_conversation_join,agent_conversation_leave



class ConversationService:
    customer_namespace = CUSTOMER_CHAT_NAMESPACE
    agent_namespace = AGENT_CHAT_NAMESPACE

    customer_join = customer_conversation_join
    agent_join = agent_conversation_join

    customer_leave = customer_conversation_leave
    agent_leave = agent_conversation_leave

    def __init__(self):

        from src.websocket.utils.chat_utils import ChatUtils
        from src.socket_config import sio

        self.sio = sio  
        self.conversation_utils = ConversationUtility
        self.chatUtils = ChatUtils
    
    async def get_redis(self):
        from src.services.redis_service import RedisService
        return await RedisService.get_redis()
    
    def get_room_name(self,conversation_id:int):

        return self.chatUtils.conversation_group(conversation_id)

    async def redis_publish(self, channel:str, message:dict):
        from src.services.redis_service import RedisService
        return await RedisService.redis_publish(channel, message)

    async def join_conversation(self, sid:str, room:str, namespace:str):
        await self.sio.enter_room(sid=sid, room=room, namespace=namespace)

    async def leave_conversation(self, sid:str, room:str, namespace:str):
        await self.sio.leave_room(sid=sid, room=room, namespace=namespace)
    


    async def join_agent_group(self,sid,orgId:int,user_id:int):
        print(f"agent {user_id} joining group for org {orgId} with sid {sid}")
        await self.conversation_utils.set_agent_sid(sid, user_id)
        room_name = self.chatUtils.user_notification_group(orgId)
        await self.sio.enter_room(sid=sid, room=room_name, namespace=self.agent_namespace)
    
   
    async def customer_connect(self,sid,customer_id:int,orgId:int):
        await self.conversation_utils.set_customer_sid(sid, customer_id)
        room_name = self.chatUtils.customer_notification_group(orgId)
        await self.sio.enter_room(sid=sid, room=room_name, namespace=self.customer_namespace)

    async def customer_join_conversation(self, customer_id:int, conversation_id:int):
        from src.models import Customer,Conversation

        try:
            
            sid = await self.conversation_utils.get_customer_sid(customer_id)

            if not sid:
                print(f"❌ Cannot join conversation: No SID found for customer {customer_id}")
                return False

            conversation = await Conversation.get(conversation_id)
            customer = await Customer.get(customer_id)

            if not conversation or not customer:
                print(f"❌ Cannot join conversation: No conversation found for ID {conversation_id} or customer found for ID {customer_id}")
                return False

            room = self.get_room_name(conversation_id)

            await self.join_conversation(sid=sid, room=room, namespace=self.customer_namespace)
            await self.conversation_utils.set_conversation_id(sid,conversation_id=conversation_id)
            
            await self.redis_publish(
                CUSTOMER_JOIN_CONVERSATION,
                {"event":self.customer_join, "sid": sid,"conversation_id":conversation_id, "conversation":{**conversation.to_json(),"customer":customer.to_json()},"conversation_id":conversation_id,"organization_id":conversation.organization_id}
            )
        except Exception as e:
            print(f"Error joining customer {customer_id} to conversation {conversation_id}: {e}")

    async def agent_join_conversation(self, user_id:int, conversation_id:int):
        from src.models import User
        from src.websocket.utils.conversation_utils import ConversationUtility


        try:
            sid = await ConversationUtility.get_agent_sid(user_id)

            print(f'sid {sid}')

            if not sid:
                print(f"❌ Cannot join conversation: No SID found for user {user_id}")
                return False
            
            user = await User.get(user_id)

            if not user:

                print(f"❌ Cannot join conversation: No user found for ID {user_id}")

                return False
            
            room = self.get_room_name(conversation_id)
            print(f"agent room {room}")

            await self.sio.enter_room(sid=sid, room=room, namespace=self.agent_namespace)
            # await self.conversation_utils.set_conversation_id(sid,conversation_id=conversation_id)

            await self.redis_publish(
                AGENT_JOIN_CONVERSATION,
                {"event": self.agent_join, "sid": sid, "user": user.to_json(),"conversation_id":conversation_id}
            )
        except Exception as e:
            print(f"Error joining agent {user_id} to conversation {conversation_id}: {e}")

    async def customer_leave_conversation(self, sid:str):
        try:
            conversation_id = await self.conversation_utils.get_conversation_id(sid)
            room = self.get_room_name(conversation_id)

            
            if not sid:
                print(f"❌ Cannot leave conversation: No SID found for customer {customer_id}")
                return False

            room = self.get_room_name(conversation_id)

            await self.sio.leave_room(sid=sid, room=room, namespace=self.customer_namespace)

            customer_id = await self.conversation_utils.get_customer_id(sid)
            await self.conversation_utils.remove_sid_from_conversation(sid,conversation_id=conversation_id)
            

            await self.redis_publish(
                CUSTOMER_LEAVE_CONVERSATION,
                {"event": self.customer_leave, "sid": sid, "customer_id": customer_id}
            )
        except Exception as e:
            print(f"Error leaving customer :{e}")
    
    async def agent_leave_conversation(self, sid:str,data):
        print("agent leave conversation ")
        try:
            
            conversation_id = data.get('conversation_id')
         
            
            if not sid:
                print(f"❌ Cannot leave conversation: No SID found for agent with SID {sid}")
                return False

            room = self.get_room_name(conversation_id)
            print(f"LEAVING: sid={sid}, room={room}, namespace={self.agent_namespace}")

            await self.sio.leave_room(sid=sid, room=room, namespace=self.agent_namespace)
            

            user_id = await self.conversation_utils.get_agent_id(sid)
            await self.conversation_utils.remove_sid_from_conversation(sid,conversation_id=conversation_id)

            await self.redis_publish(
                AGENT_LEAVE_CONVERSATION,
                {"event": self.agent_leave, "sid": sid, "user_id": user_id}
            )
        except Exception as e:
            print(f"Error leaving agent :{e}")


    

        
    
    




    






    
