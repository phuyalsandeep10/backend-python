import socketio
from src.websocket.constants.chat_namespace_constants import AGENT_CHAT_NAMESPACE, CUSTOMER_CHAT_NAMESPACE

from src.websocket.constants.channel_names import (
    AGENT_NOTIFICATION_CHANNEL,
    MESSAGE_CHANNEL,
    TYPING_CHANNEL,
    TYPING_STOP_CHANNEL,
    MESSAGE_SEEN_CHANNEL,
    CONVERSATION_UNRESOLVED_CHANNEL,
    CUSTOMER_LAND_WEBSITE,
    AGENT_ONLINE_CHANNEL,
    CUSTOMER_JOIN_CONVERSATION,
    AGENT_OFFLINE_CHANNEL,
    CUSTOMER_OFFLINE_CHANNEL,
)
from src.websocket.constants.chat_event_constants import message_notification



class ChatSubscriber:
    agent_namespace = AGENT_CHAT_NAMESPACE
    customer_namespace = CUSTOMER_CHAT_NAMESPACE
    

    def __init__(
        self, sio: socketio.AsyncServer, namespace: str = None, payload: dict = {},
        chatUtils=None
    ):
        # print(f"chat subscriber payload {payload} and type {type(payload)}")
        self.sio = sio
        self.payload = payload
        self.event = payload.get("event")
        self.namespace = namespace
        self.chatUtils = chatUtils
        self.organizationId = payload.get("organization_id")
        self.conversationId = payload.get("conversation_id")

    async def emit(self, room: str, namespace: str = None, sid: str = None):
        namespace = namespace if namespace else self.namespace
        print(f"emit to room {room} ")
        print(f"emit to namespace {namespace}")
        print(f"emit to event {self.event}")
        print(f"skip to sid {sid}")

      
        
        # print(f"emit to payload {self.payload}")
        
        try:
            result = await self.sio.emit(
                event=self.event,
                room=room,
                data=self.payload,
                namespace=namespace,
                skip_sid=sid,
            )
            print(f"✅ Emitted event '{self.event}' to room '{room}' in namespace '{namespace}'")
            return result
        except Exception as e:
            print(f"❌ Emit failed: {e}")
            return None

    async def agent_notification(self):
        print("📢 Agent notification broadcast ")
        room_name = self.chatUtils.user_notification_group(
            org_id=self.organizationId
        )
        await self.emit(room_name, namespace=self.agent_namespace)

    async def customer_notification(self):
        print("📢 Customer notification broadcast")
        room_name = self.chatUtils.customer_notification_group(
            org_id=self.organizationId
        )
        await self.emit(room_name, namespace=self.customer_namespace)

    async def agent_message_broadcast(self):
        # print("agent message broadcast")
        await self.agent_notification()
        # room_name = self.chatUtils.conversation_group(
        #     conversation_id=self.conversationId
        # )

        # await self.emit(
        #     room_name, namespace=self.agent_namespace, sid=self.payload.get("sid")
        # )
    

    async def customer_message_broadcast(self):
        print("customer message broadcast")
        room_name = self.chatUtils.conversation_group(
            conversation_id=self.conversationId
        )
        sids = self.sio.manager.rooms.get(self.customer_namespace, {}).get(room_name, set())
        print(f"sids in room {room_name}: {sids}")
        
        # Skip the sender if sid is provided
        skip_sid = self.payload.get("sid")
        await self.emit(room_name, namespace=self.customer_namespace, sid=skip_sid)

    async def broadcast_conversation(self):
        is_customer = self.payload.get("is_customer")
        print(f"Broadcasting conversation - is_customer: {is_customer}")
        
        if is_customer:
            print("Customer message - broadcasting to agents only")
            return await self.agent_message_broadcast()

        print("Agent message - broadcasting to both customers and agents")
        await self.customer_message_broadcast()
        await self.agent_message_broadcast()
    
    async def agent_join_conversation(self):
        print("👥 Agent join conversation broadcast")
        await self.agent_message_broadcast()

    
    async def message(self):    
        
        # Check if this is a customer message and check agent availability
        if self.payload.get("is_customer"):
            # isAgentAvailable = await self._check_and_notify_agent_availability()
            # if not isAgentAvailable:
            #     print('agent is not available in this conversation')
                
            #     self.event = message_notification
            return await self.agent_notification()
        
        await self.broadcast_conversation()

    
    # async def _check_and_notify_agent_availability(self):
    #     """Check if agents are available in the conversation and notify customer if not"""
    #     from src.websocket.services.conversation_service import ConversationService
    #     try:
    #         conversation_id = self.payload.get("conversation_id")

    #         if not conversation_id:
    #             return False
    #         room_name = self.chatUtils.conversation_group(
    #             conversation_id=conversation_id
    #         )
            
   
     
    #         if self.sio.manager.rooms and room_name in self.sio.manager.rooms[self.agent_namespace]:
    #             sids_in_room = self.sio.manager.rooms[self.agent_namespace][room_name]
    #             actual_sids = list(sids_in_room.keys())
    #             print(f"sid {self.payload.get('sid')}")
    #             print(f"actual sid {actual_sids} of room: {room_name}")
    #             if len(actual_sids):
    #                 return True
               

    #         return False 
    #         # # Get the agent namespace instance to check availability
    #         # room_members = await  ConversationService().conversation_utils.get_conversation_sids(conversation_id=conversation_id)
    #         # filteredMembers = [v for v in room_members if v !=self.payload.get('sid')]

    #         # print(f"Members {room_members} and filtered room members {filteredMembers}")
    #         # # Create a temporary instance to check availability
            
            
    #         # return len(filteredMembers)>0

    #     except Exception as e:
    #         print(f"⚠️ Error checking agent availability for message: {e}")
    #         return False



    async def message_seen(self):
        room_name = self.chatUtils.conversation_group(
            conversation_id=self.payload.get("conversation_id")
        )
        if self.payload.get("is_customer"):
            await self.agent_notification()
        else:
            await self.emit(room_name, namespace=self.customer_namespace, sid=self.payload.get("sid"))

    async def conversation_unresolved(self):
        print("🔄 Processing conversation unresolved event"
        )
        await self.agent_notification()
    




    
        



async def chat_subscriber(sio: socketio.AsyncServer, channel: str, payload: dict):
    from src.websocket.utils.chat_utils import ChatUtils
    print(f"🔔 Chat subscriber called for channel: {channel}")
   

    subscriber = ChatSubscriber(sio, payload=payload, chatUtils=ChatUtils)

    # handle chat events
    if channel == AGENT_NOTIFICATION_CHANNEL:
        print("📢 Processing agent notification")
        await subscriber.agent_notification()



    elif channel == AGENT_ONLINE_CHANNEL:
        print("👥 Processing agent availability notification")
        await subscriber.agent_notification()
        await subscriber.customer_notification()
    elif channel == AGENT_OFFLINE_CHANNEL:
        print("👥 Processing agent offline notification")
        await subscriber.agent_notification()
        await subscriber.customer_notification()
      
    
    elif channel==CUSTOMER_OFFLINE_CHANNEL:
        print('customer offline')
        await subscriber.agent_notification()

    elif channel ==CUSTOMER_LAND_WEBSITE:
        print('processing customer land website')
        await subscriber.agent_notification()
    


    elif channel == MESSAGE_CHANNEL:
        print("💬 Processing message")
        await subscriber.message()

    elif channel == TYPING_CHANNEL:
        print("⌨️ Processing typing")
        await subscriber.broadcast_conversation()

    elif channel == TYPING_STOP_CHANNEL:
        print("⏹️ Processing stop typing")
        await subscriber.broadcast_conversation()

    elif channel ==CUSTOMER_JOIN_CONVERSATION:
        await subscriber.agent_notification()




    elif channel == MESSAGE_SEEN_CHANNEL:
        print("👁️ Processing message seen")
        await subscriber.message_seen()
    elif channel == CONVERSATION_UNRESOLVED_CHANNEL:
        print("🔄 Processing conversation unresolved")
        await subscriber.conversation_unresolved()
    
    
    

    
    
    

    
 
    
    else:
        print(f"⚠️ Unknown channel: {channel}")
