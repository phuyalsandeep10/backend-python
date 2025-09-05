from src.services.redis_service import RedisService

REDIS_SID_KEY = "ws:chat:sid:"  # chat:sid:{sid} -> conversation_id
REDIS_ROOM_KEY = "ws:chat:room:"
class ConversationUtility:

    @staticmethod
    async def set_agent_sid(sid:str, user_id:int):
        await RedisService.setValue(f"agent_id:{user_id}",sid)
        await RedisService.setValue(f'agent_sid:{sid}',user_id)

    @staticmethod
    async def get_agent_sid(user_id:int):
        return await RedisService.getValue(f"agent_id:{user_id}")

    @staticmethod
    async def get_agent_id(sid:str):
        return await RedisService.getValue(f'agent_sid:{sid}')
   

    @staticmethod
    async def set_customer_sid(sid:str, customer_id:int):
        await RedisService.setValue(f"customer_id:{customer_id}",sid)
        await RedisService.setValue(f"customer_sid:{sid}",customer_id)

    @staticmethod
    async def get_customer_sid(customer_id:int):
        return await RedisService.getValue(f"customer_id:{customer_id}")
    
    @staticmethod
    async def get_customer_id(sid:str):
        return await RedisService.getValue(f"customer_sid:{sid}")

    @staticmethod
    async def get_conversation_id(sid:int):
        return await RedisService.getValue(f"{REDIS_SID_KEY}:{sid}")

    @staticmethod
    async def set_conversation_id(sid, conversation_id:int):
        await RedisService.setValue(f"{REDIS_SID_KEY}:{sid}", conversation_id)
        roomKey = f'{REDIS_ROOM_KEY}:{conversation_id}'
        print(f"set key {roomKey}")
        redis = await RedisService.get_redis()
        await redis.sadd(roomKey, sid)
        # await RedisService.setValue(f'{REDIS_ROOM_KEY}:{conversation_id}',sid)
    
    @staticmethod
    async def remove_sid_from_conversation(sid:str,conversation_id:int):
        # before_ids = await ConversationUtility.get_conversation_sids(conversation_id=conversation_id)

        await RedisService.remove(f'{REDIS_ROOM_KEY}:{conversation_id}',sid)
        ids = await ConversationUtility.get_conversation_sids(conversation_id=conversation_id)
      

    @staticmethod
    async def get_conversation_sids(conversation_id:int):
        try:
            redis = await RedisService.get_redis()
            roomKey = f'{REDIS_ROOM_KEY}:{conversation_id}'
            print(f"conversation sids roomKey {roomKey} and conversation key {conversation_id}")
            result = await redis.smembers(roomKey)
            print(f"conversation sids member result {result}")
            return [item.decode("utf-8") for item in result] if result else []
        except Exception as e:
            print(f"Error getting conversation sids: {e}")
            return []
