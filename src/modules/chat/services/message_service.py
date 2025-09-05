from src.services.redis_service import RedisService
from src.models import Conversation, Message, MessageAttachment
from src.utils.response import CustomResponse as cr
from src.websocket.constants.channel_names import MESSAGE_CHANNEL,CONVERSATION_UNRESOLVED_CHANNEL
from ..schema import MessageSchema
from typing import Optional
from sqlalchemy.orm import selectinload
from src.services.redis_service import RedisService
from src.websocket.utils.chat_utils import ChatUtils
from src.websocket.constants.chat_event_constants import edit_message,receive_message,unresolve_conversation




class MessageService:
    def __init__(
        self, organization_id, payload: Optional[MessageSchema] = None, user_id: Optional[int] = None
    ):
        self.organization_id = organization_id
        self.payload = payload
        self.user_id = user_id
        


    async def get_user_sid(self, userId: int):
        if not userId:
            return None
            
        redis = await RedisService.get_redis()
        result = await redis.get(ChatUtils._user_add_sid(userId))
        if not result:
            return None
        return result.decode('utf-8')

    def make_msg_payload(self,record): 
        payload = record.to_json()
        
        if record.user:
            payload["user"] = {
                "id": record.user.id,
                "name": record.user.name,
                "email": record.user.email,
                "image": record.user.image
            }
        
        if record.reply_to:
            payload["reply_to"] = {
                "id": record.reply_to.id,
                "content": record.reply_to.content,
                "user_id": record.reply_to.user_id,
            }
        
        
        return payload
    

    async def get_message_payload(self, messageId:int,customerId:int=None):
        from src.websocket.utils.conversation_utils import ConversationUtility

        record = await Message.find_one({
            "id": messageId,
        }, options=[selectinload(Message.reply_to), selectinload(Message.user)])
        
        # Only get user SID if user_id is present (agent messages)
        skipSid = None
        if self.user_id:
            skipSid = await ConversationUtility.get_agent_sid(self.user_id)
        else:
            skipSid = await ConversationUtility.get_customer_sid(customer_id=customerId)

        
        payload = self.make_msg_payload(record)
        payload["sid"] = skipSid
        payload["event"] = receive_message
        
        return payload

    
    async def create(self, conversation_id: int):
        record = await Conversation.find_one(
            {"id": conversation_id, "organization_id": self.organization_id}
        )

        if not record:
            return cr.error(message="Conversation Not found")
        
        
        data = {
            **self.payload.dict(),
            "user_id": self.user_id,
            "conversation_id": conversation_id,
        }
        
        new_message = await Message.create(**data)

        for file in self.payload.attachments:
            await MessageAttachment.create(message_id=new_message.id, **file.dict())
        
       
        payload = await self.get_message_payload(new_message.id,record.customer_id)
        payload['customer_id'] = record.customer_id
        
        payload['organization_id'] = self.organization_id
        
        # Set is_customer flag based on whether user_id is present
        # If user_id is None, it's a customer message
        payload['is_customer'] = self.user_id is None

        if payload['is_customer'] and record.is_resolved:
            conversation = await Conversation.update(conversation_id, is_resolved=False)
            await RedisService.redis_publish(
                channel=CONVERSATION_UNRESOLVED_CHANNEL, message={"conversation_id": conversation_id,"event":unresolve_conversation,**conversation.to_json()}
            )

        await RedisService.redis_publish(
            channel=MESSAGE_CHANNEL, message=payload
        )
        

        return payload

    # edit message service
    async def edit(self, message_id: int):
        record = await Message.find_one({"id": message_id})

        if not record:
            return cr.error(message="Message Not found")

        updated_data = {**self.payload.dict()}
        updated_record = await Message.update(message_id, **updated_data, edited_content=record.content)

        payload = await self.get_message_payload(message_id)
        
        # Set is_customer flag based on whether user_id is present
        payload['is_customer'] = self.user_id is None

        await RedisService.redis_publish(
            channel=MESSAGE_CHANNEL, message={ **payload,"event": edit_message,}
        )



        return updated_record
    

    async def get_messages(self,conversationId:int):
   
        messages = await Message.filter(where={"conversation_id": conversationId},options=[selectinload(Message.reply_to), selectinload(Message.user)])
        records = []
        for msg in messages:
            payload = self.make_msg_payload(msg)
            records.append(payload)
        
        return records
