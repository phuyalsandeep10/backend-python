import json



from .base_chat_namespace import BaseChatNamespace
from src.websocket.constants.chat_namespace_constants import CUSTOMER_CHAT_NAMESPACE
from src.websocket.constants.channel_names import CUSTOMER_LAND_WEBSITE




class CustomerChatNamespace(BaseChatNamespace):
    namespace = CUSTOMER_CHAT_NAMESPACE

    def __init__(self):
        super().__init__(self.namespace, is_customer=True)



    async def _notify_to_users(self, org_id: int, customer):
        print("notify users in the same workspace that a customer has connected")
        print(f'customer {customer}')
   
        await self.redis_publish(
            channel=CUSTOMER_LAND_WEBSITE,
            message={
                    "event": self.customer_land,
                    "mode": "online",
                    "organization_id": org_id,
                    "customer": customer.to_json()
                }
            
        )

    
    async def on_connect(self, sid, environ, auth: dict):
        print(f"🔌Customer Socket connection attempt: {sid}")
        from src.models import Customer

        if not auth:
            print("No auth data provided")
            return False

        # Handle customer connection (without token)
        customer_id = auth.get("customer_id")
        print(f"customer id {customer_id}")
        if not customer_id:
            return False
        organization_id = auth.get("organization_id")
        conversation_id = auth.get("conversation_id")
        customer = await Customer.update(customer_id,is_online=True)

        if not customer or not organization_id:
            print(
                f"❌ Missing customer connection data: customer_id={customer_id}"
            )
            return False

        await self.conversation_service.customer_connect(sid, customer_id, organization_id)
        
        await self._notify_to_users(organization_id, customer)

        if conversation_id:
            await self.conversation_service.customer_join_conversation(customer_id, conversation_id)

        # notify users with a specific customer landing event
        print("✅ Published customer_land event to ")
        print(f"✅ Customer {customer_id} connected with SID {sid}")

        return True

   
